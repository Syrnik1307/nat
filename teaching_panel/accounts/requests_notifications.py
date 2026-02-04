"""
Уведомления о новых регистрациях (заявках) в отдельный Telegram-канал.
Python 3.8 compatible.
"""
import logging
from typing import List, Optional, Tuple
from django.conf import settings
from django.contrib.auth import get_user_model

import requests

logger = logging.getLogger(__name__)


def _get_bot_config() -> Tuple[str, str]:
    """Возвращает (token, chat_id) для бота уведомлений о заявках."""
    token = getattr(settings, 'TELEGRAM_REQUESTS_BOT_TOKEN', '')
    chat_id = getattr(settings, 'TELEGRAM_REQUESTS_CHAT_ID', '')
    return token, chat_id


def _get_fallback_staff_chat_ids() -> List[str]:
    """Возвращает список chat_id для staff пользователей с привязанным Telegram."""
    User = get_user_model()
    chat_ids = list(
        User.objects.filter(is_staff=True, telegram_chat_id__isnull=False)
        .exclude(telegram_chat_id='')
        .values_list('telegram_chat_id', flat=True)
    )
    # Удаляем дубликаты с сохранением порядка
    seen = set()
    unique = []
    for cid in chat_ids:
        if cid in seen:
            continue
        seen.add(cid)
        unique.append(cid)
    return unique


def notify_new_registration(
    user_id: int,
    email: str,
    role: str,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    referral_code: Optional[str] = None,
    utm_source: Optional[str] = None,
    channel: Optional[str] = None,
) -> bool:
    """
    Отправляет уведомление о новой регистрации в Telegram.
    
    Returns:
        bool: True если сообщение отправлено успешно
    """
    token, chat_id = _get_bot_config()
    
    if not token:
        logger.warning('TELEGRAM_REQUESTS_BOT_TOKEN not configured, skipping registration notification')
        return False
    
    # Форматируем имя
    name_parts = []
    if first_name:
        name_parts.append(first_name)
    if last_name:
        name_parts.append(last_name)
    full_name = ' '.join(name_parts) or '—'
    
    # Роль на русском
    role_labels = {
        'teacher': 'Преподаватель',
        'student': 'Ученик',
        'admin': 'Администратор',
    }
    role_label = role_labels.get(role, role)
    
    # Источник
    source_parts = []
    if utm_source:
        source_parts.append(f"utm: {utm_source}")
    if referral_code:
        source_parts.append(f"ref: {referral_code}")
    if channel:
        source_parts.append(f"channel: {channel}")
    source_info = ', '.join(source_parts) if source_parts else '—'
    
    message = (
        f"Новая регистрация\n\n"
        f"ID: {user_id}\n"
        f"Email: {email}\n"
        f"Имя: {full_name}\n"
        f"Роль: {role_label}\n"
        f"Источник: {source_info}"
    )
    
    target_chat_ids = [chat_id] if chat_id else []
    if not target_chat_ids:
        try:
            target_chat_ids = _get_fallback_staff_chat_ids()
        except Exception as exc:
            logger.warning('Failed to resolve staff chat ids for registration alerts: %s', exc)
            target_chat_ids = []

    if not target_chat_ids:
        logger.warning('No Telegram chat_id configured for registration notifications')
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload_base = {
        'text': message,
        'disable_web_page_preview': True,
    }

    sent_any = False
    for target_chat_id in target_chat_ids:
        payload = {**payload_base, 'chat_id': target_chat_id}
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.ok:
                sent_any = True
            else:
                logger.warning('Failed to send registration notification: %s %s', response.status_code, response.text)
        except requests.RequestException as exc:
            logger.warning('Failed to send registration notification: %s', exc)

    if sent_any:
        logger.info('Registration notification sent for user %s', user_id)
        return True
    return False
