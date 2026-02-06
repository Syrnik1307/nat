"""
Обработчики команд учителя - напоминания об уроках
"""
import logging
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes
from asgiref.sync import sync_to_async
from django.utils import timezone

from ...utils import (
    require_linked_account,
    require_teacher,
    get_dialog_state,
    set_dialog_state,
    clear_dialog_state,
    format_lesson_card,
    format_broadcast_preview,
    render_template,
    get_default_template,
    check_broadcast_permission,
    record_broadcast,
)
from ...keyboards import (
    group_selector_keyboard,
    lesson_selector_keyboard,
    broadcast_preview_keyboard,
    time_selector_keyboard,
    section_keyboard,
)
from ...services import BroadcastService, SchedulerService

logger = logging.getLogger(__name__)


@require_linked_account
@require_teacher
async def remind_lesson_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало wizard'а напоминания об уроке"""
    user = context.user_data.get('db_user')
    telegram_id = update.effective_user.id
    
    # Получаем группы учителя
    def get_groups():
        from schedule.models import Group
        return list(
            Group.objects.filter(teacher=user).prefetch_related('students').order_by('name')
        )
    
    groups = await sync_to_async(get_groups)()
    
    if not groups:
        await update.effective_message.reply_text(
            "📭 У вас пока нет групп.\n\n"
            "Создайте группу в Teaching Panel, чтобы отправлять напоминания."
        )
        return
    
    # Сохраняем состояние диалога
    set_dialog_state(telegram_id, {
        'action': 'remind_lesson',
        'step': 'select_groups',
        'selected_groups': [],
        'teacher_id': user.id,
    })
    
    keyboard = group_selector_keyboard(
        groups=groups,
        selected_ids=set(),
        callback_prefix='rl_group',
        back_callback='menu:broadcast',
        done_callback='rl_groups_done',
    )
    
    await update.effective_message.reply_text(
        "📅 *Напоминание об уроке*\n\n"
        "Выберите группы для рассылки (можно несколько):",
        parse_mode='Markdown',
        reply_markup=keyboard,
    )


async def remind_lesson_group_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Переключение выбора группы"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    state = get_dialog_state(telegram_id)
    
    if not state or state.get('action') != 'remind_lesson':
        await query.edit_message_text("❌ Сессия истекла. Начните заново: /remind_lesson")
        return
    
    # Извлекаем ID группы из callback_data
    group_id = int(query.data.split(':')[1])
    selected = set(state.get('selected_groups', []))
    
    if group_id in selected:
        selected.discard(group_id)
    else:
        selected.add(group_id)
    
    state['selected_groups'] = list(selected)
    set_dialog_state(telegram_id, state)
    
    # Получаем группы заново для обновления клавиатуры
    def get_groups():
        from schedule.models import Group
        return list(
            Group.objects.filter(teacher_id=state['teacher_id']).prefetch_related('students').order_by('name')
        )
    
    groups = await sync_to_async(get_groups)()
    
    keyboard = group_selector_keyboard(
        groups=groups,
        selected_ids=selected,
        callback_prefix='rl_group',
        back_callback='menu:broadcast',
        done_callback='rl_groups_done',
    )
    
    await query.edit_message_reply_markup(reply_markup=keyboard)


async def remind_lesson_groups_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Группы выбраны, переход к выбору урока"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    state = get_dialog_state(telegram_id)
    
    if not state or not state.get('selected_groups'):
        await query.edit_message_text("❌ Выберите хотя бы одну группу.")
        return
    
    state['step'] = 'select_lesson'
    set_dialog_state(telegram_id, state)
    
    # Получаем ближайшие уроки для выбранных групп
    def get_lessons():
        from schedule.models import Lesson
        now = timezone.now()
        group_ids = state['selected_groups']
        return list(
            Lesson.objects.filter(
                group_id__in=group_ids,
                start_time__gte=now,
            ).select_related('group', 'teacher').order_by('start_time')[:10]
        )
    
    lessons = await sync_to_async(get_lessons)()
    
    keyboard = lesson_selector_keyboard(
        lessons=lessons,
        callback_prefix='rl_lesson',
        back_callback='rl_back_groups',
    )
    
    # Добавляем кнопку "Свой текст"
    from telegram import InlineKeyboardButton
    keyboard.inline_keyboard.insert(-1, [
        InlineKeyboardButton('✏️ Свой текст', callback_data='rl_custom_text')
    ])
    
    await query.edit_message_text(
        "📅 *Выберите урок* или напишите свой текст:\n\n"
        "Если урока нет в списке, выберите 'Свой текст'.",
        parse_mode='Markdown',
        reply_markup=keyboard,
    )


async def remind_lesson_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Урок выбран, формируем предпросмотр"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    state = get_dialog_state(telegram_id)
    
    if not state:
        await query.edit_message_text("❌ Сессия истекла.")
        return
    
    lesson_id = int(query.data.split(':')[1])
    
    # Получаем урок и формируем сообщение
    def get_lesson_and_message():
        from schedule.models import Lesson, Group
        
        lesson = Lesson.objects.select_related('group', 'teacher').get(id=lesson_id)
        
        template = get_default_template('lesson_reminder')
        message = render_template(
            template['content'],
            lesson_title=lesson.title,
            lesson_time=timezone.localtime(lesson.start_time).strftime('%d.%m в %H:%M') if lesson.start_time else 'скоро',
            group=lesson.group.name if lesson.group else '',
            custom_text='',
        )
        
        # Считаем получателей
        group_ids = state['selected_groups']
        recipients_count = 0
        groups = Group.objects.filter(id__in=group_ids).prefetch_related('students')
        group_list = []
        for g in groups:
            recipients_count += g.students.filter(
                is_active=True,
                notification_consent=True,
                telegram_id__isnull=False,
            ).exclude(telegram_id='').count()
            group_list.append(g)
        
        return lesson, message, recipients_count, group_list
    
    lesson, message, recipients_count, groups = await sync_to_async(get_lesson_and_message)()
    
    state['step'] = 'preview'
    state['lesson_id'] = lesson_id
    state['message'] = message
    state['recipients_count'] = recipients_count
    set_dialog_state(telegram_id, state)
    
    preview = format_broadcast_preview(
        message_type='lesson_reminder',
        content=message,
        groups=groups,
        students_count=recipients_count,
    )
    
    keyboard = broadcast_preview_keyboard(
        confirm_callback='rl_send_now',
        schedule_callback='rl_schedule',
        edit_callback='rl_edit',
        cancel_callback='menu:broadcast',
    )
    
    await query.edit_message_text(
        preview,
        parse_mode='Markdown',
        reply_markup=keyboard,
    )


async def remind_lesson_send_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправить напоминание сейчас"""
    query = update.callback_query
    await query.answer('Отправляю...')
    
    telegram_id = update.effective_user.id
    state = get_dialog_state(telegram_id)
    user = context.user_data.get('db_user')
    
    if not state or not user:
        await query.edit_message_text("❌ Сессия истекла.")
        return
    
    # Проверяем лимиты
    can_send, reason = await check_broadcast_permission(user)
    if not can_send:
        await query.edit_message_text(f"⚠️ {reason}")
        return
    
    # Отправляем
    service = BroadcastService()
    result = await service.send_to_groups(
        group_ids=state['selected_groups'],
        text=state['message'],
        teacher_id=user.id,
        message_type='lesson_reminder',
    )
    
    # Записываем факт рассылки
    await record_broadcast(user, result['sent_count'])
    
    # Очищаем состояние
    clear_dialog_state(telegram_id)
    
    await query.edit_message_text(
        f"✅ *Напоминание отправлено!*\n\n"
        f"📨 Доставлено: {result['sent_count']}\n"
        f"❌ Ошибок: {result['failed_count']}",
        parse_mode='Markdown',
        reply_markup=section_keyboard('broadcast', include_refresh=False),
    )


async def remind_lesson_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать выбор времени для отложенной отправки"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    state = get_dialog_state(telegram_id)
    
    if not state:
        await query.edit_message_text("❌ Сессия истекла.")
        return
    
    state['step'] = 'schedule_time'
    set_dialog_state(telegram_id, state)
    
    keyboard = time_selector_keyboard(
        callback_prefix='rl_time',
        back_callback='rl_back_preview',
    )
    
    await query.edit_message_text(
        "⏰ *Когда отправить напоминание?*",
        parse_mode='Markdown',
        reply_markup=keyboard,
    )


async def remind_lesson_schedule_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение отложенной отправки"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    state = get_dialog_state(telegram_id)
    user = context.user_data.get('db_user')
    
    if not state or not user:
        await query.edit_message_text("❌ Сессия истекла.")
        return
    
    # Извлекаем время из callback
    time_option = query.data.split(':')[1]
    scheduled_at = SchedulerService.calculate_schedule_time(time_option)
    
    # Создаём отложенное сообщение
    msg = await SchedulerService.schedule_message(
        teacher_id=user.id,
        content=state['message'],
        scheduled_at=scheduled_at,
        message_type='lesson_reminder',
        group_ids=state['selected_groups'],
        lesson_id=state.get('lesson_id'),
    )
    
    clear_dialog_state(telegram_id)
    
    from ..utils.templates import format_datetime
    time_str = format_datetime(scheduled_at)
    
    await query.edit_message_text(
        f"✅ *Напоминание запланировано!*\n\n"
        f"⏰ Отправка: {time_str}\n"
        f"📨 Получателей: ~{state.get('recipients_count', 0)}\n\n"
        f"Управлять запланированными: /scheduled",
        parse_mode='Markdown',
        reply_markup=section_keyboard('broadcast', include_refresh=False),
    )


async def remind_lesson_custom_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Переход к вводу своего текста"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    state = get_dialog_state(telegram_id)
    
    if not state:
        await query.edit_message_text("❌ Сессия истекла.")
        return
    
    state['step'] = 'custom_text'
    set_dialog_state(telegram_id, state)
    
    await query.edit_message_text(
        "✏️ *Введите текст напоминания:*\n\n"
        "Просто отправьте сообщение в чат.\n"
        "Поддерживается Markdown форматирование.",
        parse_mode='Markdown',
    )


async def remind_lesson_handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода пользовательского текста"""
    telegram_id = update.effective_user.id
    state = get_dialog_state(telegram_id)
    
    if not state or state.get('step') != 'custom_text':
        return False  # Не наш обработчик
    
    text = update.message.text
    if not text:
        return False
    
    # Формируем предпросмотр
    def get_recipients_info():
        from schedule.models import Group
        group_ids = state['selected_groups']
        recipients_count = 0
        groups = Group.objects.filter(id__in=group_ids).prefetch_related('students')
        group_list = []
        for g in groups:
            recipients_count += g.students.filter(
                is_active=True,
                notification_consent=True,
                telegram_id__isnull=False,
            ).exclude(telegram_id='').count()
            group_list.append(g)
        return recipients_count, group_list
    
    recipients_count, groups = await sync_to_async(get_recipients_info)()
    
    state['step'] = 'preview'
    state['message'] = text
    state['recipients_count'] = recipients_count
    set_dialog_state(telegram_id, state)
    
    preview = format_broadcast_preview(
        message_type='lesson_reminder',
        content=text,
        groups=groups,
        students_count=recipients_count,
    )
    
    keyboard = broadcast_preview_keyboard(
        confirm_callback='rl_send_now',
        schedule_callback='rl_schedule',
        edit_callback='rl_custom_text',
        cancel_callback='menu:broadcast',
    )
    
    await update.message.reply_text(
        preview,
        parse_mode='Markdown',
        reply_markup=keyboard,
    )
    
    return True  # Обработано
