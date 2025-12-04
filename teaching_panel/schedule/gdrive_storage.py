"""
Google Drive Storage Backend для Django
Хранение файлов ДЗ, материалов и записей на Google Drive
"""

from django.core.files.storage import Storage
from django.core.files.base import File
from django.utils.decoding import force_str
from django.conf import settings
from .gdrive_utils import get_gdrive_manager
import os
import io
import logging
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

logger = logging.getLogger(__name__)


class GoogleDriveStorage(Storage):
    """
    Django Storage Backend для Google Drive
    Автоматически загружает файлы в Google Drive вместо локального хранилища
    """
    
    def __init__(self, folder_type='homework'):
        """
        Args:
            folder_type: Тип папки ('homework', 'materials', 'recordings', 'attachments')
        """
        self.folder_type = folder_type
        self._gdrive = None
        self._folder_id = None
    
    @property
    def gdrive(self):
        """Lazy initialization Google Drive Manager"""
        if self._gdrive is None:
            try:
                self._gdrive = get_gdrive_manager()
            except Exception as e:
                logger.error(f"Failed to initialize Google Drive: {e}")
                raise
        return self._gdrive
    
    @property
    def folder_id(self):
        """Получить ID папки для текущего типа файлов"""
        if self._folder_id is None:
            folder_mapping = {
                'homework': getattr(settings, 'GDRIVE_HOMEWORK_FOLDER_ID', None),
                'materials': getattr(settings, 'GDRIVE_MATERIALS_FOLDER_ID', None),
                'recordings': getattr(settings, 'GDRIVE_RECORDINGS_FOLDER_ID', None),
                'attachments': getattr(settings, 'GDRIVE_ATTACHMENTS_FOLDER_ID', None),
            }
            self._folder_id = folder_mapping.get(self.folder_type)
            
            if not self._folder_id:
                # Если папка не настроена, создаем её
                root_id = getattr(settings, 'GDRIVE_ROOT_FOLDER_ID', None)
                if root_id:
                    folder_name = f"TeachingPanel_{self.folder_type.title()}"
                    try:
                        self._folder_id = self.gdrive.create_folder(folder_name, root_id)
                        logger.info(f"Created {self.folder_type} folder: {folder_name}")
                    except Exception as e:
                        logger.error(f"Failed to create folder: {e}")
                        self._folder_id = root_id
        
        return self._folder_id
    
    def _save(self, name, content):
        """
        Сохранить файл в Google Drive
        
        Args:
            name: Имя файла
            content: File object
            
        Returns:
            str: Сохранённое имя файла (Google Drive file ID)
        """
        try:
            # Создаем временный файл для загрузки
            temp_file_path = None
            
            if hasattr(content, 'temporary_file_path'):
                # Django TemporaryUploadedFile
                temp_file_path = content.temporary_file_path()
            else:
                # InMemoryUploadedFile - сохраняем во временный файл
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    for chunk in content.chunks():
                        temp_file.write(chunk)
                    temp_file_path = temp_file.name
            
            # Metadata для файла
            file_metadata = {
                'name': name,
                'parents': [self.folder_id] if self.folder_id else []
            }
            
            # Загружаем файл
            media = MediaFileUpload(
                temp_file_path,
                mimetype=getattr(content, 'content_type', 'application/octet-stream'),
                resumable=True
            )
            
            uploaded_file = self.gdrive.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, mimeType, size, webViewLink, webContentLink'
            ).execute()
            
            file_id = uploaded_file.get('id')
            file_size = uploaded_file.get('size', 0)
            
            logger.info(f"Uploaded {name} to Google Drive: {file_id} ({file_size} bytes)")
            
            # Удаляем временный файл если создавали
            if not hasattr(content, 'temporary_file_path'):
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
            
            # Возвращаем file_id как имя (будем хранить в БД)
            return file_id
            
        except Exception as e:
            logger.error(f"Failed to upload file {name} to Google Drive: {e}")
            raise
    
    def _open(self, name, mode='rb'):
        """
        Открыть файл из Google Drive
        
        Args:
            name: Google Drive file ID
            mode: Режим открытия
            
        Returns:
            File: Django File object
        """
        try:
            # name - это file_id в Google Drive
            file_id = name
            
            request = self.gdrive.service.files().get_media(fileId=file_id)
            file_stream = io.BytesIO()
            downloader = MediaIoBaseDownload(file_stream, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            file_stream.seek(0)
            return File(file_stream, name=name)
            
        except Exception as e:
            logger.error(f"Failed to download file {name} from Google Drive: {e}")
            raise
    
    def delete(self, name):
        """
        Удалить файл из Google Drive
        
        Args:
            name: Google Drive file ID
        """
        try:
            file_id = name
            self.gdrive.service.files().delete(fileId=file_id).execute()
            logger.info(f"Deleted file from Google Drive: {file_id}")
        except Exception as e:
            logger.error(f"Failed to delete file {name}: {e}")
    
    def exists(self, name):
        """
        Проверить существование файла
        
        Args:
            name: Google Drive file ID
            
        Returns:
            bool: True если файл существует
        """
        try:
            file_id = name
            self.gdrive.service.files().get(
                fileId=file_id,
                fields='id'
            ).execute()
            return True
        except:
            return False
    
    def size(self, name):
        """
        Получить размер файла
        
        Args:
            name: Google Drive file ID
            
        Returns:
            int: Размер файла в байтах
        """
        try:
            file_id = name
            file_metadata = self.gdrive.service.files().get(
                fileId=file_id,
                fields='size'
            ).execute()
            return int(file_metadata.get('size', 0))
        except:
            return 0
    
    def url(self, name):
        """
        Получить URL для просмотра/скачивания файла
        
        Args:
            name: Google Drive file ID
            
        Returns:
            str: URL файла
        """
        try:
            file_id = name
            # Возвращаем прямую ссылку на просмотр
            return f"https://drive.google.com/file/d/{file_id}/view"
        except:
            return ""
    
    def get_download_url(self, name):
        """
        Получить прямую ссылку на скачивание
        
        Args:
            name: Google Drive file ID
            
        Returns:
            str: URL для скачивания
        """
        try:
            file_id = name
            return f"https://drive.google.com/uc?export=download&id={file_id}"
        except:
            return ""
    
    def listdir(self, path):
        """
        Список файлов в папке
        
        Args:
            path: ID папки или путь
            
        Returns:
            tuple: (directories, files)
        """
        try:
            folder_id = path if path else self.folder_id
            
            query = f"'{folder_id}' in parents and trashed=false"
            results = self.gdrive.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name, mimeType)'
            ).execute()
            
            items = results.get('files', [])
            
            directories = [
                item['name'] 
                for item in items 
                if item['mimeType'] == 'application/vnd.google-apps.folder'
            ]
            
            files = [
                item['name'] 
                for item in items 
                if item['mimeType'] != 'application/vnd.google-apps.folder'
            ]
            
            return (directories, files)
            
        except Exception as e:
            logger.error(f"Failed to list directory: {e}")
            return ([], [])


# Предконфигурированные storage backends для разных типов файлов
homework_storage = lambda: GoogleDriveStorage(folder_type='homework')
materials_storage = lambda: GoogleDriveStorage(folder_type='materials')
attachments_storage = lambda: GoogleDriveStorage(folder_type='attachments')
