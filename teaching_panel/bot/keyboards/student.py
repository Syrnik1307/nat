"""
Клавиатуры для ученика
"""
from typing import List
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .common import back_button


def student_homework_keyboard(
    homeworks: List,
    callback_prefix: str = 'student_hw',
    back_callback: str = 'menu:root',
) -> InlineKeyboardMarkup:
    """Клавиатура списка ДЗ ученика"""
    from ..utils.templates import format_datetime
    from ..config import HW_STATUS_EMOJI
    
    rows = []
    
    for hw_data in homeworks:
        hw = hw_data['homework']
        status = hw_data['status']
        
        status_emoji = HW_STATUS_EMOJI.get(status, '❓')
        deadline_str = format_datetime(hw.deadline, '%d.%m') if hw.deadline else ''
        
        text = f"{status_emoji} {hw.title[:20]} | {deadline_str}"
        rows.append([
            InlineKeyboardButton(text, callback_data=f'{callback_prefix}:{hw.id}')
        ])
    
    if not homeworks:
        rows.append([InlineKeyboardButton('📭 Нет домашних заданий', callback_data='noop')])
    
    rows.append([back_button(back_callback)])
    
    return InlineKeyboardMarkup(rows)


def student_lesson_keyboard(
    lessons: List,
    callback_prefix: str = 'student_lesson',
    back_callback: str = 'menu:root',
) -> InlineKeyboardMarkup:
    """Клавиатура списка уроков ученика"""
    from ..utils.templates import format_datetime
    
    rows = []
    
    for lesson in lessons:
        time_str = format_datetime(lesson.start_time, '%d.%m %H:%M')
        text = f"📅 {time_str} | {lesson.title[:20]}"
        
        row = [InlineKeyboardButton(text, callback_data=f'{callback_prefix}:{lesson.id}')]
        
        # Добавляем кнопку Zoom если есть
        if lesson.zoom_join_url:
            row.append(InlineKeyboardButton('🔗', url=lesson.zoom_join_url))
        
        rows.append(row)
    
    if not lessons:
        rows.append([InlineKeyboardButton('📭 Нет уроков', callback_data='noop')])
    
    rows.append([back_button(back_callback)])
    
    return InlineKeyboardMarkup(rows)


def student_progress_keyboard(back_callback: str = 'menu:root') -> InlineKeyboardMarkup:
    """Клавиатура раздела прогресса"""
    rows = [
        [InlineKeyboardButton('📝 Все мои ДЗ', callback_data='menu:my_homework')],
        [InlineKeyboardButton('⏰ Ближайшие дедлайны', callback_data='menu:deadlines')],
        [back_button(back_callback)],
    ]
    return InlineKeyboardMarkup(rows)


def reminder_settings_keyboard(
    current_lesson_minutes: int = 30,
    current_hw_hours: int = 24,
    back_callback: str = 'menu:notifications',
) -> InlineKeyboardMarkup:
    """Клавиатура настройки напоминаний"""
    rows = [
        [InlineKeyboardButton(f'📅 Урок: за {current_lesson_minutes} мин', callback_data='noop')],
        [
            InlineKeyboardButton('15', callback_data='reminder:lesson:15'),
            InlineKeyboardButton('30', callback_data='reminder:lesson:30'),
            InlineKeyboardButton('60', callback_data='reminder:lesson:60'),
        ],
        [InlineKeyboardButton(f'📝 ДЗ: за {current_hw_hours} ч.', callback_data='noop')],
        [
            InlineKeyboardButton('6ч', callback_data='reminder:hw:6'),
            InlineKeyboardButton('12ч', callback_data='reminder:hw:12'),
            InlineKeyboardButton('24ч', callback_data='reminder:hw:24'),
        ],
        [back_button(back_callback)],
    ]
    return InlineKeyboardMarkup(rows)
