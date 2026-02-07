"""
Утилиты для работы с Google Drive API
Автоматическая загрузка записей уроков в Google Drive через OAuth2
"""

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload, MediaIoBaseUpload
from googleapiclient.errors import HttpError
from django.conf import settings
from django.core.cache import cache
import google_auth_httplib2
import httplib2

# Явный импорт RedirectMissingLocation для корректной обработки
try:
    from httplib2.error import RedirectMissingLocation
except ImportError:
    # Fallback для старых версий httplib2
    class RedirectMissingLocation(Exception):
        pass
import socket
import os
import sys
import uuid
import io
import subprocess
import tempfile
import logging
import json
import time
import random
import functools
import threading

logger = logging.getLogger(__name__)

# ============================================================
# CRITICAL: Таймауты для Google API
# httplib2 по умолчанию может зависнуть навсегда на DNS/connect
# ============================================================
MAX_RETRIES = 3
RETRY_DELAY_BASE = 1.0  # секунд
RETRY_DELAY_MAX = 10.0  # секунд
REQUEST_TIMEOUT = 30  # секунд для обычных запросов
FOLDER_TIMEOUT = 60  # секунд для операций с папками (DNS/SSL могут быть медленными)
CONNECT_TIMEOUT = 10  # секунд для установки соединения
UPLOAD_TIMEOUT = 300  # секунд для загрузки файлов
RESUMABLE_MAX_TOTAL_ATTEMPTS = 10  # макс. общее число итераций resumable upload
CACHE_TTL = 3600  # 1 час кэш папок учителя
SIMPLE_UPLOAD_THRESHOLD = 5 * 1024 * 1024  # 5 MB - для файлов меньше используем simple upload

# Устанавливаем глобальный socket timeout для httplib2
socket.setdefaulttimeout(REQUEST_TIMEOUT)

# ============================================================
# CRITICAL: Force IPv4 for Google API requests
# IPv6 causes 10+ second delays due to connection timeouts
# Same issue as Zoom API - see zoom_client.py
# ============================================================
_original_getaddrinfo = socket.getaddrinfo

def _ipv4_only_getaddrinfo(*args, **kwargs):
    """Filter to only return IPv4 addresses to avoid IPv6 timeout issues"""
    responses = _original_getaddrinfo(*args, **kwargs)
    return [r for r in responses if r[0] == socket.AF_INET]

# Apply the patch globally for this module
socket.getaddrinfo = _ipv4_only_getaddrinfo


class TimeoutError(Exception):
    """Исключение для таймаутов Google API операций"""
    pass


def _run_with_timeout(func, timeout_seconds, *args, **kwargs):
    """
    Выполнить функцию с жёстким таймаутом через threading.
    Работает на всех платформах (включая Windows где нет SIGALRM).
    """
    result = [None]
    exception = [None]
    completed = threading.Event()
    
    def target():
        try:
            result[0] = func(*args, **kwargs)
        except Exception as e:
            exception[0] = e
        finally:
            completed.set()
    
    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    
    if not completed.wait(timeout=timeout_seconds):
        raise TimeoutError(f"Operation timed out after {timeout_seconds}s")
    
    if exception[0] is not None:
        raise exception[0]
    
    return result[0]


def retry_on_error(max_retries=MAX_RETRIES, delay_base=RETRY_DELAY_BASE, timeout=REQUEST_TIMEOUT):
    """
    Декоратор для повторных попыток при ошибках Google API.
    
    Args:
        max_retries: Максимальное количество попыток
        delay_base: Базовая задержка между попытками (экспоненциальный backoff)
        timeout: Таймаут на одну попытку в секундах
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    # Оборачиваем вызов в таймаут
                    return _run_with_timeout(func, timeout, *args, **kwargs)
                except TimeoutError as e:
                    last_error = e
                    delay = min(delay_base * (2 ** attempt), RETRY_DELAY_MAX)
                    delay += random.uniform(0, delay * 0.3)  # jitter до 30%
                    logger.warning(f"Timeout (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {delay:.1f}s...")
                    time.sleep(delay)
                except HttpError as e:
                    last_error = e
                    # Не повторяем для 4xx ошибок (кроме 429 - rate limit)
                    if e.resp.status < 500 and e.resp.status != 429:
                        raise
                    delay = min(delay_base * (2 ** attempt), RETRY_DELAY_MAX)
                    delay += random.uniform(0, delay * 0.3)
                    logger.warning(f"Google API error (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {delay:.1f}s...")
                    time.sleep(delay)
                except RedirectMissingLocation as e:
                    # Google API redirect без Location header — транзиентная ошибка
                    last_error = e
                    delay = min(delay_base * (2 ** attempt), RETRY_DELAY_MAX)
                    delay += random.uniform(0, delay * 0.3)
                    logger.warning(f"RedirectMissingLocation (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {delay:.1f}s...")
                    time.sleep(delay)
                except (socket.timeout, socket.error, OSError) as e:
                    # Явные сетевые ошибки
                    last_error = e
                    delay = min(delay_base * (2 ** attempt), RETRY_DELAY_MAX)
                    delay += random.uniform(0, delay * 0.3)
                    logger.warning(f"Socket error (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {delay:.1f}s...")
                    time.sleep(delay)
                except Exception as e:
                    last_error = e
                    error_str = str(e).lower()
                    # Повторяем только для таймаутов и сетевых ошибок
                    if 'timeout' in error_str or 'connection' in error_str or 'network' in error_str or 'timed out' in error_str:
                        delay = min(delay_base * (2 ** attempt), RETRY_DELAY_MAX)
                        delay += random.uniform(0, delay * 0.3)
                        logger.warning(f"Network error (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {delay:.1f}s...")
                        time.sleep(delay)
                    else:
                        raise
            # Все попытки исчерпаны
            logger.error(f"All {max_retries} attempts failed for {func.__name__}")
            raise last_error
        return wrapper
    return decorator


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

    def file_exists(self, file_id):
        """Dummy: всегда возвращает True"""
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

    def get_drive_quota(self):
        """Dummy: возвращает заглушку квоты"""
        return {
            'limit': 15 * 1024 * 1024 * 1024,  # 15 GB
            'usage': 0,
            'usage_in_drive': 0,
            'usage_in_trash': 0,
            'limit_gb': 15.0,
            'usage_gb': 0.0,
            'free_gb': 15.0,
            'usage_percent': 0.0,
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
            
            # Создаем клиент Drive API с настроенными таймаутами
            # CRITICAL: httplib2.Http timeout применяется к socket операциям
            # Но некоторые операции (DNS, SSL handshake) могут зависнуть
            # Поэтому также используем socket.setdefaulttimeout и threading timeout в декораторе
            http = httplib2.Http(
                timeout=REQUEST_TIMEOUT,
                disable_ssl_certificate_validation=False
            )
            # Устанавливаем дополнительные параметры для предотвращения зависаний
            http.force_exception_to_status_code = False  # Не глотать исключения
            authed_http = google_auth_httplib2.AuthorizedHttp(creds, http=http)
            self.service = build('drive', 'v3', http=authed_http, cache_discovery=False)
            
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
    
    def _rebuild_service(self):
        """Пересоздать HTTP-клиент и Drive service.
        
        При RedirectMissingLocation httplib2 connection может быть corrupted.
        Пересоздание service с новым httplib2.Http решает проблему.
        """
        try:
            token_path = getattr(settings, 'GDRIVE_TOKEN_FILE', 'gdrive_token.json')
            creds = Credentials.from_authorized_user_file(
                token_path,
                scopes=['https://www.googleapis.com/auth/drive.file']
            )
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
            http = httplib2.Http(
                timeout=REQUEST_TIMEOUT,
                disable_ssl_certificate_validation=False
            )
            http.force_exception_to_status_code = False
            authed_http = google_auth_httplib2.AuthorizedHttp(creds, http=http)
            self.service = build('drive', 'v3', http=authed_http, cache_discovery=False)
            logger.info("Rebuilt Google Drive service connection")
        except Exception as e:
            logger.error(f"Failed to rebuild service: {e}")
            # Не перебрасываем — пусть следующий upload попробует на старом service

    @retry_on_error(timeout=FOLDER_TIMEOUT)
    def create_folder(self, folder_name, parent_folder_id=None):
        """
        Создать папку в Google Drive
        
        Args:
            folder_name: Название папки
            parent_folder_id: ID родительской папки (если None, создаст в корне)
            
        Returns:
            str: ID созданной папки
        """
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
    
    def get_or_create_teacher_folder(self, teacher):
        """
        Получить или создать подпапку для преподавателя с подструктурой.
        Использует кэширование в Redis и БД для минимизации API вызовов.
        
        Args:
            teacher: Объект CustomUser (преподаватель)
            
        Returns:
            dict: {'root': folder_id, 'recordings': rec_id, 'homework': hw_id, 'materials': mat_id, 'students': st_id}
        """
        # 1. Проверяем кэш Redis
        cache_key = f"gdrive_folders_teacher_{teacher.id}"
        cached = cache.get(cache_key)
        if cached:
            logger.debug(f"Using cached folders for teacher {teacher.id}")
            return cached
        
        # 2. Проверяем gdrive_folder_id в БД
        if teacher.gdrive_folder_id:
            # Есть сохранённый root ID - попробуем восстановить структуру быстро
            try:
                # Проверяем что папка ещё существует
                subfolders = self._get_existing_subfolders(teacher.gdrive_folder_id)
                if subfolders:
                    cache.set(cache_key, subfolders, CACHE_TTL)
                    logger.info(f"Restored folder structure from DB for teacher {teacher.id}")
                    return subfolders
            except Exception as e:
                logger.warning(f"Cached folder not accessible, recreating: {e}")
        
        # 3. Создаём структуру папок
        try:
            # Формируем название папки: Teacher_123_Ivan_Petrov
            folder_name = f"Teacher_{teacher.id}_{teacher.first_name}_{teacher.last_name}".replace(' ', '_')
            
            # Ищем существующую папку
            teacher_folder_id = self._find_folder(folder_name, self.root_folder_id)
            
            if not teacher_folder_id:
                # Создаём новую папку
                teacher_folder_id = self.create_folder(folder_name, self.root_folder_id)
                logger.info(f"Created new teacher folder: {folder_name} (ID: {teacher_folder_id})")
            else:
                logger.info(f"Found existing teacher folder: {folder_name} (ID: {teacher_folder_id})")
            
            # Создаём подпапки внутри папки учителя
            subfolders = {}
            subfolder_names = ['Recordings', 'Homework', 'Materials', 'Students']
            
            for subfolder_name in subfolder_names:
                subfolder_id = self._get_or_create_subfolder(subfolder_name, teacher_folder_id)
                subfolders[subfolder_name.lower()] = subfolder_id
            
            subfolders['root'] = teacher_folder_id
            
            # 4. Сохраняем в БД для последующих запросов
            if not teacher.gdrive_folder_id:
                teacher.gdrive_folder_id = teacher_folder_id
                teacher.save(update_fields=['gdrive_folder_id'])
            
            # 5. Кэшируем в Redis
            cache.set(cache_key, subfolders, CACHE_TTL)
            
            return subfolders
                
        except Exception as e:
            logger.error(f"Failed to get/create teacher folder: {e}")
            # Если не удалось создать подпапку, используем root
            return {'root': self.root_folder_id, 'recordings': self.root_folder_id, 
                    'homework': self.root_folder_id, 'materials': self.root_folder_id,
                    'students': self.root_folder_id}
    
    @retry_on_error()
    def _find_folder(self, folder_name, parent_id=None):
        """Найти папку по имени"""
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent_id:
            query += f" and '{parent_id}' in parents"
        
        results = self.service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)',
            pageSize=1
        ).execute()
        
        items = results.get('files', [])
        return items[0]['id'] if items else None
    
    @retry_on_error()
    def _get_existing_subfolders(self, root_folder_id):
        """Получить существующие подпапки по root ID"""
        query = f"'{root_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        
        results = self.service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)'
        ).execute()
        
        items = results.get('files', [])
        
        subfolders = {'root': root_folder_id}
        folder_map = {item['name'].lower(): item['id'] for item in items}
        
        for name in ['recordings', 'homework', 'materials', 'students']:
            subfolders[name] = folder_map.get(name, root_folder_id)
        
        # Если все подпапки найдены, возвращаем
        if all(name in folder_map for name in ['recordings', 'homework', 'materials', 'students']):
            return subfolders
        return None
    
    @retry_on_error()
    def _get_or_create_subfolder(self, folder_name, parent_id):
        """Получить или создать подпапку"""
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        query += f" and '{parent_id}' in parents"
        
        results = self.service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)',
            pageSize=1
        ).execute()
        
        items = results.get('files', [])
        
        if items:
            return items[0]['id']
        else:
            return self.create_folder(folder_name, parent_id)
    
    @retry_on_error()
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
            return self._find_folder(folder_name, teacher_students_folder_id) or \
                   self.create_folder(folder_name, teacher_students_folder_id)
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
        tmp_path = None
        file_content = None
        file_size = 0
        
        try:
            # Определяем целевую папку
            target_folder_id = folder_id
            if not target_folder_id and teacher:
                # Создаём/получаем папку преподавателя
                folders = self.get_or_create_teacher_folder(teacher)
                target_folder_id = folders.get('materials', folders.get('root'))
            elif not target_folder_id:
                # Используем root папку
                target_folder_id = self.root_folder_id
            
            file_metadata = {'name': file_name}
            
            if target_folder_id:
                file_metadata['parents'] = [target_folder_id]
            
            # Определяем размер файла и читаем контент для маленьких файлов
            if isinstance(file_path_or_object, str):
                file_size = os.path.getsize(file_path_or_object)
                use_simple_upload = file_size < SIMPLE_UPLOAD_THRESHOLD
                
                if use_simple_upload:
                    # Simple upload - читаем весь файл в память
                    with open(file_path_or_object, 'rb') as f:
                        file_content = f.read()
                    media = MediaIoBaseUpload(
                        io.BytesIO(file_content),
                        mimetype=mime_type,
                        resumable=False
                    )
                else:
                    # Resumable upload для больших файлов
                    media = MediaFileUpload(
                        file_path_or_object,
                        mimetype=mime_type,
                        resumable=True,
                        chunksize=1024*1024*5  # 5 MB chunks
                    )
            else:
                # File object - читаем в память
                file_content = file_path_or_object.read()
                file_size = len(file_content)
                use_simple_upload = file_size < SIMPLE_UPLOAD_THRESHOLD
                
                media = MediaIoBaseUpload(
                    io.BytesIO(file_content),
                    mimetype=mime_type,
                    resumable=not use_simple_upload,
                    chunksize=1024*1024*5 if not use_simple_upload else -1
                )
            
            # Загрузка
            if use_simple_upload:
                # Simple upload - один запрос
                file = self._execute_simple_upload(file_metadata, media, file_name)
            else:
                # Resumable upload для больших файлов
                try:
                    file = self._execute_resumable_upload(file_metadata, media, file_name)
                except (RedirectMissingLocation, Exception) as e:
                    # Fallback: если resumable upload падает с redirect ошибкой
                    # пробуем simple upload (пересоздав HTTP-соединение)
                    error_str = str(e).lower()
                    is_redirect_error = 'redirect' in error_str or isinstance(e, RedirectMissingLocation)
                    if is_redirect_error:
                        logger.warning(
                            f"Resumable upload failed with redirect error for {file_name}. "
                            f"File is {file_size/1024/1024:.2f}MB, "
                            f"rebuilding service connection and trying simple upload fallback..."
                        )
                        # Пересоздаём HTTP-клиент т.к. соединение corrupted
                        self._rebuild_service()
                        # Пересоздаём media stream для simple upload (не resumable)
                        if file_content is not None:
                            media = MediaIoBaseUpload(
                                io.BytesIO(file_content),
                                mimetype=mime_type,
                                resumable=False
                            )
                        elif isinstance(file_path_or_object, str):
                            with open(file_path_or_object, 'rb') as f:
                                file_content = f.read()
                            media = MediaIoBaseUpload(
                                io.BytesIO(file_content),
                                mimetype=mime_type,
                                resumable=False
                            )
                        else:
                            self._reset_media_stream(media)
                        file = self._execute_simple_upload(file_metadata, media, file_name)
                    else:
                        raise
            
            file_id = file.get('id')
            
            # Делаем файл доступным по ссылке
            self.set_file_public(file_id)
            
            upload_type = 'simple' if use_simple_upload else 'resumable'
            logger.info(f"Uploaded file to Google Drive ({upload_type}): {file_name} (ID: {file_id}, size: {file_size}) in folder {target_folder_id}")
            
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
        finally:
            # Удалить временный файл если создавался
            if tmp_path:
                try:
                    os.remove(tmp_path)
                except:
                    pass
    
    @retry_on_error()
    def _execute_simple_upload(self, file_metadata, media, file_name):
        """Выполнить простую загрузку одним запросом (для маленьких файлов)"""
        file = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, size, webViewLink, webContentLink'
        ).execute()
        logger.debug(f"Simple upload completed for {file_name}")
        return file
    
    def _execute_resumable_upload(self, file_metadata, media, file_name):
        """Выполнить resumable upload с retry логикой.
        
        CRITICAL: При retry после RedirectMissingLocation необходимо:
        1. Сбросить курсор BytesIO media stream в начало
        2. Пересоздать MediaIoBaseUpload с новым stream
        3. Ограничить общее число итераций (RESUMABLE_MAX_TOTAL_ATTEMPTS)
        """
        request = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, size, webViewLink, webContentLink'
        )
        
        response = None
        retries = 0
        total_attempts = 0
        while response is None:
            total_attempts += 1
            if total_attempts > RESUMABLE_MAX_TOTAL_ATTEMPTS:
                raise Exception(
                    f"Resumable upload for {file_name} exceeded {RESUMABLE_MAX_TOTAL_ATTEMPTS} "
                    f"total attempts ({retries} retries). Aborting."
                )
            try:
                status, response = request.next_chunk()
                if status:
                    logger.debug(f"Upload progress for {file_name}: {int(status.progress() * 100)}%")
            except HttpError as e:
                if e.resp.status in [500, 502, 503, 504] and retries < MAX_RETRIES:
                    retries += 1
                    delay = min(RETRY_DELAY_BASE * (2 ** retries), RETRY_DELAY_MAX)
                    delay += random.uniform(0, delay * 0.3)  # jitter
                    logger.warning(f"Upload error (attempt {retries}): {e}. Retrying in {delay:.1f}s...")
                    time.sleep(delay)
                else:
                    raise
            except RedirectMissingLocation as e:
                # CRITICAL: Google API иногда возвращает redirect без Location header
                # Это транзиентная ошибка, требующая полного пересоздания upload сессии
                if retries < MAX_RETRIES:
                    retries += 1
                    delay = min(RETRY_DELAY_BASE * (2 ** retries), RETRY_DELAY_MAX)
                    delay += random.uniform(0, delay * 0.3)  # jitter
                    logger.warning(
                        f"RedirectMissingLocation for {file_name} "
                        f"(attempt {retries}/{MAX_RETRIES}). "
                        f"Resetting stream and creating new upload session in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                    
                    # Сбросить media stream - критично для повторной попытки
                    stream_reset_ok = self._reset_media_stream(media)
                    if not stream_reset_ok:
                        logger.error(
                            f"Failed to reset media stream for {file_name}. "
                            f"Subsequent retry will likely fail."
                        )
                    
                    # Пересоздать request для новой resumable upload сессии
                    request = self.service.files().create(
                        body=file_metadata,
                        media_body=media,
                        fields='id, name, size, webViewLink, webContentLink'
                    )
                else:
                    logger.error(
                        f"RedirectMissingLocation persists after {MAX_RETRIES} retries "
                        f"for {file_name}. This indicates persistent Google API issues."
                    )
                    raise
            except Exception as e:
                error_str = str(e).lower()
                # Retry on network errors, redirects without location, and other transient issues
                retryable_errors = (
                    'timeout' in error_str or 
                    'connection' in error_str or
                    'redirect' in error_str or  # httplib2.error.RedirectMissingLocation
                    'location' in error_str or  # Missing Location header
                    'broken pipe' in error_str or
                    'reset by peer' in error_str
                )
                if retryable_errors and retries < MAX_RETRIES:
                    retries += 1
                    delay = min(RETRY_DELAY_BASE * (2 ** retries), RETRY_DELAY_MAX)
                    delay += random.uniform(0, delay * 0.3)  # jitter
                    logger.warning(f"Network/redirect error during upload (attempt {retries}): {e}. Retrying in {delay:.1f}s...")
                    time.sleep(delay)
                    # CRITICAL: сбросить курсор media stream перед пересозданием request
                    self._reset_media_stream(media)
                    # Recreate request for fresh resumable upload session
                    request = self.service.files().create(
                        body=file_metadata,
                        media_body=media,
                        fields='id, name, size, webViewLink, webContentLink'
                    )
                else:
                    raise
        
        return response
    
    @staticmethod
    def _reset_media_stream(media):
        """Сбросить позицию stream в media upload объекте.
        
        Решает RedirectMissingLocation: при retry после ошибки redirect
        курсор BytesIO уже в конце → пересозданный request отправляет пустые данные.
        
        Returns:
            bool: True если сброс успешен, False если не удалось
        """
        try:
            # MediaIoBaseUpload хранит stream в _fd
            if hasattr(media, '_fd') and hasattr(media._fd, 'seek'):
                current_pos = media._fd.tell()
                media._fd.seek(0)
                logger.debug(f"Reset media stream cursor: {current_pos} -> 0")
                return True
            # MediaFileUpload хранит stream в _file
            elif hasattr(media, '_file') and hasattr(media._file, 'seek'):
                current_pos = media._file.tell()
                media._file.seek(0)
                logger.debug(f"Reset media file cursor: {current_pos} -> 0")
                return True
            else:
                logger.warning("Could not reset media stream - no seekable attribute found")
                return False
        except Exception as e:
            logger.error(f"Failed to reset media stream: {e}")
            return False
    
    @retry_on_error()
    def set_file_public(self, file_id):
        """
        Сделать файл публичным (доступным по ссылке)
        
        Args:
            file_id: ID файла в Google Drive
        """
        permission = {
            'type': 'anyone',
            'role': 'reader'
        }
        
        self.service.permissions().create(
            fileId=file_id,
            body=permission
        ).execute()
        
        logger.debug(f"Set file {file_id} as public")

    @retry_on_error()
    def copy_file(self, file_id, parent_folder_id=None, new_name=None, make_public=True):
        """Скопировать файл в другую папку Google Drive.

        Используем для: шаблоны ДЗ → копии ДЗ (чтобы удаление шаблона не ломало назначенное).

        Args:
            file_id: исходный Google Drive fileId
            parent_folder_id: папка назначения (parents)
            new_name: новое имя файла (optional)
            make_public: сделать копию доступной по ссылке

        Returns:
            dict: {file_id, name, size, web_view_link, web_content_link}
        """
        body = {}
        if new_name:
            body['name'] = new_name
        if parent_folder_id:
            body['parents'] = [parent_folder_id]

        copied = self.service.files().copy(
            fileId=file_id,
            body=body,
            fields='id, name, size, webViewLink, webContentLink'
        ).execute()

        new_id = copied.get('id')
        if make_public and new_id:
            self.set_file_public(new_id)

        return {
            'file_id': new_id,
            'name': copied.get('name'),
            'size': int(copied.get('size', 0) or 0),
            'web_view_link': copied.get('webViewLink'),
            'web_content_link': copied.get('webContentLink'),
        }
    
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
    
    @retry_on_error()
    def delete_file(self, file_id):
        """
        Удалить файл из Google Drive
        
        Args:
            file_id: ID файла
        """
        self.service.files().delete(fileId=file_id).execute()
        logger.info(f"Deleted file from Google Drive: {file_id}")
    
    def file_exists(self, file_id):
        """
        Проверить существует ли файл в Google Drive.
        
        КРИТИЧЕСКИ ВАЖНО: Используется для верификации перед удалением записи с Zoom.
        
        Args:
            file_id: ID файла в Google Drive
            
        Returns:
            bool: True если файл существует и доступен
        """
        if not file_id:
            return False
        
        try:
            # Минимальный запрос - только id файла
            file = self.service.files().get(
                fileId=file_id,
                fields='id'
            ).execute()
            
            # Если получили ответ с id - файл существует
            return bool(file and file.get('id'))
            
        except HttpError as e:
            if e.resp.status == 404:
                logger.debug(f"File {file_id} not found on Google Drive")
                return False
            logger.error(f"Error checking file existence on Google Drive: {e}")
            return False
        except Exception as e:
            # Другие ошибки - логируем но возвращаем False для безопасности
            logger.error(f"Error checking file existence on Google Drive: {e}")
            return False
    
    @retry_on_error()
    def get_file_info(self, file_id):
        """
        Получить информацию о файле
        
        Args:
            file_id: ID файла
            
        Returns:
            dict: Информация о файле
        """
        file = self.service.files().get(
            fileId=file_id,
            fields='id, name, size, mimeType, createdTime, modifiedTime'
        ).execute()
        
        return file
    
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
    
    @retry_on_error()
    def get_drive_quota(self):
        """
        Получить информацию о квоте Google Drive
        
        Returns:
            dict: Информация о квоте с полями:
                - limit: лимит в байтах
                - usage: использовано в байтах
                - usage_in_drive: использовано в Drive
                - usage_in_trash: использовано в корзине
                - limit_gb: лимит в GB
                - usage_gb: использовано в GB
                - free_gb: свободно в GB
                - usage_percent: процент использования
        """
        try:
            about = self.service.about().get(fields='storageQuota').execute()
            quota = about.get('storageQuota', {})
            
            # Google Drive возвращает значения в байтах как строки
            limit = int(quota.get('limit', 0))
            usage = int(quota.get('usage', 0))
            usage_in_drive = int(quota.get('usageInDrive', 0))
            usage_in_trash = int(quota.get('usageInDriveTrash', 0))
            
            # Конвертация в GB
            limit_gb = round(limit / (1024 * 1024 * 1024), 2) if limit > 0 else 0
            usage_gb = round(usage / (1024 * 1024 * 1024), 2)
            free_gb = round((limit - usage) / (1024 * 1024 * 1024), 2) if limit > 0 else 0
            usage_percent = round((usage / limit) * 100, 1) if limit > 0 else 0
            
            return {
                'limit': limit,
                'usage': usage,
                'usage_in_drive': usage_in_drive,
                'usage_in_trash': usage_in_trash,
                'limit_gb': limit_gb,
                'usage_gb': usage_gb,
                'free_gb': free_gb,
                'usage_percent': usage_percent,
            }
            
        except Exception as e:
            logger.error(f"Failed to get Drive quota: {e}")
            return {
                'limit': 0,
                'usage': 0,
                'usage_in_drive': 0,
                'usage_in_trash': 0,
                'limit_gb': 0,
                'usage_gb': 0,
                'free_gb': 0,
                'usage_percent': 0,
                'error': str(e)
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
