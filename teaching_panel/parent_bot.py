"""
Telegram бот для родителей — @lectio_parent_bot.

Функции:
- /start <token>  — привязка chat_id к ParentAccess по deep-link
- /status         — статус подключения
- /help           — справка

Запуск: python parent_bot.py
Или через systemd: parent_bot.service
"""
import os
import sys
import asyncio
import logging

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from django.conf import settings as django_settings
from asgiref.sync import sync_to_async
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)


# === Helpers ===

@sync_to_async
def _link_parent(token_str: str, chat_id: str):
    """Привязать chat_id к ParentAccess по UUID-токену."""
    import uuid
    from parents.models import ParentAccess

    try:
        token = uuid.UUID(token_str)
    except (ValueError, AttributeError):
        return None, 'invalid_token'

    try:
        access = ParentAccess.objects.select_related('student').get(
            token=token, is_active=True,
        )
    except ParentAccess.DoesNotExist:
        return None, 'not_found'

    access.telegram_chat_id = chat_id
    access.telegram_connected = True
    access.save(update_fields=['telegram_chat_id', 'telegram_connected'])
    return access, 'ok'


@sync_to_async
def _get_parent_status(chat_id: str):
    """Получить статус подключения по chat_id."""
    from parents.models import ParentAccess

    try:
        access = ParentAccess.objects.select_related('student').get(
            telegram_chat_id=chat_id, is_active=True,
        )
        return access
    except ParentAccess.DoesNotExist:
        return None


# === Handlers ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /start <token> — привязка.
    /start          — приветствие.
    """
    args = context.args or []
    chat_id = str(update.effective_chat.id)

    if not args:
        await update.message.reply_text(
            'Lectio Space — уведомления для родителей.\n\n'
            'Чтобы подключиться, перейдите по ссылке из дашборда '
            'вашего ребёнка (кнопка «Подключить Telegram»).\n\n'
            'После подключения вы будете получать уведомления о:\n'
            '- Несданных домашних заданиях\n'
            '- Пропущенных уроках\n'
            '- Новых оценках\n\n'
            'Команды:\n'
            '/status — статус подключения\n'
            '/help — справка'
        )
        return

    token_str = args[0].strip()
    access, result = await _link_parent(token_str, chat_id)

    if result == 'invalid_token':
        await update.message.reply_text(
            'Неверная ссылка. Пожалуйста, используйте ссылку '
            'из дашборда вашего ребёнка.'
        )
        return

    if result == 'not_found':
        await update.message.reply_text(
            'Доступ не найден или деактивирован. '
            'Обратитесь к учителю для получения новой ссылки.'
        )
        return

    student_name = await sync_to_async(access.student.get_full_name)()
    await update.message.reply_text(
        f'Подключено! Вы будете получать уведомления '
        f'об ученике: {student_name}.\n\n'
        f'/status — проверить подключение'
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/status — показать статус подключения."""
    chat_id = str(update.effective_chat.id)
    access = await _get_parent_status(chat_id)

    if not access:
        await update.message.reply_text(
            'Вы ещё не подключены. Используйте ссылку '
            'из родительского дашборда для подключения.'
        )
        return

    student_name = await sync_to_async(access.student.get_full_name)()

    alerts = []
    if access.alert_missed_hw:
        alerts.append('- Несданные ДЗ')
    if access.alert_missed_lesson:
        alerts.append('- Пропущенные уроки')
    if access.alert_new_grade:
        alerts.append('- Новые оценки')

    alerts_text = '\n'.join(alerts) if alerts else '(нет активных уведомлений)'

    await update.message.reply_text(
        f'Подключено\n'
        f'Ученик: {student_name}\n\n'
        f'Активные уведомления:\n{alerts_text}'
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/help — справка."""
    await update.message.reply_text(
        'Lectio Space — уведомления для родителей\n\n'
        'Этот бот отправляет уведомления о прогрессе вашего ребёнка.\n\n'
        'Как подключиться:\n'
        '1. Откройте родительский дашборд (ссылка от учителя)\n'
        '2. Нажмите «Подключить Telegram»\n'
        '3. Бот автоматически подключится\n\n'
        'Команды:\n'
        '/status — статус подключения\n'
        '/help — эта справка'
    )


def main():
    token = getattr(django_settings, 'TELEGRAM_PARENT_BOT_TOKEN', '')
    if not token:
        logger.error('TELEGRAM_PARENT_BOT_TOKEN not set. Exiting.')
        sys.exit(1)

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('status', status_command))
    app.add_handler(CommandHandler('help', help_command))

    logger.info('Parent bot starting polling...')
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
