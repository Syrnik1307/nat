"""
Обработчики команд учителя
"""
from .lessons import (
    remind_lesson_start,
    remind_lesson_group_toggle,
    remind_lesson_groups_done,
    remind_lesson_selected,
    remind_lesson_send_now,
    remind_lesson_schedule,
    remind_lesson_schedule_confirm,
    remind_lesson_custom_text,
    remind_lesson_handle_text,
)
from .homework import (
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

__all__ = [
    # Lessons
    'remind_lesson_start',
    'remind_lesson_group_toggle',
    'remind_lesson_groups_done',
    'remind_lesson_selected',
    'remind_lesson_send_now',
    'remind_lesson_schedule',
    'remind_lesson_schedule_confirm',
    'remind_lesson_custom_text',
    'remind_lesson_handle_text',
    # Homework
    'check_hw_start',
    'check_hw_selected',
    'list_not_submitted',
    'ping_not_submitted',
    'ping_send_now',
    'remind_hw_start',
    'remind_hw_selected',
    'remind_hw_group_toggle',
    'remind_hw_groups_done',
    'remind_hw_send_now',
    'remind_hw_schedule',
    'remind_hw_schedule_confirm',
]
