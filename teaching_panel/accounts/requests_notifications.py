"""
Уведомления о заявках (регистрациях новых пользователей)

Отправляет уведомления в отдельный Telegram-канал о новых регистрациях.
Токен бота: TELEGRAM_REQUESTS_BOT_TOKEN
Chat ID: TELEGRAM_REQUESTS_CHAT_ID
"""
import logging
import os
from typing import Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _get_bot_config() -> tuple[str, str]:
    """Получить токен бота и chat_id для уведомлений о заявках"""
    token = getattr(settings, 'TELEGRAM_REQUESTS_BOT_TOKEN', '') or os.environ.get('TELEGRAM_REQUESTS_BOT_TOKEN', '')
    chat_id = getattr(settings, 'TELEGRAM_REQUESTS_CHAT_ID', '') or os.environ.get('TELEGRAM_REQUESTS_CHAT_ID', '')
    return token, chat_id


def _iter_fallback_admin_chat_ids():
    """Fallback: отправка напрямую всем staff с telegram_id.

    Важно: импортируем модель лениво, чтобы не зацепить Django на import-time.
    """
    try:
        from accounts.models import CustomUser

        qs = CustomUser.objects.filter(is_staff=True, telegram_id__isnull=False).exclude(telegram_id='')
        for u in qs.iterator():
            telegram_id = str(getattr(u, 'telegram_id', '') or '').strip()
            if telegram_id:
                yield telegram_id
    except Exception:
        return


def _send_message(*, token: str, chat_id: str, text: str) -> bool:
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'Markdown',
            'disable_web_page_preview': True,
        }
        response = requests.post(url, json=data, timeout=5)

        if response.status_code == 200:
            return True

        logger.warning(f"[RequestsBot] Failed to send notification: {response.status_code}")
        return False
    except Exception as e:
        logger.error(f"[RequestsBot] Error sending notification: {e}")
        return False


def notify_new_registration(
    *,
    user_id: int,
    email: str,
    role: str,
    first_name: str = '',
    last_name: str = '',
    referral_code: str = '',
    utm_source: str = '',
    channel: str = '',
) -> bool:
    """
    Отправить уведомление о новой регистрации пользователя.
    
    Args:
        user_id: ID нового пользователя
        email: Email пользователя
        role: Роль (student, teacher, admin)
        first_name: Имя
        last_name: Фамилия
        referral_code: Реферальный код (если был использован)
        utm_source: UTM source (если есть)
        channel: Канал привлечения
    
    Returns:
        True если уведомление отправлено успешно
    """
    token, chat_id = _get_bot_config()
    
    if not token:
        logger.debug("[RequestsBot] Token not configured, skipping notification")
        return False
    
    # Формируем сообщение
    role_emoji = {
        'student': '🎓',
        'teacher': '👨‍🏫',
        'admin': '⚙️',
    }.get(role, '👤')
    
    role_name = {
        'student': 'Ученик',
        'teacher': 'Учитель',
        'admin': 'Администратор',
    }.get(role, role)
    
    # Собираем имя
    full_name = ' '.join(filter(None, [first_name, last_name])) or 'Не указано'
    
    # Формируем текст сообщения
    lines = [
        f"🆕 *Новая регистрация*",
        "",
        f"{role_emoji} *Роль:* {role_name}",
        f"📧 *Email:* `{email}`",
        f"👤 *Имя:* {full_name}",
        f"🔑 *ID:* {user_id}",
    ]
    
    # Добавляем источник трафика если есть
    if referral_code:
        lines.append(f"🎁 *Реферал:* {referral_code}")
    if utm_source:
        lines.append(f"📊 *UTM Source:* {utm_source}")
    if channel:
        lines.append(f"📣 *Канал:* {channel}")
    
    # Для учителей добавляем пометку
    if role == 'teacher':
        lines.append("")
        lines.append("💼 _Потенциальный клиент!_")
    
    text = '\n'.join(lines)
    
    if chat_id:
        ok = _send_message(token=token, chat_id=chat_id, text=text)
        if ok:
            logger.info(f"[RequestsBot] Notification sent for user {email}")
        return ok

    # Fallback: отправка всем staff (если TELEGRAM_REQUESTS_CHAT_ID не настроен)
    any_ok = False
    for admin_chat_id in _iter_fallback_admin_chat_ids():
        any_ok = _send_message(token=token, chat_id=admin_chat_id, text=text) or any_ok
    if any_ok:
        logger.info(f"[RequestsBot] Notification sent (fallback) for user {email}")
    return any_ok


def notify_teacher_trial_started(
    *,
    user_id: int,
    email: str,
    first_name: str = '',
    last_name: str = '',
    trial_days: int = 14,
) -> bool:
    """
    Уведомление о старте пробного периода учителя.
    
    Используется когда учитель активирует пробную подписку.
    """
    token, chat_id = _get_bot_config()
    
    if not token:
        return False
    
    full_name = ' '.join(filter(None, [first_name, last_name])) or 'Не указано'
    
    text = (
        f"🎯 *Учитель начал пробный период*\n\n"
        f"👨‍🏫 *Имя:* {full_name}\n"
        f"📧 *Email:* `{email}`\n"
        f"⏱️ *Дней:* {trial_days}\n"
        f"🔑 *ID:* {user_id}\n\n"
        f"_Возможно стоит связаться для онбординга_"
    )
    
    if chat_id:
        return _send_message(token=token, chat_id=chat_id, text=text)

    any_ok = False
    for admin_chat_id in _iter_fallback_admin_chat_ids():
        any_ok = _send_message(token=token, chat_id=admin_chat_id, text=text) or any_ok
    return any_ok
