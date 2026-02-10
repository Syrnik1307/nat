"""
Celery задачи для модуля экзаменов.

Основная задача — автоматическая сдача экзаменов при истечении таймера.
"""

from celery import shared_task
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@shared_task(name='exam.auto_submit_expired')
def auto_submit_expired_exams():
    """
    Автоматическая сдача просроченных экзаменов.
    
    Запускается по расписанию (каждую минуту).
    Находит все ExamAttempt с deadline_at < now и status='in_progress'.
    """
    from exam.models import ExamAttempt
    
    now = timezone.now()
    
    expired_attempts = ExamAttempt.objects.filter(
        deadline_at__lt=now,
        auto_submitted=False,
        submission__status='in_progress',
    ).select_related('submission', 'variant', 'variant__blueprint')
    
    count = 0
    for attempt in expired_attempts:
        try:
            _force_submit_attempt(attempt)
            count += 1
            logger.info(
                f'Auto-submitted exam attempt {attempt.id} '
                f'(student={attempt.submission.student_id}, '
                f'variant={attempt.variant_id})'
            )
        except Exception as e:
            logger.error(
                f'Failed to auto-submit attempt {attempt.id}: {e}',
                exc_info=True
            )
    
    if count:
        logger.info(f'Auto-submitted {count} expired exam attempts')
    
    return count


def _force_submit_attempt(attempt):
    """Принудительная сдача одной попытки."""
    from django.db import transaction
    
    with transaction.atomic():
        attempt.auto_submitted = True
        
        if attempt.started_at:
            attempt.time_spent_seconds = int(
                (timezone.now() - attempt.started_at).total_seconds()
            )
        
        attempt.save(update_fields=['auto_submitted', 'time_spent_seconds'])
        
        submission = attempt.submission
        submission.status = 'submitted'
        submission.submitted_at = timezone.now()
        submission.save(update_fields=['status', 'submitted_at'])
        
        # Автопроверка
        for answer in submission.answers.select_related('question').all():
            answer.evaluate()
            answer.save()
        
        submission.compute_auto_score()
        
        # Если нет ручной проверки — сразу graded
        needs_manual = submission.answers.filter(needs_manual_review=True).exists()
        if not needs_manual:
            submission.status = 'graded'
            submission.graded_at = timezone.now()
            submission.save(update_fields=['status', 'graded_at'])
        
        # Считаем итоговые баллы
        attempt.calculate_scores()
