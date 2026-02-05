"""
Сигналы для автоматического логирования активности студентов.
Эти "сенсоры" захватывают события без модификации контроллеров.

Используем существующую модель StudentActivityLog из accounts.models.
"""
from django.db.models.signals import post_save
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.utils import timezone

from accounts.models import StudentActivityLog


# Маппинг весов для разных типов событий (для расчёта "heat" интенсивности)
EVENT_WEIGHTS = {
    'login': 1,
    'homework_submit': 5,
    'homework_start': 2,
    'answer_save': 1,
    'lesson_join': 10,
    'recording_watch': 3,
    'chat_message': 2,
    'question_ask': 3,
}


# ============================================================
# HOMEWORK SENSOR: Сдача домашнего задания
# ============================================================
@receiver(post_save, sender='homework.StudentSubmission')
def log_homework_submission(sender, instance, created, **kwargs):
    """
    Логирует событие сдачи домашнего задания.
    Срабатывает только при переходе статуса в 'submitted'.
    """
    # Пропускаем если это не студент
    if not hasattr(instance, 'student') or instance.student.role != 'student':
        return
    
    # Проверяем что статус = 'submitted'
    if instance.status != 'submitted':
        return
    
    # Избегаем дублирования: проверяем, не логировали ли уже эту сдачу
    if not instance.submitted_at:
        return
    
    # Проверяем, нет ли уже записи для этой submission
    existing = StudentActivityLog.objects.filter(
        student=instance.student,
        action_type='homework_submit',
        details__submission_id=instance.id
    ).exists()
    
    if existing:
        return
    
    # Определяем группу из homework
    group = None
    if hasattr(instance.homework, 'group'):
        group = instance.homework.group
    
    StudentActivityLog.objects.create(
        student=instance.student,
        action_type='homework_submit',
        group=group,
        details={
            'submission_id': instance.id,
            'homework_id': instance.homework_id,
            'homework_title': instance.homework.title if instance.homework else None,
            'weight': EVENT_WEIGHTS['homework_submit'],
        }
    )


# ============================================================
# ATTENDANCE SENSOR: Посещение занятия
# ============================================================
@receiver(post_save, sender='schedule.Attendance')
def log_lesson_attendance(sender, instance, created, **kwargs):
    """
    Логирует посещение занятия.
    Срабатывает только при статусе 'present'.
    """
    # Пропускаем если это не студент
    if not hasattr(instance, 'student') or instance.student.role != 'student':
        return
    
    # Только для присутствующих
    if instance.status != 'present':
        return
    
    # Проверяем дубликаты
    existing = StudentActivityLog.objects.filter(
        student=instance.student,
        action_type='lesson_join',
        details__lesson_id=instance.lesson_id
    ).exists()
    
    if existing:
        return
    
    # Определяем группу из lesson
    group = None
    if hasattr(instance.lesson, 'group'):
        group = instance.lesson.group
    
    StudentActivityLog.objects.create(
        student=instance.student,
        action_type='lesson_join',
        group=group,
        details={
            'lesson_id': instance.lesson_id,
            'lesson_title': instance.lesson.title if instance.lesson else None,
            'attendance_id': instance.id,
            'weight': EVENT_WEIGHTS['lesson_join'],
        }
    )


# ============================================================
# LOGIN SENSOR: Вход в систему
# ============================================================
@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """
    Логирует вход пользователя в систему.
    Срабатывает только для студентов.
    
    Примечание: Логируем максимум 1 вход в день для избежания спама.
    """
    # Только для студентов
    if not hasattr(user, 'role') or user.role != 'student':
        return
    
    # Проверяем, был ли уже логин сегодня
    today = timezone.now().date()
    existing = StudentActivityLog.objects.filter(
        student=user,
        action_type='login',
        created_at__date=today
    ).exists()
    
    if existing:
        return
    
    StudentActivityLog.objects.create(
        student=user,
        action_type='login',
        details={
            'ip_address': get_client_ip(request) if request else None,
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200] if request else None,
            'weight': EVENT_WEIGHTS['login'],
        }
    )


def get_client_ip(request):
    """Извлекает IP-адрес клиента из запроса."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')
