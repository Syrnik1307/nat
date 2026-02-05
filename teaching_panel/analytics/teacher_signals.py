"""
Сигналы для автоматического логирования активности преподавателей.
Эти "сенсоры" захватывают события без модификации контроллеров.

Используем модель TeacherActivityLog из accounts.models.
"""
from django.db.models.signals import post_save
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.utils import timezone

from accounts.models import TeacherActivityLog, TeacherSession


# Маппинг весов для разных типов событий
EVENT_WEIGHTS = {
    'login': 1,
    'lesson_conducted': 10,
    'homework_created': 5,
    'homework_graded': 3,
    'recording_uploaded': 5,
    'student_feedback': 2,
    'material_created': 3,
    'session_time': 1,  # 1 балл за каждые 10 минут
}


# ============================================================
# LESSON SENSOR: Проведение занятия
# ============================================================
@receiver(post_save, sender='schedule.Lesson')
def log_lesson_conducted(sender, instance, created, **kwargs):
    """
    Логирует проведение занятия.
    Срабатывает когда занятие завершено (status='completed' или ended_at заполнен).
    """
    # Пропускаем если нет учителя
    if not hasattr(instance, 'teacher') or not instance.teacher:
        return
    
    if instance.teacher.role != 'teacher':
        return
    
    # Логируем только завершённые занятия
    if not instance.ended_at:
        return
    
    # Проверяем дубликаты
    existing = TeacherActivityLog.objects.filter(
        teacher=instance.teacher,
        action_type='lesson_conducted',
        details__lesson_id=instance.id
    ).exists()
    
    if existing:
        return
    
    TeacherActivityLog.objects.create(
        teacher=instance.teacher,
        action_type='lesson_conducted',
        details={
            'lesson_id': instance.id,
            'lesson_title': instance.title if hasattr(instance, 'title') else '',
            'group_id': instance.group_id if hasattr(instance, 'group_id') else None,
            'weight': EVENT_WEIGHTS['lesson_conducted'],
        }
    )


# ============================================================
# HOMEWORK SENSOR: Создание ДЗ
# ============================================================
@receiver(post_save, sender='homework.Homework')
def log_homework_created(sender, instance, created, **kwargs):
    """
    Логирует создание домашнего задания.
    """
    if not created:
        return
    
    # Определяем учителя
    teacher = None
    if hasattr(instance, 'teacher') and instance.teacher:
        teacher = instance.teacher
    elif hasattr(instance, 'created_by') and instance.created_by:
        teacher = instance.created_by
    
    if not teacher or teacher.role != 'teacher':
        return
    
    TeacherActivityLog.objects.create(
        teacher=teacher,
        action_type='homework_created',
        details={
            'homework_id': instance.id,
            'homework_title': instance.title if hasattr(instance, 'title') else '',
            'weight': EVENT_WEIGHTS['homework_created'],
        }
    )


# ============================================================
# GRADING SENSOR: Проверка ДЗ
# ============================================================
@receiver(post_save, sender='homework.StudentSubmission')
def log_homework_graded(sender, instance, created, **kwargs):
    """
    Логирует проверку домашнего задания (когда учитель ставит оценку).
    """
    # Только при обновлении статуса на 'graded'
    if instance.status != 'graded':
        return
    
    # Определяем учителя-проверяющего
    teacher = None
    if hasattr(instance, 'graded_by') and instance.graded_by:
        teacher = instance.graded_by
    elif hasattr(instance.homework, 'teacher') and instance.homework.teacher:
        teacher = instance.homework.teacher
    elif hasattr(instance.homework, 'created_by') and instance.homework.created_by:
        teacher = instance.homework.created_by
    
    if not teacher or teacher.role != 'teacher':
        return
    
    # Проверяем дубликаты
    existing = TeacherActivityLog.objects.filter(
        teacher=teacher,
        action_type='homework_graded',
        details__submission_id=instance.id
    ).exists()
    
    if existing:
        return
    
    TeacherActivityLog.objects.create(
        teacher=teacher,
        action_type='homework_graded',
        details={
            'submission_id': instance.id,
            'homework_id': instance.homework_id,
            'student_id': instance.student_id,
            'weight': EVENT_WEIGHTS['homework_graded'],
        }
    )


# ============================================================
# RECORDING SENSOR: Загрузка записи
# ============================================================
@receiver(post_save, sender='schedule.LessonRecording')
def log_recording_uploaded(sender, instance, created, **kwargs):
    """
    Логирует загрузку записи занятия.
    """
    if not created:
        return
    
    # Определяем учителя через lesson
    teacher = None
    if hasattr(instance, 'lesson') and instance.lesson and hasattr(instance.lesson, 'teacher'):
        teacher = instance.lesson.teacher
    elif hasattr(instance, 'uploaded_by') and instance.uploaded_by:
        teacher = instance.uploaded_by
    
    if not teacher or teacher.role != 'teacher':
        return
    
    TeacherActivityLog.objects.create(
        teacher=teacher,
        action_type='recording_uploaded',
        details={
            'recording_id': instance.id,
            'lesson_id': instance.lesson_id if hasattr(instance, 'lesson_id') else None,
            'weight': EVENT_WEIGHTS['recording_uploaded'],
        }
    )


# ============================================================
# LOGIN SENSOR: Вход в систему + создание сессии
# ============================================================
@receiver(user_logged_in)
def log_teacher_login(sender, request, user, **kwargs):
    """
    Логирует вход преподавателя и создаёт сессию для отслеживания времени.
    """
    # Только для учителей
    if not hasattr(user, 'role') or user.role != 'teacher':
        return
    
    # Проверяем, был ли уже логин сегодня
    today = timezone.now().date()
    existing_login = TeacherActivityLog.objects.filter(
        teacher=user,
        action_type='login',
        created_at__date=today
    ).exists()
    
    if not existing_login:
        TeacherActivityLog.objects.create(
            teacher=user,
            action_type='login',
            details={
                'ip_address': get_client_ip(request) if request else None,
                'weight': EVENT_WEIGHTS['login'],
            }
        )
    
    # Закрываем старые активные сессии
    TeacherSession.objects.filter(
        teacher=user,
        is_active=True
    ).update(is_active=False)
    
    # Создаём новую сессию
    TeacherSession.objects.create(teacher=user)


def get_client_ip(request):
    """Извлекает IP-адрес клиента из запроса."""
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


# ============================================================
# Вспомогательная функция для ручного логирования
# ============================================================
def log_teacher_activity(teacher, action_type, details=None):
    """
    Вспомогательная функция для ручного логирования активности преподавателя.
    Используется когда нельзя использовать сигналы.
    
    Пример:
        from analytics.teacher_signals import log_teacher_activity
        log_teacher_activity(request.user, 'student_feedback', {'student_id': 123})
    """
    if not teacher or teacher.role != 'teacher':
        return None
    
    if details is None:
        details = {}
    
    if 'weight' not in details:
        details['weight'] = EVENT_WEIGHTS.get(action_type, 1)
    
    return TeacherActivityLog.objects.create(
        teacher=teacher,
        action_type=action_type,
        details=details
    )
