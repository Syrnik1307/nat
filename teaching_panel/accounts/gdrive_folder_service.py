"""
Google Drive Folder Service for Teacher Storage

Manages teacher folders on Google Drive:
- Creates folder structure when subscription is activated
- Calculates storage usage
- Enforces storage limits
"""
import logging
from django.conf import settings
from decimal import Decimal

logger = logging.getLogger(__name__)


def get_gdrive_manager():
    """Lazy import to avoid circular dependencies"""
    from schedule.gdrive_utils import get_gdrive_manager as get_manager
    return get_manager()


def create_teacher_folder_on_subscription(subscription):
    """
    Создать папку учителя на Google Drive при активации подписки.
    
    Структура:
    📁 lectio.space (GDRIVE_ROOT_FOLDER_ID)
       └── 📁 Teacher_{id}_{FirstName}_{LastName}
           ├── 📁 Recordings (записи уроков)
           ├── 📁 Homework (материалы ДЗ)
           ├── 📁 Materials (материалы уроков)
           └── 📁 Students (данные учеников)
    
    Args:
        subscription: Subscription instance with active status
        
    Returns:
        str: ID созданной папки или None при ошибке
    """
    if not settings.USE_GDRIVE_STORAGE or not settings.GDRIVE_ROOT_FOLDER_ID:
        logger.warning("Google Drive storage not configured, skipping folder creation")
        return None
    
    user = subscription.user
    
    if user.role != 'teacher':
        logger.warning(f"User {user.email} is not a teacher, skipping folder creation")
        return None
    
    # Если папка уже создана - используем существующую
    if subscription.gdrive_folder_id:
        logger.info(f"Teacher {user.email} already has GDrive folder: {subscription.gdrive_folder_id}")
        return subscription.gdrive_folder_id
    
    try:
        gdrive = get_gdrive_manager()
        
        # Формируем имя папки
        first_name = (user.first_name or 'User').replace(' ', '_')
        last_name = (user.last_name or '').replace(' ', '_')
        folder_name = f"Teacher_{user.id}_{first_name}_{last_name}"
        
        # Проверяем, нет ли уже такой папки (на случай миграции)
        existing_folder_id = _find_existing_teacher_folder(gdrive, folder_name)
        
        if existing_folder_id:
            logger.info(f"Found existing folder for {user.email}: {existing_folder_id}")
            teacher_folder_id = existing_folder_id
        else:
            # Создаём главную папку учителя
            teacher_folder_id = gdrive.create_folder(
                folder_name,
                parent_folder_id=settings.GDRIVE_ROOT_FOLDER_ID
            )
            logger.info(f"Created GDrive folder for {user.email}: {teacher_folder_id}")
        
        # Создаём подпапки
        for subfolder in ['Recordings', 'Homework', 'Materials', 'Students']:
            try:
                _get_or_create_subfolder(gdrive, subfolder, teacher_folder_id)
            except Exception as e:
                logger.warning(f"Failed to create subfolder {subfolder}: {e}")
        
        # Сохраняем ID папки в подписку
        subscription.gdrive_folder_id = teacher_folder_id
        subscription.save(update_fields=['gdrive_folder_id', 'updated_at'])
        
        logger.info(f"GDrive folder setup complete for {user.email}")
        return teacher_folder_id
        
    except Exception as e:
        logger.exception(f"Failed to create GDrive folder for {user.email}: {e}")
        return None


def _find_existing_teacher_folder(gdrive, folder_name):
    """Поиск существующей папки учителя"""
    try:
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if settings.GDRIVE_ROOT_FOLDER_ID:
            query += f" and '{settings.GDRIVE_ROOT_FOLDER_ID}' in parents"
        
        results = gdrive.service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)'
        ).execute()
        
        items = results.get('files', [])
        return items[0]['id'] if items else None
        
    except Exception as e:
        logger.warning(f"Error searching for folder {folder_name}: {e}")
        return None


def _get_or_create_subfolder(gdrive, folder_name, parent_id):
    """Получить или создать подпапку"""
    try:
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        query += f" and '{parent_id}' in parents"
        
        results = gdrive.service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)'
        ).execute()
        
        items = results.get('files', [])
        
        if items:
            return items[0]['id']
        else:
            return gdrive.create_folder(folder_name, parent_id)
            
    except Exception as e:
        logger.error(f"Failed to get/create subfolder {folder_name}: {e}")
        return parent_id


def get_teacher_storage_usage(subscription):
    """
    Получить реальное использование хранилища учителем с Google Drive.
    
    Args:
        subscription: Subscription instance
        
    Returns:
        dict: {
            'used_bytes': int,
            'used_gb': float,
            'limit_gb': int,
            'available_gb': float,
            'usage_percent': float,
            'file_count': int,
            'breakdown': {
                'recordings': {'size': bytes, 'files': count},
                'homework': {'size': bytes, 'files': count},
                ...
            }
        }
    """
    if not subscription.gdrive_folder_id:
        return {
            'used_bytes': 0,
            'used_gb': 0.0,
            'limit_gb': subscription.total_storage_gb,
            'available_gb': float(subscription.total_storage_gb),
            'usage_percent': 0.0,
            'file_count': 0,
            'breakdown': {}
        }
    
    try:
        gdrive = get_gdrive_manager()
        stats = gdrive.calculate_folder_size(subscription.gdrive_folder_id)
        
        total_bytes = stats.get('total_size', 0)
        total_gb = total_bytes / (1024 ** 3)
        limit_gb = subscription.total_storage_gb
        available_gb = max(0, limit_gb - total_gb)
        usage_percent = (total_gb / limit_gb * 100) if limit_gb > 0 else 0
        
        # Обновляем used_storage_gb в модели
        subscription.used_storage_gb = Decimal(str(round(total_gb, 2)))
        subscription.save(update_fields=['used_storage_gb', 'updated_at'])
        
        return {
            'used_bytes': total_bytes,
            'used_gb': round(total_gb, 2),
            'limit_gb': limit_gb,
            'available_gb': round(available_gb, 2),
            'usage_percent': round(usage_percent, 1),
            'file_count': stats.get('file_count', 0),
            'breakdown': {}  # Можно добавить детализацию по подпапкам
        }
        
    except Exception as e:
        logger.exception(f"Failed to get storage usage for subscription {subscription.id}: {e}")
        return {
            'used_bytes': 0,
            'used_gb': float(subscription.used_storage_gb),
            'limit_gb': subscription.total_storage_gb,
            'available_gb': float(subscription.total_storage_gb - subscription.used_storage_gb),
            'usage_percent': float(subscription.used_storage_gb / subscription.total_storage_gb * 100) if subscription.total_storage_gb > 0 else 0,
            'file_count': 0,
            'breakdown': {},
            'error': str(e)
        }


def check_storage_limit(subscription, file_size_bytes):
    """
    Проверить, хватает ли места для загрузки файла.
    
    Args:
        subscription: Subscription instance
        file_size_bytes: размер файла в байтах
        
    Returns:
        tuple: (allowed: bool, message: str)
    """
    usage = get_teacher_storage_usage(subscription)
    
    file_size_gb = file_size_bytes / (1024 ** 3)
    
    if usage['available_gb'] >= file_size_gb:
        return True, ""
    else:
        return False, f"Недостаточно места. Доступно: {usage['available_gb']:.2f} ГБ, требуется: {file_size_gb:.2f} ГБ"


def get_teacher_folder_link(subscription):
    """
    Получить ссылку на папку учителя в Google Drive.
    
    Returns:
        str: URL или None
    """
    if subscription.gdrive_folder_id:
        return f"https://drive.google.com/drive/folders/{subscription.gdrive_folder_id}"
    return None
