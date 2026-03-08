"""
Celery tasks для модуля parents — уведомления родителям.

Задачи:
- check_parent_alerts: периодическая проверка и отправка алертов
  (несданные ДЗ, пропущенные уроки, новые оценки)
"""
import logging
from datetime import timedelta

import requests
from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def _get_parent_bot_token():
    token = getattr(settings, 'TELEGRAM_PARENT_BOT_TOKEN', '')
    if not token or token in ('', 'YOUR_BOT_TOKEN_HERE'):
        return None
    return token


def _send_parent_message(chat_id: str, text: str) -> bool:
    """Отправить сообщение родителю через @lectio_parent_bot."""
    token = _get_parent_bot_token()
    if not token:
        logger.debug('[PARENT_ALERT] TELEGRAM_PARENT_BOT_TOKEN not configured')
        return False
    if not chat_id:
        return False
    try:
        resp = requests.post(
            f'https://api.telegram.org/bot{token}/sendMessage',
            json={
                'chat_id': chat_id,
                'text': text,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True,
            },
            timeout=10,
        )
        if resp.status_code != 200:
            logger.warning('[PARENT_ALERT] Telegram error %s: %s', resp.status_code, resp.text[:200])
            return False
        return True
    except requests.RequestException as e:
        logger.warning('[PARENT_ALERT] Telegram send failed: %s', e)
        return False


@shared_task(
    name='parents.tasks.check_parent_alerts',
    soft_time_limit=120,
    time_limit=180,
    max_retries=1,
    autoretry_for=(Exception,),
    retry_backoff=60,
)
def check_parent_alerts():
    """
    Периодическая проверка алертов для родителей.

    Проверяет:
    1. alert_missed_hw: ДЗ не сдано > 3 дней после дедлайна
    2. alert_missed_lesson: пропущен урок за последние 24 часа
    3. alert_new_grade: новая оценка за контрольную за последние 24 часа

    Запускается раз в день.
    """
    from parents.models import ParentAccess, ParentAccessGrant
    from homework.models import Homework, StudentSubmission, HomeworkGroupAssignment
    from schedule.models import Attendance, Lesson
    from analytics.models import ControlPointResult

    now = timezone.now()
    sent = 0

    # Только активные доступы с Telegram
    accesses = ParentAccess.objects.filter(
        is_active=True,
        telegram_connected=True,
        telegram_chat_id__isnull=False,
    ).exclude(telegram_chat_id='').select_related('student')

    for access in accesses:
        student = access.student
        grants = ParentAccessGrant.objects.filter(
            parent_access=access, is_active=True
        ).select_related('teacher', 'group')

        if not grants.exists():
            continue

        messages = []

        # --- 1. Несданные ДЗ (alert_missed_hw) ---
        if access.alert_missed_hw:
            overdue_items = _check_overdue_homework(student, grants, now)
            if overdue_items:
                messages.append(_format_overdue_hw_message(student, overdue_items))

        # --- 2. Пропущенные уроки (alert_missed_lesson) ---
        if access.alert_missed_lesson:
            missed_items = _check_missed_lessons(student, grants, now)
            if missed_items:
                messages.append(_format_missed_lessons_message(student, missed_items))

        # --- 3. Новые оценки (alert_new_grade) ---
        if access.alert_new_grade:
            grade_items = _check_new_grades(student, grants, now)
            if grade_items:
                messages.append(_format_new_grades_message(student, grade_items))

        # Отправляем все сообщения одним текстом
        if messages:
            full_text = '\n\n'.join(messages)
            if _send_parent_message(access.telegram_chat_id, full_text):
                sent += 1

    logger.info('[PARENT_ALERT] Sent alerts to %d parents', sent)
    return {'sent': sent, 'timestamp': now.isoformat()}


def _check_overdue_homework(student, grants, now):
    """Найти ДЗ, просроченные более чем на 3 дня."""
    from homework.models import Homework, StudentSubmission, HomeworkGroupAssignment

    threshold = now - timedelta(days=3)
    overdue = []

    for grant in grants:
        if not grant.show_homework:
            continue

        # Найти назначенные ДЗ для этой группы
        assignments = HomeworkGroupAssignment.objects.filter(
            group=grant.group,
            homework__is_published=True,
        ).select_related('homework')

        for assignment in assignments:
            hw = assignment.homework
            deadline = assignment.deadline or hw.deadline
            if not deadline or deadline > threshold:
                continue

            # Проверяем, сдал ли ученик
            submitted = StudentSubmission.objects.filter(
                homework=hw, student=student
            ).exists()

            if not submitted:
                overdue.append({
                    'subject': grant.subject_label,
                    'teacher': grant.teacher.get_full_name(),
                    'title': hw.title,
                    'deadline': deadline,
                })

    return overdue


def _check_missed_lessons(student, grants, now):
    """Найти пропущенные уроки за последние 24 часа."""
    from schedule.models import Attendance, Lesson

    yesterday = now - timedelta(hours=24)
    missed = []

    for grant in grants:
        if not grant.show_attendance:
            continue

        lessons = Lesson.objects.filter(
            group=grant.group,
            date__gte=yesterday.date(),
            date__lte=now.date(),
        )

        for lesson in lessons:
            absent = Attendance.objects.filter(
                lesson=lesson,
                student=student,
                status='absent',
            ).exists()

            if absent:
                missed.append({
                    'subject': grant.subject_label,
                    'teacher': grant.teacher.get_full_name(),
                    'date': lesson.date,
                    'topic': lesson.topic or '',
                })

    return missed


def _check_new_grades(student, grants, now):
    """Найти новые оценки за контрольные за последние 24 часа."""
    from analytics.models import ControlPointResult

    yesterday = now - timedelta(hours=24)
    grades = []

    for grant in grants:
        if not grant.show_grades:
            continue

        results = ControlPointResult.objects.filter(
            student=student,
            control_point__group=grant.group,
            created_at__gte=yesterday,
        ).select_related('control_point')

        for result in results:
            grades.append({
                'subject': grant.subject_label,
                'teacher': grant.teacher.get_full_name(),
                'name': result.control_point.name,
                'score': result.score,
                'max_score': result.control_point.max_score,
            })

    return grades


# === Форматирование сообщений ===

def _format_overdue_hw_message(student, items):
    name = student.get_full_name()
    lines = [f'<b>Несданные домашние задания</b> — {name}']
    for item in items:
        deadline_str = item['deadline'].strftime('%d.%m.%Y')
        lines.append(
            f"  - {item['subject']} ({item['teacher']}): "
            f"«{item['title']}», дедлайн {deadline_str}"
        )
    return '\n'.join(lines)


def _format_missed_lessons_message(student, items):
    name = student.get_full_name()
    lines = [f'<b>Пропущенные уроки</b> — {name}']
    for item in items:
        date_str = item['date'].strftime('%d.%m.%Y')
        topic_part = f" ({item['topic']})" if item['topic'] else ''
        lines.append(
            f"  - {item['subject']} ({item['teacher']}): "
            f"{date_str}{topic_part}"
        )
    return '\n'.join(lines)


def _format_new_grades_message(student, items):
    name = student.get_full_name()
    lines = [f'<b>Новые оценки</b> — {name}']
    for item in items:
        lines.append(
            f"  - {item['subject']} ({item['teacher']}): "
            f"«{item['name']}» — {item['score']}/{item['max_score']}"
        )
    return '\n'.join(lines)
