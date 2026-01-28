"""
Обработчики команд учителя - работа с домашними заданиями
"""
import logging
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes
from asgiref.sync import sync_to_async
from django.utils import timezone

from ..utils import (
    require_linked_account,
    require_teacher,
    get_dialog_state,
    set_dialog_state,
    clear_dialog_state,
    format_hw_stats,
    format_broadcast_preview,
    render_template,
    get_default_template,
    check_broadcast_permission,
    record_broadcast,
)
from ..keyboards import (
    homework_selector_keyboard,
    group_selector_keyboard,
    hw_stats_actions_keyboard,
    broadcast_preview_keyboard,
    time_selector_keyboard,
    section_keyboard,
)
from ..services import BroadcastService, HomeworkService, SchedulerService

logger = logging.getLogger(__name__)


@require_linked_account
@require_teacher
async def check_hw_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало проверки сдачи ДЗ"""
    user = context.user_data.get('db_user')
    
    homeworks = await HomeworkService.get_teacher_homeworks(user.id, limit=10)
    
    if not homeworks:
        await update.effective_message.reply_text(
            "📭 У вас пока нет активных домашних заданий.\n\n"
            "Создайте ДЗ в Teaching Panel."
        )
        return
    
    keyboard = homework_selector_keyboard(
        homeworks=homeworks,
        callback_prefix='check_hw',
        back_callback='menu:homework',
    )
    
    await update.effective_message.reply_text(
        "✓ *Проверка сдачи ДЗ*\n\n"
        "Выберите домашнее задание:",
        parse_mode='Markdown',
        reply_markup=keyboard,
    )


async def check_hw_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показ статистики выбранного ДЗ"""
    query = update.callback_query
    await query.answer()
    
    homework_id = int(query.data.split(':')[1])
    
    # Получаем статистику
    stats = await HomeworkService.get_homework_stats(homework_id)
    
    # Получаем название ДЗ
    def get_hw_title():
        from homework.models import Homework
        hw = Homework.objects.get(id=homework_id)
        return hw
    
    hw = await sync_to_async(get_hw_title)()
    
    stats_text = format_hw_stats(hw, stats)
    
    not_submitted = stats.get('pending', 0) + stats.get('overdue', 0)
    
    keyboard = hw_stats_actions_keyboard(
        homework_id=homework_id,
        not_submitted_count=not_submitted,
        back_callback='menu:homework',
    )
    
    await query.edit_message_text(
        stats_text,
        parse_mode='Markdown',
        reply_markup=keyboard,
    )


async def list_not_submitted(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список не сдавших"""
    query = update.callback_query
    await query.answer()
    
    homework_id = int(query.data.split(':')[1])
    
    students = await HomeworkService.get_not_submitted_students(homework_id)
    
    if not students:
        await query.edit_message_text(
            "✅ Все ученики сдали это задание!",
            reply_markup=section_keyboard('homework', include_refresh=False),
        )
        return
    
    lines = ["📋 *Не сдали ДЗ:*\n"]
    for i, (student_id, name, telegram_id) in enumerate(students[:20], 1):
        tg_status = '📱' if telegram_id else '—'
        lines.append(f"{i}. {name} {tg_status}")
    
    if len(students) > 20:
        lines.append(f"\n... и ещё {len(students) - 20}")
    
    lines.append(f"\n📱 = есть Telegram")
    
    keyboard = hw_stats_actions_keyboard(
        homework_id=homework_id,
        not_submitted_count=len(students),
        back_callback='menu:homework',
    )
    
    await query.edit_message_text(
        '\n'.join(lines),
        parse_mode='Markdown',
        reply_markup=keyboard,
    )


async def ping_not_submitted(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пингануть не сдавших"""
    query = update.callback_query
    await query.answer('Готовлю рассылку...')
    
    telegram_id = update.effective_user.id
    user = context.user_data.get('db_user')
    homework_id = int(query.data.split(':')[1])
    
    # Получаем не сдавших с Telegram
    students = await HomeworkService.get_not_submitted_students(homework_id)
    students_with_tg = [(sid, name, tg) for sid, name, tg in students if tg]
    
    if not students_with_tg:
        await query.edit_message_text(
            "⚠️ Среди не сдавших нет учеников с привязанным Telegram.",
            reply_markup=section_keyboard('homework', include_refresh=False),
        )
        return
    
    # Получаем ДЗ и формируем сообщение
    def get_hw_and_message():
        from homework.models import Homework
        hw = Homework.objects.get(id=homework_id)
        
        template = get_default_template('not_submitted_ping')
        from ..utils.templates import format_datetime
        message = render_template(
            template['content'],
            hw_title=hw.title,
            deadline=format_datetime(hw.deadline) if hw.deadline else 'не указан',
        )
        return hw, message
    
    hw, message = await sync_to_async(get_hw_and_message)()
    
    # Сохраняем состояние
    set_dialog_state(telegram_id, {
        'action': 'ping_not_submitted',
        'step': 'preview',
        'homework_id': homework_id,
        'student_ids': [sid for sid, _, _ in students_with_tg],
        'telegram_ids': [tg for _, _, tg in students_with_tg],
        'message': message,
        'recipients_count': len(students_with_tg),
        'teacher_id': user.id,
    })
    
    preview_text = (
        f"📣 *Пинг не сдавших*\n\n"
        f"📝 ДЗ: {hw.title}\n"
        f"📨 Получателей: {len(students_with_tg)}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{message}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    
    keyboard = broadcast_preview_keyboard(
        confirm_callback='ping_send_now',
        schedule_callback='ping_schedule',
        edit_callback='ping_edit',
        cancel_callback='menu:homework',
    )
    
    await query.edit_message_text(
        preview_text,
        parse_mode='Markdown',
        reply_markup=keyboard,
    )


async def ping_send_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправить пинг не сдавшим сейчас"""
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
    result = await service.broadcast_to_users(
        telegram_ids=state['telegram_ids'],
        text=state['message'],
        teacher_id=user.id,
        message_type='hw_reminder',
    )
    
    await record_broadcast(user, result['sent_count'])
    clear_dialog_state(telegram_id)
    
    await query.edit_message_text(
        f"✅ *Напоминание отправлено!*\n\n"
        f"📨 Доставлено: {result['sent_count']}\n"
        f"❌ Ошибок: {result['failed_count']}",
        parse_mode='Markdown',
        reply_markup=section_keyboard('homework', include_refresh=False),
    )


@require_linked_account
@require_teacher
async def remind_hw_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало wizard'а напоминания о ДЗ"""
    user = context.user_data.get('db_user')
    telegram_id = update.effective_user.id
    
    homeworks = await HomeworkService.get_teacher_homeworks(user.id, limit=10)
    
    if not homeworks:
        await update.effective_message.reply_text(
            "📭 У вас пока нет активных домашних заданий."
        )
        return
    
    set_dialog_state(telegram_id, {
        'action': 'remind_hw',
        'step': 'select_hw',
        'teacher_id': user.id,
    })
    
    keyboard = homework_selector_keyboard(
        homeworks=homeworks,
        callback_prefix='rh_hw',
        back_callback='menu:broadcast',
    )
    
    await update.effective_message.reply_text(
        "📝 *Напоминание о ДЗ*\n\n"
        "Выберите домашнее задание:",
        parse_mode='Markdown',
        reply_markup=keyboard,
    )


async def remind_hw_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ДЗ выбрано, показываем группы"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    state = get_dialog_state(telegram_id)
    
    if not state:
        await query.edit_message_text("❌ Сессия истекла.")
        return
    
    homework_id = int(query.data.split(':')[1])
    
    # Получаем группы связанные с ДЗ
    def get_hw_groups():
        from homework.models import Homework
        from schedule.models import Group
        
        hw = Homework.objects.get(id=homework_id)
        groups = set()
        
        if hw.lesson and hw.lesson.group:
            groups.add(hw.lesson.group)
        
        for g in hw.assigned_groups.all():
            groups.add(g)
        
        return hw, list(groups)
    
    hw, groups = await sync_to_async(get_hw_groups)()
    
    state['step'] = 'select_groups'
    state['homework_id'] = homework_id
    state['hw_title'] = hw.title
    state['hw_deadline'] = str(hw.deadline) if hw.deadline else None
    state['selected_groups'] = [g.id for g in groups]  # По умолчанию все выбраны
    set_dialog_state(telegram_id, state)
    
    keyboard = group_selector_keyboard(
        groups=groups,
        selected_ids=set(state['selected_groups']),
        callback_prefix='rh_group',
        back_callback='menu:broadcast',
        done_callback='rh_groups_done',
    )
    
    await query.edit_message_text(
        f"📝 *{hw.title}*\n\n"
        "Выберите группы для напоминания:",
        parse_mode='Markdown',
        reply_markup=keyboard,
    )


async def remind_hw_group_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Переключение группы для напоминания о ДЗ"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    state = get_dialog_state(telegram_id)
    
    if not state or state.get('action') != 'remind_hw':
        await query.edit_message_text("❌ Сессия истекла.")
        return
    
    group_id = int(query.data.split(':')[1])
    selected = set(state.get('selected_groups', []))
    
    if group_id in selected:
        selected.discard(group_id)
    else:
        selected.add(group_id)
    
    state['selected_groups'] = list(selected)
    set_dialog_state(telegram_id, state)
    
    # Обновляем клавиатуру
    def get_groups():
        from schedule.models import Group
        return list(Group.objects.filter(id__in=list(selected) + [group_id]).prefetch_related('students'))
    
    groups = await sync_to_async(get_groups)()
    
    keyboard = group_selector_keyboard(
        groups=groups,
        selected_ids=selected,
        callback_prefix='rh_group',
        back_callback='menu:broadcast',
        done_callback='rh_groups_done',
    )
    
    await query.edit_message_reply_markup(reply_markup=keyboard)


async def remind_hw_groups_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Группы выбраны, формируем предпросмотр"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    state = get_dialog_state(telegram_id)
    
    if not state or not state.get('selected_groups'):
        await query.edit_message_text("❌ Выберите хотя бы одну группу.")
        return
    
    # Формируем сообщение
    def get_message_data():
        from schedule.models import Group
        from homework.models import Homework
        from ..utils.templates import format_datetime, format_time_remaining
        
        hw = Homework.objects.get(id=state['homework_id'])
        template = get_default_template('hw_reminder')
        
        message = render_template(
            template['content'],
            hw_title=hw.title,
            deadline=format_datetime(hw.deadline) if hw.deadline else 'не указан',
            time_remaining=format_time_remaining(hw.deadline) if hw.deadline else '',
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
        
        return message, recipients_count, group_list
    
    message, recipients_count, groups = await sync_to_async(get_message_data)()
    
    state['step'] = 'preview'
    state['message'] = message
    state['recipients_count'] = recipients_count
    set_dialog_state(telegram_id, state)
    
    preview = format_broadcast_preview(
        message_type='hw_reminder',
        content=message,
        groups=groups,
        students_count=recipients_count,
    )
    
    keyboard = broadcast_preview_keyboard(
        confirm_callback='rh_send_now',
        schedule_callback='rh_schedule',
        edit_callback='rh_edit',
        cancel_callback='menu:broadcast',
    )
    
    await query.edit_message_text(
        preview,
        parse_mode='Markdown',
        reply_markup=keyboard,
    )


async def remind_hw_send_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправить напоминание о ДЗ сейчас"""
    query = update.callback_query
    await query.answer('Отправляю...')
    
    telegram_id = update.effective_user.id
    state = get_dialog_state(telegram_id)
    user = context.user_data.get('db_user')
    
    if not state or not user:
        await query.edit_message_text("❌ Сессия истекла.")
        return
    
    can_send, reason = await check_broadcast_permission(user)
    if not can_send:
        await query.edit_message_text(f"⚠️ {reason}")
        return
    
    service = BroadcastService()
    result = await service.send_to_groups(
        group_ids=state['selected_groups'],
        text=state['message'],
        teacher_id=user.id,
        message_type='hw_reminder',
    )
    
    await record_broadcast(user, result['sent_count'])
    clear_dialog_state(telegram_id)
    
    await query.edit_message_text(
        f"✅ *Напоминание отправлено!*\n\n"
        f"📨 Доставлено: {result['sent_count']}\n"
        f"❌ Ошибок: {result['failed_count']}",
        parse_mode='Markdown',
        reply_markup=section_keyboard('broadcast', include_refresh=False),
    )


async def remind_hw_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать выбор времени"""
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
        callback_prefix='rh_time',
        back_callback='rh_back_preview',
    )
    
    await query.edit_message_text(
        "⏰ *Когда отправить напоминание?*",
        parse_mode='Markdown',
        reply_markup=keyboard,
    )


async def remind_hw_schedule_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение отложенной отправки напоминания о ДЗ"""
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    state = get_dialog_state(telegram_id)
    user = context.user_data.get('db_user')
    
    if not state or not user:
        await query.edit_message_text("❌ Сессия истекла.")
        return
    
    time_option = query.data.split(':')[1]
    scheduled_at = SchedulerService.calculate_schedule_time(time_option)
    
    msg = await SchedulerService.schedule_message(
        teacher_id=user.id,
        content=state['message'],
        scheduled_at=scheduled_at,
        message_type='hw_reminder',
        group_ids=state['selected_groups'],
        homework_id=state.get('homework_id'),
    )
    
    clear_dialog_state(telegram_id)
    
    from ..utils.templates import format_datetime
    time_str = format_datetime(scheduled_at)
    
    await query.edit_message_text(
        f"✅ *Напоминание запланировано!*\n\n"
        f"⏰ Отправка: {time_str}\n"
        f"📨 Получателей: ~{state.get('recipients_count', 0)}",
        parse_mode='Markdown',
        reply_markup=section_keyboard('broadcast', include_refresh=False),
    )
