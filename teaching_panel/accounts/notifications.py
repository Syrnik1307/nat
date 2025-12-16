"""Helper utilities for user notification delivery."""
from datetime import timedelta
import logging
from typing import Dict

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


NOTIFICATION_FIELD_MAP: Dict[str, str] = {
    'homework_submitted': 'notify_homework_submitted',
    'homework_graded': 'notify_homework_graded',
    'homework_deadline': 'notify_homework_deadline',
    'subscription_expiring': 'notify_subscription_expiring',
    'payment_success': 'notify_payment_success',
    'lesson_reminder': 'notify_lesson_reminders',
    'new_homework': 'notify_new_homework',
    'storage_quota_warning': 'notify_lesson_reminders',  # Используем существующее поле
    'storage_quota_exceeded': 'notify_lesson_reminders',  # Используем существующее поле

    # Исторические/альтернативные имена типов (используются в некоторых задачах)
    'storage_warning': 'notify_lesson_reminders',
    'storage_limit_exceeded': 'notify_lesson_reminders',
}


def _get_bot_token() -> str:
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
    if not token or token == 'YOUR_BOT_TOKEN_HERE':
        return ''
    return token


def send_telegram_notification(user, notification_type: str, message: str, *, disable_web_page_preview: bool = True, silent: bool = False) -> bool:
    """Send a Telegram message respecting user notification preferences."""
    from .models import NotificationSettings, NotificationLog
    
    if not user:
        return False

    token = _get_bot_token()
    if not token:
        logger.warning('Telegram bot token is not configured. Skipping notification %s', notification_type)
        NotificationLog.objects.create(
            user=user,
            notification_type=notification_type,
            channel='telegram',
            status='skipped',
            message=message,
            error_message='TELEGRAM_BOT_TOKEN not configured'
        )
        return False

    settings_obj, _ = NotificationSettings.objects.get_or_create(user=user)
    field_name = NOTIFICATION_FIELD_MAP.get(notification_type)

    if not settings_obj.telegram_enabled:
        NotificationLog.objects.create(
            user=user,
            notification_type=notification_type,
            channel='telegram',
            status='skipped',
            message=message,
            error_message='Telegram notifications disabled by user'
        )
        return False

    if field_name and not getattr(settings_obj, field_name, True):
        NotificationLog.objects.create(
            user=user,
            notification_type=notification_type,
            channel='telegram',
            status='skipped',
            message=message,
            error_message=f'{field_name} disabled'
        )
        return False

    if not user.telegram_chat_id:
        NotificationLog.objects.create(
            user=user,
            notification_type=notification_type,
            channel='telegram',
            status='skipped',
            message=message,
            error_message='Missing telegram_chat_id'
        )
        return False

    # Dedupe: avoid sending identical notifications repeatedly due to retries / double-dispatch
    # (e.g., Celery task + synchronous fallback).
    dedupe_window = timezone.now() - timedelta(minutes=2)
    if NotificationLog.objects.filter(
        user=user,
        notification_type=notification_type,
        channel='telegram',
        status='sent',
        message=message,
        created_at__gte=dedupe_window,
    ).exists():
        NotificationLog.objects.create(
            user=user,
            notification_type=notification_type,
            channel='telegram',
            status='skipped',
            message=message,
            error_message='Deduped: identical recent notification'
        )
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': user.telegram_chat_id,
        'text': message,
        'parse_mode': 'Markdown',
        'disable_web_page_preview': disable_web_page_preview,
        'disable_notification': silent,
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.ok:
            NotificationLog.objects.create(
                user=user,
                notification_type=notification_type,
                channel='telegram',
                status='sent',
                message=message,
            )
            return True
        NotificationLog.objects.create(
            user=user,
            notification_type=notification_type,
            channel='telegram',
            status='failed',
            message=message,
            error_message=response.text[:500],
        )
        logger.warning('Telegram API returned %s: %s', response.status_code, response.text)
        return False
    except requests.RequestException as exc:
        NotificationLog.objects.create(
            user=user,
            notification_type=notification_type,
            channel='telegram',
            status='failed',
            message=message,
            error_message=str(exc)
        )
        logger.exception('Failed to send Telegram notification: %s', exc)
        return False
