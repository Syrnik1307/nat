"""
Уведомления о новых регистрациях (заявках) в отдельный Telegram-канал.
Python 3.8 compatible.
"""
import logging
from typing import Optional, Tuple
from django.conf import settings

import requests

logger = logging.getLogger(__name__)


def _get_bot_config() -> Tuple[str, str]:
    """Возвращает (token, chat_id) для бота уведомлений о заявках."""
    token = getattr(settings, 'TELEGRAM_REQUESTS_BOT_TOKEN', '')
    chat_id = getattr(settings, 'TELEGRAM_REQUESTS_CHAT_ID', '')
    return token, chat_id


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
    
    if not token or not chat_id:
        logger.debug('TELEGRAM_REQUESTS_BOT not configured, skipping registration notification')
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
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message,
        'disable_web_page_preview': True,
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.ok:
            logger.info(f'Registration notification sent for user {user_id}')
            return True
        logger.warning(f'Failed to send registration notification: {response.status_code}')
        return False
    except requests.RequestException as exc:
        logger.warning(f'Failed to send registration notification: {exc}')
        return False
