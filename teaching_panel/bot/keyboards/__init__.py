"""
Клавиатуры бота
"""
from .common import (
    back_button,
    cancel_button,
    confirm_button,
    main_menu_keyboard,
    section_keyboard,
    confirmation_keyboard,
    pagination_keyboard,
    time_selector_keyboard,
)
from .teacher import (
    teacher_broadcast_menu,
    group_selector_keyboard,
    lesson_selector_keyboard,
    homework_selector_keyboard,
    hw_stats_actions_keyboard,
    broadcast_preview_keyboard,
    scheduled_list_keyboard,
    scheduled_detail_keyboard,
)
from .student import (
    student_homework_keyboard,
    student_lesson_keyboard,
    student_progress_keyboard,
    reminder_settings_keyboard,
)

__all__ = [
    # Common
    'back_button',
    'cancel_button',
    'confirm_button',
    'main_menu_keyboard',
    'section_keyboard',
    'confirmation_keyboard',
    'pagination_keyboard',
    'time_selector_keyboard',
    # Teacher
    'teacher_broadcast_menu',
    'group_selector_keyboard',
    'lesson_selector_keyboard',
    'homework_selector_keyboard',
    'hw_stats_actions_keyboard',
    'broadcast_preview_keyboard',
    'scheduled_list_keyboard',
    'scheduled_detail_keyboard',
    # Student
    'student_homework_keyboard',
    'student_lesson_keyboard',
    'student_progress_keyboard',
    'reminder_settings_keyboard',
]
