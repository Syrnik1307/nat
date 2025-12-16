"""Celery tasks for subscription maintenance and notifications."""
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from .models import Subscription, NotificationLog
from .notifications import send_telegram_notification

REMINDER_DAYS = 3
REMINDER_COOLDOWN_HOURS = 24


@shared_task
def check_expiring_subscriptions():
    """Send Telegram reminders to teachers when their subscription is about to expire."""
    now = timezone.now()
    window_end = now + timedelta(days=REMINDER_DAYS)

    subscriptions = (
        Subscription.objects.select_related('user')
        .filter(
            status=Subscription.STATUS_ACTIVE,
            expires_at__isnull=False,
            expires_at__lte=window_end,
            expires_at__gte=now,
        )
    )

    sent = 0
    for sub in subscriptions:
        user = sub.user
        if not user:
            continue

        # Skip if we already notified the user recently
        recently_notified = NotificationLog.objects.filter(
            user=user,
            notification_type='subscription_expiring',
            created_at__gte=now - timedelta(hours=REMINDER_COOLDOWN_HOURS),
        ).exists()
        if recently_notified:
            continue

        days_left = max((sub.expires_at - now).days, 0)
        message = (
            "⚠️ Подписка Teaching Panel скоро истекает!\n"
            f"Осталось: {days_left} дн., до {sub.expires_at.strftime('%d.%m.%Y')}\n"
            "Продлите подписку, чтобы не потерять доступ к урокам и записям."
        )

        if send_telegram_notification(user, 'subscription_expiring', message):
            sent += 1

    return {
        'checked': subscriptions.count(),
        'sent': sent,
        'timestamp': now.isoformat(),
    }


@shared_task
def process_expired_subscriptions():
    """Mark subscriptions as expired once their expiration date has passed."""
    now = timezone.now()
    expired_qs = Subscription.objects.filter(
        expires_at__lt=now,
        status__in=[Subscription.STATUS_ACTIVE, Subscription.STATUS_PENDING],
    )
    updated = expired_qs.update(status=Subscription.STATUS_EXPIRED, auto_renew=False)

    return {
        'updated': updated,
        'timestamp': now.isoformat(),
    }


STORAGE_WARNING_THRESHOLD_PERCENT = 90
STORAGE_LIMIT_COOLDOWN_HOURS = 24


@shared_task
def sync_teacher_storage_usage():
    """
    Периодически пересчитывает использование хранилища для всех учителей.
    
    Запускается 4 раза в день (каждые 6 часов).
    При превышении лимита отправляет уведомление учителю.
    """
    import logging
    from decimal import Decimal
    from django.conf import settings
    from django.contrib.auth import get_user_model
    
    logger = logging.getLogger(__name__)
    now = timezone.now()
    
    # Проверяем что Google Drive включен
    if not getattr(settings, 'USE_GDRIVE_STORAGE', False):
        logger.info("[Celery] sync_teacher_storage_usage: Google Drive storage disabled")
        return {'status': 'disabled', 'reason': 'USE_GDRIVE_STORAGE=False'}
    
    User = get_user_model()
    teachers = User.objects.filter(role='teacher', is_active=True)
    
    updated = 0
    warnings_sent = 0
    errors = 0
    
    for teacher in teachers:
        try:
            subscription = getattr(teacher, 'subscription', None)
            if not subscription:
                continue
            
            # Пропускаем если нет папки на Google Drive
            if not subscription.gdrive_folder_id:
                continue
            
            # Получаем реальный размер с Google Drive
            from .gdrive_folder_service import get_teacher_storage_usage
            storage_stats = get_teacher_storage_usage(subscription)
            
            if 'error' in storage_stats:
                logger.warning(f"Failed to get storage for teacher {teacher.id}: {storage_stats.get('error')}")
                errors += 1
                continue
            
            # used_storage_gb уже обновлён внутри get_teacher_storage_usage
            updated += 1
            
            # Проверяем лимит и отправляем уведомление
            usage_percent = storage_stats.get('usage_percent', 0)
            
            if usage_percent >= 100:
                # Лимит исчерпан — уведомляем
                _notify_storage_limit_exceeded(teacher, subscription, storage_stats)
                warnings_sent += 1
            elif usage_percent >= STORAGE_WARNING_THRESHOLD_PERCENT:
                # Приближается к лимиту — предупреждаем
                _notify_storage_warning(teacher, subscription, storage_stats)
                warnings_sent += 1
                
        except Exception as e:
            logger.exception(f"Error syncing storage for teacher {teacher.id}: {e}")
            errors += 1
    
    logger.info(f"[Celery] sync_teacher_storage_usage: updated={updated}, warnings={warnings_sent}, errors={errors}")
    
    return {
        'updated': updated,
        'warnings_sent': warnings_sent,
        'errors': errors,
        'timestamp': now.isoformat(),
    }


def _notify_storage_limit_exceeded(teacher, subscription, stats):
    """Отправляет уведомление о превышении лимита хранилища."""
    now = timezone.now()
    
    # Проверяем cooldown (не спамим)
    recently_notified = NotificationLog.objects.filter(
        user=teacher,
        notification_type='storage_limit_exceeded',
        created_at__gte=now - timedelta(hours=STORAGE_LIMIT_COOLDOWN_HOURS),
    ).exists()
    
    if recently_notified:
        return False
    
    used_gb = stats.get('used_gb', 0)
    limit_gb = stats.get('limit_gb', 10)
    
    message = (
        "🚨 Хранилище заполнено!\n\n"
        f"Использовано: {used_gb:.2f} ГБ из {limit_gb} ГБ (100%)\n\n"
        "Новые записи уроков не будут сохраняться.\n"
        "Удалите старые записи или докупите место в настройках подписки."
    )
    
    send_telegram_notification(teacher, 'storage_limit_exceeded', message)
    return True


def _notify_storage_warning(teacher, subscription, stats):
    """Отправляет предупреждение о приближении к лимиту (90%+)."""
    now = timezone.now()
    
    # Проверяем cooldown
    recently_notified = NotificationLog.objects.filter(
        user=teacher,
        notification_type='storage_warning',
        created_at__gte=now - timedelta(hours=STORAGE_LIMIT_COOLDOWN_HOURS * 2),  # 48 часов для предупреждений
    ).exists()
    
    if recently_notified:
        return False
    
    used_gb = stats.get('used_gb', 0)
    limit_gb = stats.get('limit_gb', 10)
    available_gb = stats.get('available_gb', 0)
    usage_percent = stats.get('usage_percent', 0)
    
    message = (
        "⚠️ Хранилище почти заполнено!\n\n"
        f"Использовано: {used_gb:.2f} ГБ из {limit_gb} ГБ ({usage_percent:.0f}%)\n"
        f"Осталось: {available_gb:.2f} ГБ\n\n"
        "Рекомендуем удалить старые записи или докупить место."
    )
    
    send_telegram_notification(teacher, 'storage_warning', message)
    return True
