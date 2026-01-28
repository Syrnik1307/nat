"""
Обработчик всех callback запросов
"""
import logging

from telegram import Update
from telegram.ext import ContextTypes

from .common import menu_callback
from .teacher import (
    remind_lesson_group_toggle,
    remind_lesson_groups_done,
    remind_lesson_selected,
    remind_lesson_send_now,
    remind_lesson_schedule,
    remind_lesson_schedule_confirm,
    remind_lesson_custom_text,
    remind_lesson_start,
    check_hw_start,
    check_hw_selected,
    list_not_submitted,
    ping_not_submitted,
    ping_send_now,
    remind_hw_start,
    remind_hw_selected,
    remind_hw_group_toggle,
    remind_hw_groups_done,
    remind_hw_send_now,
    remind_hw_schedule,
    remind_hw_schedule_confirm,
)
from .student import (
    lesson_details,
    homework_details,
    detailed_grades,
)

logger = logging.getLogger(__name__)


async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Универсальный обработчик callback запросов"""
    query = update.callback_query
    data = query.data
    
    logger.debug(f"Callback: {data}")
    
    # Роутинг по префиксам
    
    # Меню навигация
    if data.startswith('menu:'):
        await menu_callback(update, context)
        return
    
    # Действия (переход к wizard'ам)
    if data.startswith('action:'):
        action = data.split(':')[1]
        await handle_action(update, context, action)
        return
    
    # Remind Lesson wizard
    if data.startswith('rl_'):
        await handle_remind_lesson_callback(update, context, data)
        return
    
    # Remind HW wizard
    if data.startswith('rh_'):
        await handle_remind_hw_callback(update, context, data)
        return
    
    # Check HW
    if data.startswith('check_hw:'):
        await check_hw_selected(update, context)
        return
    
    if data.startswith('not_submitted:'):
        await list_not_submitted(update, context)
        return
    
    if data.startswith('ping:'):
        await ping_not_submitted(update, context)
        return
    
    if data == 'ping_send_now':
        await ping_send_now(update, context)
        return
    
    # Student callbacks
    if data.startswith('st_lesson:'):
        await lesson_details(update, context)
        return
    
    if data.startswith('st_hw:'):
        await homework_details(update, context)
        return
    
    if data == 'st_grades':
        await detailed_grades(update, context)
        return
    
    # Ничего не подошло
    await query.answer("Неизвестная команда")


async def handle_action(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str):
    """Обработчик переходов к действиям из меню"""
    query = update.callback_query
    await query.answer()
    
    if action == 'remind_lesson':
        await remind_lesson_start(update, context)
    elif action == 'remind_hw':
        await remind_hw_start(update, context)
    elif action == 'check_hw':
        await check_hw_start(update, context)
    elif action == 'scheduled':
        await show_scheduled(update, context)
    else:
        await query.edit_message_text(f"Действие '{action}' в разработке.")


async def handle_remind_lesson_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Роутер для wizard напоминания об уроке"""
    
    if data.startswith('rl_group:'):
        await remind_lesson_group_toggle(update, context)
    elif data == 'rl_groups_done':
        await remind_lesson_groups_done(update, context)
    elif data.startswith('rl_lesson:'):
        await remind_lesson_selected(update, context)
    elif data == 'rl_send_now':
        await remind_lesson_send_now(update, context)
    elif data == 'rl_schedule':
        await remind_lesson_schedule(update, context)
    elif data.startswith('rl_time:'):
        await remind_lesson_schedule_confirm(update, context)
    elif data == 'rl_custom_text':
        await remind_lesson_custom_text(update, context)
    elif data == 'rl_back_groups':
        # Вернуться к выбору групп
        await remind_lesson_start(update, context)


async def handle_remind_hw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Роутер для wizard напоминания о ДЗ"""
    
    if data.startswith('rh_hw:'):
        await remind_hw_selected(update, context)
    elif data.startswith('rh_group:'):
        await remind_hw_group_toggle(update, context)
    elif data == 'rh_groups_done':
        await remind_hw_groups_done(update, context)
    elif data == 'rh_send_now':
        await remind_hw_send_now(update, context)
    elif data == 'rh_schedule':
        await remind_hw_schedule(update, context)
    elif data.startswith('rh_time:'):
        await remind_hw_schedule_confirm(update, context)


async def show_scheduled(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать запланированные сообщения"""
    query = update.callback_query
    user = context.user_data.get('db_user')
    
    from ..services import SchedulerService
    messages = await SchedulerService.get_teacher_scheduled(user.id)
    
    if not messages:
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton('◀️ Назад', callback_data='menu:broadcast')],
        ])
        
        await query.edit_message_text(
            "📋 *Запланированные сообщения*\n\n"
            "Нет запланированных сообщений.",
            parse_mode='Markdown',
            reply_markup=keyboard,
        )
        return
    
    from ..keyboards import scheduled_list_keyboard
    from ..utils import format_datetime
    
    lines = ["📋 *Запланированные сообщения:*\n"]
    
    for i, msg in enumerate(messages[:10], 1):
        time_str = format_datetime(msg.scheduled_at)
        preview = msg.content[:30] + '...' if len(msg.content) > 30 else msg.content
        lines.append(f"{i}. ⏰ {time_str}\n    {preview}")
    
    keyboard = scheduled_list_keyboard(messages[:10], 'cancel_scheduled')
    
    await query.edit_message_text(
        '\n'.join(lines),
        parse_mode='Markdown',
        reply_markup=keyboard,
    )
