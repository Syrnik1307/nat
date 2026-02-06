from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
import logging

from .models import CustomUser, NotificationSettings

logger = logging.getLogger(__name__)


@receiver(post_save, sender=CustomUser)
def ensure_notification_settings(sender, instance, created, **kwargs):
    """Гарантируем, что у каждого пользователя есть настройки уведомлений.
    
    SECURITY FIX: Убрали hasattr() проверку - она не thread-safe и создавала
    race condition при параллельных запросах. get_or_create() уже атомарен.
    """
    if not instance:
        return
    # get_or_create использует SELECT FOR UPDATE внутренне, что предотвращает race conditions
    try:
        NotificationSettings.objects.get_or_create(user=instance)
    except Exception as e:
        # Логируем ошибку, но не прерываем сохранение пользователя
        logger.warning(f"Failed to ensure NotificationSettings for user {instance.id}: {e}")


@receiver(post_save, sender=CustomUser)
def create_teacher_gdrive_folder(sender, instance, created, **kwargs):
    """
    НЕ создаём папку при регистрации учителя.
    Папка создаётся только при активации оплаченной подписки (см. payments_service.py).
    Этот сигнал оставлен для логирования.
    """
    if not created or instance.role != 'teacher':
        return
    
    logger.info(f"Teacher {instance.email} registered. GDrive folder will be created upon subscription activation.")
