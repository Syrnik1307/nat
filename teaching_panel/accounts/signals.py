from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import CustomUser, NotificationSettings


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
