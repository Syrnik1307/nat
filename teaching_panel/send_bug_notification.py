#!/usr/bin/env python
"""
Скрипт для отправки уведомления пользователям о баге в боте поддержки.
Отправляет сообщение всем пользователям с привязанным Telegram.

Использование:
    python send_bug_notification.py              # Отправить всем
    python send_bug_notification.py --dry-run    # Показать кому отправится (без отправки)
"""

import os
import sys
import asyncio
import argparse

# Настройка Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')

import django
django.setup()

from asgiref.sync import sync_to_async
from telegram import Bot
from accounts.models import CustomUser


MESSAGE = """Здравствуйте!

Приносим извинения за возможные неудобства.

В боте поддержки был обнаружен технический сбой, из-за которого ваши сообщения могли не дойти до нас.

Если вы писали нам в последние дни и не получили ответа — пожалуйста, отправьте ваш вопрос ещё раз.

Проблема уже исправлена. Спасибо за понимание!

С уважением,
Команда Lectio"""


@sync_to_async
def get_telegram_users():
    """Получить всех пользователей с telegram_id (async-safe)"""
    return list(CustomUser.objects.filter(
        telegram_id__isnull=False,
        telegram_verified=True
    ).values('id', 'email', 'telegram_id', 'first_name'))


async def send_notifications(dry_run=False):
    """Отправить уведомления всем пользователям с Telegram"""
    
    token = os.getenv('SUPPORT_BOT_TOKEN')
    if not token:
        print("ERROR: SUPPORT_BOT_TOKEN не установлен")
        return
    
    # Получаем всех пользователей с telegram_id
    users = await get_telegram_users()
    
    print(f"\nНайдено пользователей с Telegram: {len(users)}")
    
    if dry_run:
        print("\n[DRY RUN] Сообщение будет отправлено:")
        for user in users:
            print(f"  - {user['email']} (TG: {user['telegram_id']}) - {user['first_name']}")
        print(f"\nТекст сообщения:\n{MESSAGE}")
        return
    
    bot = Bot(token=token)
    
    success = 0
    failed = 0
    
    for user in users:
        try:
            await bot.send_message(
                chat_id=user['telegram_id'],
                text=MESSAGE
            )
            print(f"OK: {user['email']} ({user['telegram_id']})")
            success += 1
        except Exception as e:
            print(f"FAIL: {user['email']} ({user['telegram_id']}) - {e}")
            failed += 1
    
    print(f"\nИтого: {success} отправлено, {failed} ошибок")


def main():
    parser = argparse.ArgumentParser(description='Отправить уведомление о баге')
    parser.add_argument('--dry-run', action='store_true', help='Показать без отправки')
    args = parser.parse_args()
    
    asyncio.run(send_notifications(dry_run=args.dry_run))


if __name__ == '__main__':
    main()
