from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
import logging

from .models import CustomUser, NotificationSettings

logger = logging.getLogger(__name__)


@receiver(post_save, sender=CustomUser)
def ensure_notification_settings(sender, instance, created, **kwargs):
    """Гарантируем, что у каждого пользователя есть настройки уведомлений."""
    if not instance:
        return
    if created:
        NotificationSettings.objects.get_or_create(user=instance)
    else:
        # Для существующих пользователей убеждаемся, что запись тоже присутствует
        if not hasattr(instance, 'notification_settings'):
            NotificationSettings.objects.get_or_create(user=instance)


@receiver(post_save, sender=CustomUser)
def create_teacher_gdrive_folder(sender, instance, created, **kwargs):
    """Автоматически создать папку учителя в Google Drive при регистрации."""
    if not created or instance.role != 'teacher':
        return
    
    # Проверяем, что Google Drive включен
    if not settings.USE_GDRIVE_STORAGE or not settings.GDRIVE_ROOT_FOLDER_ID:
        return
    
    try:
        from schedule.gdrive_utils import get_gdrive_manager
        
        gdrive = get_gdrive_manager()
        
        # Создаём папку для учителя
        teacher_folder_name = f"teacher_{instance.id}_{instance.first_name}_{instance.last_name}"
        teacher_folder_id = gdrive.create_folder(
            teacher_folder_name,
            parent_folder_id=settings.GDRIVE_ROOT_FOLDER_ID
        )
        
        # Создаём подпапки
        gdrive.create_folder('Recordings', parent_folder_id=teacher_folder_id)
        gdrive.create_folder('Homework', parent_folder_id=teacher_folder_id)
        gdrive.create_folder('Materials', parent_folder_id=teacher_folder_id)
        gdrive.create_folder('Students', parent_folder_id=teacher_folder_id)
        
        # Сохраняем ID папки в модель
        instance.gdrive_folder_id = teacher_folder_id
        instance.save(update_fields=['gdrive_folder_id'])
        
        logger.info(f"Created Google Drive folder for teacher {instance.email} (ID: {teacher_folder_id})")
        
    except Exception as e:
        logger.error(f"Failed to create Google Drive folder for teacher {instance.email}: {e}")
