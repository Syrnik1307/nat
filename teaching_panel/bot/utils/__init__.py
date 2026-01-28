"""
Утилиты бота
"""
from .state import (
    get_dialog_state,
    set_dialog_state,
    update_dialog_state,
    clear_dialog_state,
    get_cached_data,
    set_cached_data,
    invalidate_cache,
)
from .permissions import (
    get_user_by_telegram_id,
    require_linked_account,
    require_role,
    require_teacher,
    require_student,
    require_notification_consent,
    check_broadcast_permission,
    record_broadcast,
)
from .templates import (
    format_user_name,
    format_role_badge,
    format_datetime,
    format_time_remaining,
    format_lesson_card,
    format_homework_card,
    format_hw_stats,
    format_group_selector_item,
    format_broadcast_preview,
    get_default_template,
    render_template,
    DEFAULT_TEMPLATES,
)

__all__ = [
    # State
    'get_dialog_state',
    'set_dialog_state',
    'update_dialog_state',
    'clear_dialog_state',
    'get_cached_data',
    'set_cached_data',
    'invalidate_cache',
    # Permissions
    'get_user_by_telegram_id',
    'require_linked_account',
    'require_role',
    'require_teacher',
    'require_student',
    'require_notification_consent',
    'check_broadcast_permission',
    'record_broadcast',
    # Templates
    'format_user_name',
    'format_role_badge',
    'format_datetime',
    'format_time_remaining',
    'format_lesson_card',
    'format_homework_card',
    'format_hw_stats',
    'format_group_selector_item',
    'format_broadcast_preview',
    'get_default_template',
    'render_template',
    'DEFAULT_TEMPLATES',
]
