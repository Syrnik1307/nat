"""
Сигналы для автоматического обновления карты знаний
при оценке домашних заданий.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from homework.models import Answer, StudentSubmission


@receiver(post_save, sender=StudentSubmission)
def update_knowledge_map_on_graded(sender, instance, **kwargs):
    """
    Когда ДЗ получает статус 'graded', обновить mastery по всем
    привязанным темам.
    """
    if instance.status != 'graded':
        return

    homework = instance.homework
    # Проверяем есть ли привязка к темам
    if not hasattr(homework, 'exam_topics') or not homework.exam_topics.exists():
        return

    from .models import StudentTopicMastery

    # Собираем результаты по ответам
    answers = Answer.objects.filter(submission=instance)
    total_score = 0
    total_max = 0
    total_time = 0

    for answer in answers:
        score = answer.teacher_score if answer.teacher_score is not None else (answer.auto_score or 0)
        max_score = answer.question.max_score if hasattr(answer.question, 'max_score') else 1
        total_score += score
        total_max += max_score
        total_time += answer.time_spent_seconds or 0

    if total_max == 0:
        return

    # Обновить mastery для каждой привязанной темы
    for topic in homework.exam_topics.all():
        mastery, created = StudentTopicMastery.objects.get_or_create(
            student=instance.student,
            topic=topic,
        )
        mastery.record_attempt(
            score=total_score,
            max_score=total_max,
            homework_id=homework.id,
            time_seconds=total_time,
        )
