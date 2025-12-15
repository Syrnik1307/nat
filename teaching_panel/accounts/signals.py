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
    """
    НЕ создаём папку при регистрации учителя.
    Папка создаётся только при активации оплаченной подписки (см. payments_service.py).
    Этот сигнал оставлен для логирования.
    """
    if not created or instance.role != 'teacher':
        return
    
    logger.info(f"Teacher {instance.email} registered. GDrive folder will be created upon subscription activation.")
