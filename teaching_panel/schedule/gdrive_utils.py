"""
Утилиты для работы с Google Drive API
Автоматическая загрузка записей уроков в Google Drive через OAuth2
"""

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from django.conf import settings
import os
import sys
import uuid
import io
import subprocess
import tempfile
import logging
import json

logger = logging.getLogger(__name__)


class DummyGoogleDriveManager:
    """Безопасный no-op менеджер для тестов/когда Google Drive выключен.

    Нужен, чтобы unit-тесты не делали сетевые вызовы и не создавали реальные папки/файлы.
    """

    root_folder_id = None

    def create_folder(self, folder_name, parent_folder_id=None):
        return f"dummy_folder_{uuid.uuid4().hex}"

    def get_or_create_teacher_folder(self, teacher):
        root = f"dummy_teacher_{getattr(teacher, 'id', 'unknown')}_{uuid.uuid4().hex}"
        return {
            'root': root,
            'recordings': f"{root}_recordings",
            'homework': f"{root}_homework",
            'materials': f"{root}_materials",
            'students': f"{root}_students",
        }

    def upload_file(self, file_path_or_object, file_name, folder_id=None, mime_type='video/mp4', teacher=None):
        file_id = f"dummy_file_{uuid.uuid4().hex}"
        return {
            'file_id': file_id,
            'web_view_link': f"https://drive.google.com/file/d/{file_id}/view",
            'web_content_link': '',
        }

    def delete_file(self, file_id):
        return True

    def calculate_folder_size(self, folder_id):
        return {'total_size': 0, 'file_count': 0, 'folder_count': 0}

    def get_teacher_storage_stats(self, teacher):
        return {
            'total_size': 0,
            'total_files': 0,
            'total_folders': 0,
            'recordings': {'total_size': 0, 'file_count': 0},
            'homework': {'total_size': 0, 'file_count': 0},
            'materials': {'total_size': 0, 'file_count': 0},
            'students': {'total_size': 0, 'file_count': 0},
        }


def _should_use_real_gdrive() -> bool:
    if not getattr(settings, 'USE_GDRIVE_STORAGE', False):
        return False
    if os.environ.get('ALLOW_REAL_GDRIVE_IN_TESTS') == '1':
        return True
    # Защита: в автоматических unit-тестах не трогаем реальный Drive
    if any(arg == 'test' or arg.endswith('manage.py') and 'test' in sys.argv for arg in sys.argv):
        return False
    if os.environ.get('PYTEST_CURRENT_TEST'):
        return False
    return True


class GoogleDriveManager:
    """Менеджер для работы с Google Drive через OAuth2"""
    
    def __init__(self):
        """Инициализация клиента Google Drive"""
        try:
            # Путь к файлу OAuth2 token
            token_path = getattr(settings, 'GDRIVE_TOKEN_FILE', 'gdrive_token.json')
            
            if not os.path.exists(token_path):
                logger.error(f"Google Drive token file not found: {token_path}")
                raise FileNotFoundError(f"Missing {token_path}")
            
            # Загружаем credentials из token file
            creds = None
            try:
                creds = Credentials.from_authorized_user_file(
                    token_path,
                    scopes=['https://www.googleapis.com/auth/drive.file']
                )
            except Exception as e:
                logger.error(f"Failed to load credentials from {token_path}: {e}")
                raise
            
            # Обновляем токен если истёк
            if creds and creds.expired and creds.refresh_token:
                try:
                    logger.info("Refreshing expired Google Drive token...")
                    creds.refresh(Request())
                    # Сохраняем обновлённый токен
                    with open(token_path, 'w') as token:
                        token.write(creds.to_json())
                    logger.info("Token refreshed successfully")
                except Exception as e:
                    logger.error(f"Failed to refresh token: {e}")
                    raise
            
            if not creds or not creds.valid:
                raise ValueError("Invalid credentials - run setup_gdrive_oauth.py to get new token")
            
            # Создаем клиент Drive API
            self.service = build('drive', 'v3', credentials=creds)
            
            # ID корневой папки для хранения (GDRIVE_ROOT_FOLDER_ID - главная папка lectio.space)
            # Fallback на GDRIVE_RECORDINGS_FOLDER_ID для обратной совместимости
            self.root_folder_id = getattr(settings, 'GDRIVE_ROOT_FOLDER_ID', None) or \
                                  getattr(settings, 'GDRIVE_RECORDINGS_FOLDER_ID', None)
            
            if not self.root_folder_id:
                logger.error("GDRIVE_ROOT_FOLDER_ID not set in settings! Teacher folders will be created in root!")
            else:
                logger.info(f"Using root folder ID: {self.root_folder_id}")
                
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive Manager: {e}")
            raise
    
    def create_folder(self, folder_name, parent_folder_id=None):
        """
        Создать папку в Google Drive
        
        Args:
            folder_name: Название папки
            parent_folder_id: ID родительской папки (если None, создаст в корне)
            
        Returns:
            str: ID созданной папки
        """
        try:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_folder_id:
                file_metadata['parents'] = [parent_folder_id]
            
            folder = self.service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()
            
            folder_id = folder.get('id')
            logger.info(f"Created Google Drive folder: {folder_name} (ID: {folder_id})")
            
            return folder_id
            
        except Exception as e:
            logger.error(f"Failed to create Google Drive folder: {e}")
            raise
    
    def get_or_create_teacher_folder(self, teacher):
        """
        Получить или создать подпапку для преподавателя с подструктурой
        
        Args:
            teacher: Объект CustomUser (преподаватель)
            
        Returns:
            dict: {'root': folder_id, 'recordings': rec_id, 'homework': hw_id, 'materials': mat_id, 'students': st_id}
        """
        try:
            # Формируем название папки: Teacher_123_Ivan_Petrov
            folder_name = f"Teacher_{teacher.id}_{teacher.first_name}_{teacher.last_name}".replace(' ', '_')
            
            # Ищем существующую папку
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            if self.root_folder_id:
                query += f" and '{self.root_folder_id}' in parents"
            
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            items = results.get('files', [])
            
            if items:
                # Папка уже существует
                teacher_folder_id = items[0]['id']
                logger.info(f"Found existing teacher folder: {folder_name} (ID: {teacher_folder_id})")
            else:
                # Создаём новую папку
                teacher_folder_id = self.create_folder(folder_name, self.root_folder_id)
                logger.info(f"Created new teacher folder: {folder_name} (ID: {teacher_folder_id})")
            
            # Создаём подпапки внутри папки учителя
            subfolders = {}
            subfolder_names = ['Recordings', 'Homework', 'Materials', 'Students']
            
            for subfolder_name in subfolder_names:
                subfolder_id = self._get_or_create_subfolder(subfolder_name, teacher_folder_id)
                subfolders[subfolder_name.lower()] = subfolder_id
            
            subfolders['root'] = teacher_folder_id
            return subfolders
                
        except Exception as e:
            logger.error(f"Failed to get/create teacher folder: {e}")
            # Если не удалось создать подпапку, используем root
            return {'root': self.root_folder_id, 'recordings': self.root_folder_id, 
                    'homework': self.root_folder_id, 'materials': self.root_folder_id,
                    'students': self.root_folder_id}
    
    def _get_or_create_subfolder(self, folder_name, parent_id):
        """Получить или создать подпапку"""
        try:
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            query += f" and '{parent_id}' in parents"
            
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            items = results.get('files', [])
            
            if items:
                return items[0]['id']
            else:
                return self.create_folder(folder_name, parent_id)
        except:
            return parent_id
    
    def get_or_create_student_folder(self, student, teacher_students_folder_id):
        """
        Создать папку для конкретного ученика внутри папки Students учителя
        
        Args:
            student: Объект User (ученик)
            teacher_students_folder_id: ID папки Students учителя
            
        Returns:
            str: ID папки ученика
        """
        try:
            folder_name = f"Student_{student.id}_{student.first_name}_{student.last_name}".replace(' ', '_')
            
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            query += f" and '{teacher_students_folder_id}' in parents"
            
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            items = results.get('files', [])
            
            if items:
                return items[0]['id']
            else:
                return self.create_folder(folder_name, teacher_students_folder_id)
                
        except Exception as e:
            logger.error(f"Failed to create student folder: {e}")
            return teacher_students_folder_id
    
    def upload_file(self, file_path_or_object, file_name, folder_id=None, mime_type='video/mp4', teacher=None):
        """
        Загрузить файл в Google Drive
        
        Args:
            file_path_or_object: Путь к локальному файлу (str) или file object
            file_name: Имя файла в Google Drive
            folder_id: ID папки назначения (если None, использует папку преподавателя)
            mime_type: MIME тип файла
            teacher: Объект преподавателя (для создания подпапки)
            
        Returns:
            dict: {'file_id': str, 'web_view_link': str, 'web_content_link': str}
        """
        try:
            # Определяем целевую папку
            target_folder_id = folder_id
            if not target_folder_id and teacher:
                # Создаём/получаем папку преподавателя
                target_folder_id = self.get_or_create_teacher_folder(teacher)
            elif not target_folder_id:
                # Используем root папку
                target_folder_id = self.root_folder_id
            
            file_metadata = {'name': file_name}
            
            if target_folder_id:
                file_metadata['parents'] = [target_folder_id]
            
            # Поддержка как путей, так и file objects
            if isinstance(file_path_or_object, str):
                media = MediaFileUpload(
                    file_path_or_object,
                    mimetype=mime_type,
                    resumable=True
                )
            else:
                # Если передан file object, сохраним во временный файл
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_name)[1]) as tmp:
                    tmp.write(file_path_or_object.read())
                    tmp_path = tmp.name
                
                media = MediaFileUpload(
                    tmp_path,
                    mimetype=mime_type,
                    resumable=True
                )
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, size, webViewLink, webContentLink'
            ).execute()
            
            file_id = file.get('id')
            
            # Удалить временный файл если создавался
            if not isinstance(file_path_or_object, str):
                try:
                    os.remove(tmp_path)
                except:
                    pass
            
            # Делаем файл доступным по ссылке
            self.set_file_public(file_id)
            
            logger.info(f"Uploaded file to Google Drive: {file_name} (ID: {file_id}) in folder {target_folder_id}")
            
            return {
                'file_id': file_id,
                'name': file.get('name'),
                'size': int(file.get('size', 0)),
                'web_view_link': file.get('webViewLink'),
                'web_content_link': file.get('webContentLink'),
            }
            
        except Exception as e:
            logger.error(f"Failed to upload file to Google Drive: {e}")
            # Удалить временный файл в случае ошибки
            if not isinstance(file_path_or_object, str):
                try:
                    os.remove(tmp_path)
                except:
                    pass
            raise
    
    def set_file_public(self, file_id):
        """
        Сделать файл публичным (доступным по ссылке)
        
        Args:
            file_id: ID файла в Google Drive
        """
        try:
            permission = {
                'type': 'anyone',
                'role': 'reader'
            }
            
            self.service.permissions().create(
                fileId=file_id,
                body=permission
            ).execute()
            
            logger.info(f"Set file {file_id} as public")
            
        except Exception as e:
            logger.error(f"Failed to set file as public: {e}")
            raise
    
    def get_direct_download_link(self, file_id):
        """
        Получить прямую ссылку на скачивание файла
        
        Args:
            file_id: ID файла в Google Drive
            
        Returns:
            str: Прямая ссылка для скачивания
        """
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    
    def get_streaming_link(self, file_id):
        """
        Получить ссылку для стриминга видео (для HTML5 video player)
        
        Args:
            file_id: ID файла в Google Drive
            
        Returns:
            str: Прямая ссылка для стриминга
        """
        # Используем webContentLink формат который работает для стриминга
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    
    def get_embed_link(self, file_id):
        """
        Получить ссылку для встраивания видео
        
        Args:
            file_id: ID файла в Google Drive
            
        Returns:
            str: Ссылка для <iframe>
        """
        return f"https://drive.google.com/file/d/{file_id}/preview"
    
    def delete_file(self, file_id):
        """
        Удалить файл из Google Drive
        
        Args:
            file_id: ID файла
        """
        try:
            self.service.files().delete(fileId=file_id).execute()
            logger.info(f"Deleted file from Google Drive: {file_id}")
            
        except Exception as e:
            logger.error(f"Failed to delete file from Google Drive: {e}")
            raise
    
    def get_file_info(self, file_id):
        """
        Получить информацию о файле
        
        Args:
            file_id: ID файла
            
        Returns:
            dict: Информация о файле
        """
        try:
            file = self.service.files().get(
                fileId=file_id,
                fields='id, name, size, mimeType, createdTime, modifiedTime'
            ).execute()
            
            return file
            
        except Exception as e:
            logger.error(f"Failed to get file info: {e}")
            raise
    
    def calculate_folder_size(self, folder_id):
        """
        Рекурсивно посчитать размер папки и всех вложенных файлов
        
        Args:
            folder_id: ID папки
            
        Returns:
            dict: {'total_size': bytes, 'file_count': count, 'folder_count': count}
        """
        try:
            total_size = 0
            file_count = 0
            folder_count = 0
            
            # Получаем все файлы в папке
            page_token = None
            while True:
                query = f"'{folder_id}' in parents and trashed=false"
                results = self.service.files().list(
                    q=query,
                    spaces='drive',
                    fields='nextPageToken, files(id, name, mimeType, size)',
                    pageToken=page_token
                ).execute()
                
                items = results.get('files', [])
                
                for item in items:
                    mime_type = item.get('mimeType', '')
                    
                    if mime_type == 'application/vnd.google-apps.folder':
                        # Рекурсивно считаем размер подпапки
                        folder_count += 1
                        subfolder_stats = self.calculate_folder_size(item['id'])
                        total_size += subfolder_stats['total_size']
                        file_count += subfolder_stats['file_count']
                        folder_count += subfolder_stats['folder_count']
                    else:
                        # Обычный файл
                        file_size = int(item.get('size', 0))
                        total_size += file_size
                        file_count += 1
                
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
            
            return {
                'total_size': total_size,
                'file_count': file_count,
                'folder_count': folder_count
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate folder size: {e}")
            return {'total_size': 0, 'file_count': 0, 'folder_count': 0}
    
    def get_teacher_storage_stats(self, teacher):
        """
        Получить статистику использования хранилища учителем
        
        Args:
            teacher: Объект User (учитель)
            
        Returns:
            dict: Статистика по папкам учителя
        """
        try:
            folders = self.get_or_create_teacher_folder(teacher)
            teacher_folder_id = folders['root']
            
            # Считаем размер всей папки учителя
            stats = self.calculate_folder_size(teacher_folder_id)
            
            # Добавляем детализацию по подпапкам
            detailed_stats = {
                'total_size': stats['total_size'],
                'total_files': stats['file_count'],
                'total_folders': stats['folder_count'],
                'recordings': self.calculate_folder_size(folders['recordings']),
                'homework': self.calculate_folder_size(folders['homework']),
                'materials': self.calculate_folder_size(folders['materials']),
                'students': self.calculate_folder_size(folders['students']),
            }
            
            return detailed_stats
            
        except Exception as e:
            logger.error(f"Failed to get teacher storage stats: {e}")
            return {
                'total_size': 0,
                'total_files': 0,
                'total_folders': 0,
                'recordings': {'total_size': 0, 'file_count': 0},
                'homework': {'total_size': 0, 'file_count': 0},
                'materials': {'total_size': 0, 'file_count': 0},
                'students': {'total_size': 0, 'file_count': 0},
            }


# Singleton instance
_gdrive_manager = None


def get_gdrive_manager():
    """Получить singleton instance Google Drive Manager"""
    global _gdrive_manager

    if _gdrive_manager is None:
        if _should_use_real_gdrive():
            _gdrive_manager = GoogleDriveManager()
        else:
            _gdrive_manager = DummyGoogleDriveManager()

    return _gdrive_manager


def compress_video(input_path, output_path):
    """
    Сжимает видео через FFmpeg
    
    Параметры:
    - input_path: путь к исходному файлу
    - output_path: путь к сжатому файлу
    
    Возвращает:
    - True если успешно, False если ошибка
    """
    try:
        # Проверка что FFmpeg установлен
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("FFmpeg not installed, skipping compression")
            return False
        
        # Получить настройки из settings
        video_resolution = getattr(settings, 'VIDEO_MAX_RESOLUTION', '1280:720')
        video_crf = getattr(settings, 'VIDEO_CRF', 23)
        video_preset = getattr(settings, 'VIDEO_PRESET', 'medium')
        audio_bitrate = getattr(settings, 'AUDIO_BITRATE', '128k')
        
        # FFmpeg команда для оптимального сжатия
        cmd = [
            'ffmpeg',
            '-i', input_path,                    # Входной файл
            '-c:v', 'libx264',                   # Видеокодек H.264
            '-preset', video_preset,             # Баланс скорость/качество
            '-crf', str(video_crf),              # Constant Rate Factor
            '-vf', f'scale={video_resolution}',  # Масштабировать до 720p
            '-c:a', 'aac',                       # Аудиокодек AAC
            '-b:a', audio_bitrate,               # Битрейт аудио
            '-movflags', '+faststart',           # Оптимизация для веб-стриминга
            '-y',                                # Перезаписать если существует
            output_path
        ]
        
        logger.info(f"Starting video compression: {input_path}")
        
        # Запустить FFmpeg
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=3600  # Таймаут 1 час
        )
        
        if result.returncode == 0:
            # Проверить что файл создан и меньше оригинала
            if os.path.exists(output_path):
                original_size = os.path.getsize(input_path)
                compressed_size = os.path.getsize(output_path)
                compression_ratio = (1 - compressed_size / original_size) * 100
                
                logger.info(f"Video compressed: {original_size / (1024**2):.1f} MB → {compressed_size / (1024**2):.1f} MB ({compression_ratio:.1f}% reduction)")
                return True
        else:
            logger.error(f"FFmpeg failed: {result.stderr.decode()}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("FFmpeg timeout (>1 hour)")
        return False
    except Exception as e:
        logger.error(f"Compression error: {e}")
        return False
