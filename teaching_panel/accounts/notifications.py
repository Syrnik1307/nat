"""Helper utilities for user notification delivery."""
from datetime import timedelta
import logging
from typing import Dict

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


NOTIFICATION_FIELD_MAP: Dict[str, str] = {
    # Базовые — учителю
    'homework_submitted': 'notify_homework_submitted',
    'subscription_expiring': 'notify_subscription_expiring',
    'payment_success': 'notify_payment_success',

    # Базовые — ученику
    'homework_graded': 'notify_homework_graded',
    'homework_deadline': 'notify_homework_deadline',
    'lesson_reminder': 'notify_lesson_reminders',
    'new_homework': 'notify_new_homework',

    # Аналитика — учителю
    'absence_alert': 'notify_absence_alert',
    'performance_drop_alert': 'notify_performance_drop',
    'group_health_alert': 'notify_group_health',
    'grading_backlog': 'notify_grading_backlog',
    'inactive_student_alert': 'notify_inactive_student',

    # Аналитика — ученику
    'student_absence_warning': 'notify_student_absence_warning',
    'control_point_deadline': 'notify_control_point_deadline',
    'achievement': 'notify_achievement',
    'student_inactivity_nudge': 'notify_inactivity_nudge',

    # Хранилище (совместимость)
    'storage_quota_warning': 'notify_lesson_reminders',
    'storage_quota_exceeded': 'notify_lesson_reminders',
    'storage_warning': 'notify_lesson_reminders',
    'storage_limit_exceeded': 'notify_lesson_reminders',
    'recording_available': 'notify_lesson_reminders',
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


def send_telegram_to_group_chat(chat_id: str, message: str, *, notification_source: str = 'lesson_reminder', disable_web_page_preview: bool = True, silent: bool = False) -> bool:
    """Отправляет сообщение в Telegram-группу по chat_id.
    
    Args:
        chat_id: ID группового чата в Telegram (может начинаться с '-')
        message: Текст сообщения
        notification_source: Источник уведомления для логирования
        disable_web_page_preview: Отключить превью ссылок
        silent: Отправить без звука
        
    Returns:
        bool: True если сообщение успешно отправлено
    """
    if not chat_id:
        logger.warning('send_telegram_to_group_chat: chat_id is empty')
        return False
    
    token = _get_bot_token()
    if not token:
        logger.warning('Telegram bot token is not configured. Skipping group notification.')
        return False
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown',
        'disable_web_page_preview': disable_web_page_preview,
        'disable_notification': silent,
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.ok:
            logger.info('Telegram group message sent to %s (%s)', chat_id, notification_source)
            return True
        else:
            error_text = response.text[:500]
            logger.warning('Telegram API error for group %s: %s - %s', chat_id, response.status_code, error_text)
            return False
    except requests.RequestException as exc:
        logger.exception('Failed to send Telegram group notification to %s (%s): %s', chat_id, notification_source, exc)
        return False
