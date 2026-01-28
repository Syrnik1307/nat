"""
Обработчики команд бота
"""
from .common import (
    start_command,
    menu_command,
    help_command,
    profile_command,
    menu_callback,
)
from .callbacks import callback_query_handler
from .teacher import (
    remind_lesson_start,
    remind_lesson_handle_text,
    check_hw_start,
    remind_hw_start,
)
from .student import (
    my_lessons,
    today_lessons,
    my_homework,
    pending_homework,
    my_progress,
)

__all__ = [
    # Common
    'start_command',
    'menu_command',
    'help_command',
    'profile_command',
    'menu_callback',
    'callback_query_handler',
    # Teacher
    'remind_lesson_start',
    'remind_lesson_handle_text',
    'check_hw_start',
    'remind_hw_start',
    # Student
    'my_lessons',
    'today_lessons',
    'my_homework',
    'pending_homework',
    'my_progress',
]
