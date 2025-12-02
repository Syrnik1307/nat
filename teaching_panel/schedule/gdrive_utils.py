"""
Утилиты для работы с Google Drive API
Автоматическая загрузка записей уроков в Google Drive
"""

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from django.conf import settings
import os
import io
import subprocess
import tempfile
import logging

logger = logging.getLogger(__name__)


class GoogleDriveManager:
    """Менеджер для работы с Google Drive"""
    
    def __init__(self):
        """Инициализация клиента Google Drive"""
        try:
            # Путь к файлу credentials (Service Account)
            creds_path = getattr(settings, 'GDRIVE_CREDENTIALS_FILE', 'gdrive-credentials.json')
            
            if not os.path.exists(creds_path):
                logger.error(f"Google Drive credentials file not found: {creds_path}")
                raise FileNotFoundError(f"Missing {creds_path}")
            
            # Создаем credentials из Service Account
            credentials = service_account.Credentials.from_service_account_file(
                creds_path,
                scopes=['https://www.googleapis.com/auth/drive.file']
            )
            
            # Создаем клиент Drive API
            self.service = build('drive', 'v3', credentials=credentials)
            
            # ID корневой папки для хранения записей (создайте в Google Drive и укажите в settings)
            self.root_folder_id = getattr(settings, 'GDRIVE_RECORDINGS_FOLDER_ID', None)
            
            if not self.root_folder_id:
                logger.warning("GDRIVE_RECORDINGS_FOLDER_ID not set in settings")
                
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
    
    def upload_file(self, file_path, file_name, folder_id=None, mime_type='video/mp4'):
        """
        Загрузить файл в Google Drive
        
        Args:
            file_path: Путь к локальному файлу
            file_name: Имя файла в Google Drive
            folder_id: ID папки назначения
            mime_type: MIME тип файла
            
        Returns:
            dict: {'file_id': str, 'web_view_link': str, 'web_content_link': str}
        """
        try:
            file_metadata = {'name': file_name}
            
            if folder_id:
                file_metadata['parents'] = [folder_id]
            elif self.root_folder_id:
                file_metadata['parents'] = [self.root_folder_id]
            
            media = MediaFileUpload(
                file_path,
                mimetype=mime_type,
                resumable=True
            )
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, size, webViewLink, webContentLink'
            ).execute()
            
            file_id = file.get('id')
            
            # Делаем файл доступным по ссылке
            self.set_file_public(file_id)
            
            logger.info(f"Uploaded file to Google Drive: {file_name} (ID: {file_id})")
            
            return {
                'file_id': file_id,
                'name': file.get('name'),
                'size': int(file.get('size', 0)),
                'web_view_link': file.get('webViewLink'),
                'web_content_link': file.get('webContentLink'),
            }
            
        except Exception as e:
            logger.error(f"Failed to upload file to Google Drive: {e}")
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


# Singleton instance
_gdrive_manager = None


def get_gdrive_manager():
    """Получить singleton instance Google Drive Manager"""
    global _gdrive_manager
    
    if _gdrive_manager is None:
        _gdrive_manager = GoogleDriveManager()
    
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
