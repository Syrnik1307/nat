import os
from typing import Optional

import requests
from django.conf import settings

from accounts.models import CustomUser, NotificationSettings


def _safe_chat_id_for_user(user: CustomUser) -> Optional[str]:
    chat_id = (str(getattr(user, 'telegram_chat_id', '') or '')).strip()
    if chat_id:
        return chat_id
    telegram_id = (str(getattr(user, 'telegram_id', '') or '')).strip()
    return telegram_id or None


def notify_admins_new_message(*, ticket, message) -> None:
    """Уведомить админов/поддержку о новом сообщении пользователя."""
    token = os.getenv('SUPPORT_BOT_TOKEN')
    if not token:
        return

    if ticket.assigned_to and ticket.assigned_to.telegram_id:
        admins = [ticket.assigned_to]
    else:
        admins = list(CustomUser.objects.filter(is_staff=True, telegram_id__isnull=False))

    if not admins:
        return

    user_info = ticket.user.get_full_name() if ticket.user else (ticket.email or 'Пользователь')

    text = (
        f"💬 *Новое сообщение в тикете #{ticket.id}*\n\n"
        f"📝 *Тема:* {ticket.subject}\n"
        f"👤 *От:* {user_info}\n"
        f"💌 *Сообщение:*\n{message.message[:300]}{'...' if len(message.message) > 300 else ''}\n\n"
        f"Для ответа: /view\\_{ticket.id}"
    )

    for admin in admins:
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            data = {
                'chat_id': admin.telegram_id,
                'text': text,
                'parse_mode': 'Markdown',
            }
            requests.post(url, json=data, timeout=5)
        except Exception:
            # Best-effort only
            continue


def notify_user_staff_reply(*, ticket, message) -> None:
    """Отправить пользователю ответ поддержки в Telegram (если привязан)."""
    user = getattr(ticket, 'user', None)
    if not user:
        return

    chat_id = _safe_chat_id_for_user(user)
    if not chat_id:
        return

    try:
        settings_obj = NotificationSettings.objects.get(user=user)
        if not settings_obj.telegram_enabled:
            return
    except Exception:
        # Если настроек нет — не блокируем поддержку
        pass

    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '') or os.getenv('TELEGRAM_BOT_TOKEN', '')
    if not token:
        return

    text = (
        f"🛟 *Поддержка ответила по тикету #{ticket.id}*\n\n"
        f"{message.message[:350]}{'...' if len(message.message) > 350 else ''}\n\n"
        "Чтобы продолжить диалог — просто ответьте следующим сообщением.\n"
        "Закрыть обращение: /close"
    )

    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'Markdown',
            'disable_web_page_preview': True,
        }
        requests.post(url, json=data, timeout=5)
    except Exception:
        return
