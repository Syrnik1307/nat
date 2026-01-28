"""
Клавиатуры для учителя
"""
from typing import List, Set, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .common import back_button, cancel_button, confirm_button


def teacher_broadcast_menu() -> InlineKeyboardMarkup:
    """Меню рассылки для учителя"""
    rows = [
        [InlineKeyboardButton('📅 Напомнить об уроке', callback_data='broadcast:lesson_reminder')],
        [InlineKeyboardButton('📝 Напомнить о ДЗ', callback_data='broadcast:hw_reminder')],
        [InlineKeyboardButton('⏰ Пинг по дедлайну', callback_data='broadcast:hw_deadline')],
        [InlineKeyboardButton('✓ Проверить сдачу ДЗ', callback_data='broadcast:check_hw')],
        [InlineKeyboardButton('❌ Отмена урока', callback_data='broadcast:lesson_cancel')],
        [InlineKeyboardButton('💬 Произвольное сообщение', callback_data='broadcast:custom')],
        [back_button('menu:root')],
    ]
    return InlineKeyboardMarkup(rows)


def group_selector_keyboard(
    groups: List,
    selected_ids: Set[int],
    callback_prefix: str = 'select_group',
    back_callback: str = 'menu:broadcast',
    done_callback: str = 'groups_selected',
) -> InlineKeyboardMarkup:
    """
    Клавиатура выбора групп с чекбоксами.
    groups: список объектов Group
    selected_ids: set выбранных group.id
    """
    rows = []
    
    for group in groups:
        is_selected = group.id in selected_ids
        checkbox = '☑️' if is_selected else '☐'
        student_count = group.students.count() if hasattr(group, 'students') else 0
        text = f"{checkbox} {group.name} ({student_count})"
        rows.append([
            InlineKeyboardButton(text, callback_data=f'{callback_prefix}:{group.id}')
        ])
    
    # Кнопки управления
    control_row = []
    if selected_ids:
        control_row.append(InlineKeyboardButton(f'✅ Выбрано: {len(selected_ids)}', callback_data=done_callback))
    control_row.append(cancel_button(back_callback))
    rows.append(control_row)
    
    return InlineKeyboardMarkup(rows)


def lesson_selector_keyboard(
    lessons: List,
    callback_prefix: str = 'select_lesson',
    back_callback: str = 'menu:broadcast',
) -> InlineKeyboardMarkup:
    """Клавиатура выбора урока"""
    from ..utils.templates import format_datetime
    
    rows = []
    
    for lesson in lessons:
        time_str = format_datetime(lesson.start_time, '%d.%m %H:%M')
        group_name = lesson.group.name if lesson.group else 'Без группы'
        text = f"📅 {time_str} | {lesson.title[:20]}"
        rows.append([
            InlineKeyboardButton(text, callback_data=f'{callback_prefix}:{lesson.id}')
        ])
    
    if not lessons:
        rows.append([InlineKeyboardButton('📭 Нет уроков', callback_data='noop')])
    
    rows.append([back_button(back_callback)])
    
    return InlineKeyboardMarkup(rows)


def homework_selector_keyboard(
    homeworks: List,
    callback_prefix: str = 'select_hw',
    back_callback: str = 'menu:broadcast',
) -> InlineKeyboardMarkup:
    """Клавиатура выбора ДЗ"""
    from ..utils.templates import format_datetime
    
    rows = []
    
    for hw in homeworks:
        deadline_str = format_datetime(hw.deadline, '%d.%m') if hw.deadline else 'без дедлайна'
        text = f"📝 {hw.title[:25]} | {deadline_str}"
        rows.append([
            InlineKeyboardButton(text, callback_data=f'{callback_prefix}:{hw.id}')
        ])
    
    if not homeworks:
        rows.append([InlineKeyboardButton('📭 Нет активных ДЗ', callback_data='noop')])
    
    rows.append([back_button(back_callback)])
    
    return InlineKeyboardMarkup(rows)


def hw_stats_actions_keyboard(
    homework_id: int,
    not_submitted_count: int,
    back_callback: str = 'menu:homework',
) -> InlineKeyboardMarkup:
    """Клавиатура действий после просмотра статистики ДЗ"""
    rows = []
    
    if not_submitted_count > 0:
        rows.append([
            InlineKeyboardButton(
                f'📣 Пингануть не сдавших ({not_submitted_count})',
                callback_data=f'ping_not_submitted:{homework_id}'
            )
        ])
        rows.append([
            InlineKeyboardButton(
                '📋 Список не сдавших',
                callback_data=f'list_not_submitted:{homework_id}'
            )
        ])
    
    rows.append([
        InlineKeyboardButton('🔄 Обновить', callback_data=f'check_hw:{homework_id}')
    ])
    rows.append([back_button(back_callback)])
    
    return InlineKeyboardMarkup(rows)


def broadcast_preview_keyboard(
    confirm_callback: str,
    schedule_callback: str,
    edit_callback: str,
    cancel_callback: str = 'cancel',
) -> InlineKeyboardMarkup:
    """Клавиатура предпросмотра рассылки"""
    rows = [
        [InlineKeyboardButton('🚀 Отправить сейчас', callback_data=confirm_callback)],
        [InlineKeyboardButton('⏰ Отложить', callback_data=schedule_callback)],
        [InlineKeyboardButton('✏️ Редактировать', callback_data=edit_callback)],
        [cancel_button(cancel_callback)],
    ]
    return InlineKeyboardMarkup(rows)


def scheduled_list_keyboard(
    messages: List,
    callback_prefix: str = 'scheduled',
    back_callback: str = 'menu:root',
) -> InlineKeyboardMarkup:
    """Клавиатура списка запланированных сообщений"""
    from ..utils.templates import format_datetime
    
    rows = []
    
    for msg in messages:
        time_str = format_datetime(msg.scheduled_at, '%d.%m %H:%M')
        type_emoji = {
            'lesson_reminder': '📅',
            'hw_reminder': '📝',
            'hw_deadline': '⏰',
            'lesson_cancel': '❌',
            'custom': '💬',
        }.get(msg.message_type, '📨')
        
        text = f"{type_emoji} {time_str} | {msg.content[:15]}..."
        rows.append([
            InlineKeyboardButton(text, callback_data=f'{callback_prefix}:view:{msg.id}')
        ])
    
    if not messages:
        rows.append([InlineKeyboardButton('📭 Нет запланированных', callback_data='noop')])
    
    rows.append([back_button(back_callback)])
    
    return InlineKeyboardMarkup(rows)


def scheduled_detail_keyboard(
    message_id: int,
    back_callback: str = 'menu:scheduled',
) -> InlineKeyboardMarkup:
    """Клавиатура деталей запланированного сообщения"""
    rows = [
        [InlineKeyboardButton('❌ Отменить', callback_data=f'scheduled:cancel:{message_id}')],
        [back_button(back_callback)],
    ]
    return InlineKeyboardMarkup(rows)
