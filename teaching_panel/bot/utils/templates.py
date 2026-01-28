"""
Шаблоны сообщений и форматирование
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from django.utils import timezone

from ..config import ROLE_EMOJI, ROLE_NAMES, HW_STATUS_EMOJI, HW_STATUS_NAMES


def format_user_name(user) -> str:
    """Форматирует имя пользователя"""
    full = user.get_full_name() if hasattr(user, 'get_full_name') else ''
    return (full or user.first_name or user.email or 'Пользователь').strip()


def format_role_badge(user) -> str:
    """Форматирует бейдж роли"""
    emoji = ROLE_EMOJI.get(user.role, '👤')
    name = ROLE_NAMES.get(user.role, user.role.title())
    return f"{emoji} {name}"


def format_datetime(dt: Optional[datetime], format_str: str = '%d.%m %H:%M') -> str:
    """Форматирует дату/время"""
    if not dt:
        return '—'
    local_dt = timezone.localtime(dt) if timezone.is_aware(dt) else dt
    return local_dt.strftime(format_str)


def format_time_remaining(dt: Optional[datetime]) -> str:
    """Форматирует оставшееся время до дедлайна"""
    if not dt:
        return '—'
    
    now = timezone.now()
    if dt < now:
        return '🔴 Просрочено'
    
    delta = dt - now
    days = delta.days
    hours = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60
    
    if days > 0:
        return f"⏳ {days} дн. {hours} ч."
    elif hours > 0:
        return f"⏳ {hours} ч. {minutes} мин."
    else:
        return f"⚠️ {minutes} мин.!"


def format_lesson_card(lesson, include_zoom: bool = True) -> str:
    """Форматирует карточку урока"""
    start_str = format_datetime(lesson.start_time)
    teacher_name = format_user_name(lesson.teacher) if lesson.teacher else '—'
    group_name = lesson.group.name if lesson.group else 'Без группы'
    
    lines = [
        f"📅 *{lesson.title}*",
        f"⏰ {start_str}",
        f"👥 {group_name}",
        f"👨‍🏫 {teacher_name}",
    ]
    
    if include_zoom and lesson.zoom_join_url:
        lines.append(f"🔗 [Подключиться к Zoom]({lesson.zoom_join_url})")
    
    return '\n'.join(lines)


def format_homework_card(homework, submission=None, for_teacher: bool = False) -> str:
    """Форматирует карточку ДЗ"""
    deadline_str = format_datetime(homework.deadline)
    remaining = format_time_remaining(homework.deadline)
    
    lines = [
        f"📝 *{homework.title}*",
        f"⏰ Дедлайн: {deadline_str}",
        f"{remaining}",
    ]
    
    if not for_teacher and submission:
        status_emoji = HW_STATUS_EMOJI.get(submission.status, '❓')
        status_name = HW_STATUS_NAMES.get(submission.status, submission.status)
        lines.append(f"{status_emoji} {status_name}")
        
        if submission.status == 'graded' and submission.total_score is not None:
            lines.append(f"📊 Оценка: {submission.total_score}")
    
    if for_teacher:
        # Для учителя показываем статистику
        if hasattr(homework, 'submission_stats'):
            stats = homework.submission_stats
            lines.append(f"✅ Сдали: {stats.get('submitted', 0)}")
            lines.append(f"⏳ Ожидает: {stats.get('pending', 0)}")
    
    return '\n'.join(lines)


def format_hw_stats(homework, stats: Dict[str, int]) -> str:
    """Форматирует статистику сдачи ДЗ"""
    total = stats.get('total', 0)
    submitted = stats.get('submitted', 0)
    graded = stats.get('graded', 0)
    pending = stats.get('pending', 0)
    overdue = stats.get('overdue', 0)
    
    percent = int((submitted + graded) / total * 100) if total > 0 else 0
    
    lines = [
        f"📊 *Статистика: {homework.title}*",
        f"",
        f"👥 Всего учеников: {total}",
        f"✅ Сдали: {submitted + graded} ({percent}%)",
        f"  └ ✓ Проверено: {graded}",
        f"  └ 🟡 На проверке: {submitted}",
        f"⏳ Не сдали: {pending}",
    ]
    
    if overdue > 0:
        lines.append(f"🔴 Просрочили: {overdue}")
    
    return '\n'.join(lines)


def format_group_selector_item(group, selected: bool = False) -> str:
    """Форматирует элемент выбора группы"""
    checkbox = '☑️' if selected else '☐'
    student_count = group.students.count() if hasattr(group, 'students') else 0
    return f"{checkbox} {group.name} ({student_count} уч.)"


def format_broadcast_preview(
    message_type: str,
    content: str,
    groups: List,
    students_count: int,
    scheduled_at: Optional[datetime] = None
) -> str:
    """Форматирует предпросмотр рассылки"""
    type_names = {
        'lesson_reminder': '📅 Напоминание об уроке',
        'hw_reminder': '📝 Напоминание о ДЗ',
        'hw_deadline': '⏰ Дедлайн ДЗ',
        'lesson_cancel': '❌ Отмена урока',
        'custom': '💬 Сообщение',
    }
    
    lines = [
        "━━━━━━━━━━━━━━━━━━━━",
        f"*Предпросмотр рассылки*",
        f"",
        f"📌 Тип: {type_names.get(message_type, message_type)}",
        f"👥 Группы: {', '.join(g.name for g in groups) or 'Не выбраны'}",
        f"📨 Получателей: {students_count}",
    ]
    
    if scheduled_at:
        lines.append(f"⏰ Отправка: {format_datetime(scheduled_at)}")
    else:
        lines.append(f"⏰ Отправка: сейчас")
    
    lines.extend([
        f"",
        "━━━━━━━━━━━━━━━━━━━━",
        f"",
        content,
        f"",
        "━━━━━━━━━━━━━━━━━━━━",
    ])
    
    return '\n'.join(lines)


# Системные шаблоны сообщений
DEFAULT_TEMPLATES = {
    'lesson_reminder': {
        'title': 'Напоминание об уроке',
        'content': (
            "📅 *Напоминание об уроке*\n\n"
            "Скоро начнётся урок:\n"
            "📚 {lesson_title}\n"
            "⏰ {lesson_time}\n"
            "👥 Группа: {group}\n\n"
            "{custom_text}"
        ),
    },
    'hw_reminder': {
        'title': 'Напоминание о ДЗ',
        'content': (
            "📝 *Напоминание о домашнем задании*\n\n"
            "Не забудьте сдать:\n"
            "📋 {hw_title}\n"
            "⏰ Дедлайн: {deadline}\n"
            "{time_remaining}\n\n"
            "{custom_text}"
        ),
    },
    'hw_deadline_urgent': {
        'title': 'Срочный дедлайн',
        'content': (
            "⚠️ *Срочно: приближается дедлайн!*\n\n"
            "📋 {hw_title}\n"
            "⏰ До дедлайна: {time_remaining}\n\n"
            "Пожалуйста, сдайте работу вовремя!"
        ),
    },
    'lesson_cancel': {
        'title': 'Отмена урока',
        'content': (
            "❌ *Урок отменён*\n\n"
            "📚 {lesson_title}\n"
            "📅 {lesson_time}\n\n"
            "Причина: {reason}\n\n"
            "Приносим извинения за неудобства."
        ),
    },
    'not_submitted_ping': {
        'title': 'Напоминание не сдавшим',
        'content': (
            "👋 *Напоминание*\n\n"
            "Вы ещё не сдали домашнее задание:\n"
            "📋 {hw_title}\n"
            "⏰ Дедлайн: {deadline}\n\n"
            "Пожалуйста, не забудьте сдать работу!"
        ),
    },
}


def get_default_template(template_key: str) -> Optional[Dict[str, str]]:
    """Получает системный шаблон"""
    return DEFAULT_TEMPLATES.get(template_key)


def render_template(template_content: str, **kwargs) -> str:
    """Рендерит шаблон с подстановкой переменных"""
    result = template_content
    for key, value in kwargs.items():
        placeholder = '{' + key + '}'
        result = result.replace(placeholder, str(value or ''))
    # Убираем неиспользованные плейсхолдеры
    import re
    result = re.sub(r'\{[a-z_]+\}', '', result)
    # Убираем лишние пустые строки
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result.strip()
