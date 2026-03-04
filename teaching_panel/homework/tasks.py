from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .models import StudentSubmission
import logging

logger = logging.getLogger(__name__)


@shared_task(name='homework.tasks.notify_student_graded')
def notify_student_graded(submission_id: int):
    try:
        submission = StudentSubmission.objects.select_related('student', 'homework').get(id=submission_id)
    except StudentSubmission.DoesNotExist:
        return
    
    student = submission.student
    subject = f"Проверено: {submission.homework.title}"
    total = submission.total_score or 0
    message = (
        f"Здравствуйте, {student.first_name or student.email}!\n\n"
        f"Ваша работа по заданию '{submission.homework.title}' была проверена.\n"
        f"Итоговый балл: {total}.\n\n"
        f"Зайдите в систему, чтобы увидеть подробности и комментарии."
    )
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [student.email],
        fail_silently=True,
    )


# =============================================================================
# AI GRADING QUEUE — обработка очереди AI-проверки
# Все задачи защищёны feature flag AI_GRADING_ENABLED (default=False)
# =============================================================================

@shared_task(name='homework.tasks.process_ai_grading_queue', bind=True, max_retries=0)
def process_ai_grading_queue(self):
    """
    Берёт pending AI-задачи из очереди и обрабатывает через Gemini пул.
    Запускается каждые 30 сек через CELERY_BEAT_SCHEDULE.
    
    Feature flag: AI_GRADING_ENABLED=1 (иначе — no-op)
    """
    from .ai_grading_service import is_ai_grading_enabled, AIGradingService, NoAvailableKeyError
    from .models import AIGradingJob, AIGradingUsage

    if not is_ai_grading_enabled():
        return 'AI grading disabled'

    batch_size = getattr(settings, 'AI_GRADING_QUEUE_BATCH_SIZE', 10)
    max_retries = getattr(settings, 'AI_GRADING_MAX_RETRIES', 3)

    jobs = list(
        AIGradingJob.objects.filter(status='pending')
        .select_related('submission', 'homework', 'teacher', 'submission__student')
        .order_by('created_at')[:batch_size]
    )

    if not jobs:
        return 'No pending jobs'

    processed = 0
    for job in jobs:
        try:
            _process_single_job(job, max_retries)
            processed += 1
        except NoAvailableKeyError:
            # Все ключи исчерпаны — остальные jobs тоже не пройдут
            logger.warning("AI key pool exhausted, %d jobs left in queue", len(jobs) - processed)
            _send_pool_exhausted_alert(len(jobs) - processed)
            break
        except Exception as e:
            logger.exception("Error processing AI job #%d: %s", job.id, e)
            job.status = 'failed'
            job.error_message = str(e)[:500]
            job.completed_at = timezone.now()
            job.save(update_fields=['status', 'error_message', 'completed_at'])

    return f'Processed {processed}/{len(jobs)} jobs'


def _process_single_job(job, max_retries: int):
    """Обрабатывает одну AI-задачу."""
    from .ai_grading_service import AIGradingService, NoAvailableKeyError

    service = AIGradingService(provider=job.homework.ai_provider or 'gemini')

    # Проверка лимита учителя
    if not service.check_teacher_limit(job.teacher):
        job.status = 'manual_review'
        job.error_message = 'Месячный лимит AI-токенов учителя исчерпан'
        job.completed_at = timezone.now()
        job.save(update_fields=['status', 'error_message', 'completed_at'])
        _send_limit_exceeded_alert(job)
        # Fallback: submission stays as 'submitted' for manual review
        return

    # Пометить как processing
    job.status = 'processing'
    job.started_at = timezone.now()
    job.save(update_fields=['status', 'started_at'])

    # Вызов AI
    result = service.grade_submission_batch(
        submission=job.submission,
        teacher_prompt=job.homework.ai_grading_prompt or '',
    )

    if result.error:
        # Ошибка API
        job.retry_count += 1
        job.error_message = result.error[:500]
        if job.retry_count >= max_retries:
            job.status = 'failed'
            job.completed_at = timezone.now()
            logger.error("AI job #%d failed after %d retries: %s", job.id, max_retries, result.error)
        else:
            job.status = 'pending'  # Вернуть в очередь
            logger.info("AI job #%d retry %d/%d: %s", job.id, job.retry_count, max_retries, result.error)
        job.save(update_fields=['status', 'error_message', 'retry_count', 'completed_at'])
        
        # Если ошибка — NoAvailableKey, пробросить чтобы прекратить batch
        if 'исчерпаны' in result.error or 'Rate limited' in result.error:
            raise NoAvailableKeyError(result.error)
        return

    # Успешная проверка — записать результаты
    job.tokens_input = result.tokens_input
    job.tokens_output = result.tokens_output
    job.result = {
        'grades': [
            {
                'question_id': r.question_id,
                'score': r.score,
                'max_points': r.max_points,
                'feedback': r.feedback,
                'confidence': r.confidence,
            }
            for r in result.results
        ]
    }

    # Записать трекинг на учителя
    total_tokens = result.tokens_input + result.tokens_output
    service.record_teacher_usage(job.teacher, total_tokens)

    # Применить оценки к ответам
    threshold = job.homework.ai_confidence_threshold or 0.7
    has_low_confidence = False
    submission = job.submission

    for grade in result.results:
        try:
            answer = submission.answers.get(question_id=grade.question_id)
            answer.auto_score = grade.score
            answer.teacher_feedback = f"[AI] {grade.feedback}"
            
            if grade.confidence < threshold:
                has_low_confidence = True
                answer.needs_manual_review = True  # Оставить для ручной проверки
            else:
                answer.needs_manual_review = False
            
            answer.save(update_fields=['auto_score', 'teacher_feedback', 'needs_manual_review'])
        except Exception as e:
            logger.warning("Failed to apply AI grade for question %d: %s", grade.question_id, e)

    # Пересчёт итогового балла
    submission.compute_auto_score()

    # Определить итоговый статус
    if job.mode == 'auto_send' and not has_low_confidence:
        # Авторежим + все оценки уверенные → отправить ученику
        job.status = 'completed'
        submission.status = 'graded'
        submission.graded_at = timezone.now()
        submission.save(update_fields=['status', 'graded_at', 'total_score'])
        _send_student_ai_graded_notification(submission)
        _send_teacher_ai_completed_notification(job, auto_sent=True)
    elif job.mode == 'auto_send' and has_low_confidence:
        # Авторежим но AI не уверен → на ручную проверку + пинг учителю
        job.status = 'manual_review'
        submission.status = 'submitted'
        submission.save(update_fields=['status', 'total_score'])
        _send_teacher_low_confidence_alert(job)
    else:
        # Режим teacher_review → учитель проверит
        job.status = 'completed'
        submission.status = 'submitted'
        submission.save(update_fields=['status', 'total_score'])
        _send_teacher_ai_completed_notification(job, auto_sent=False)

    job.completed_at = timezone.now()
    job.save(update_fields=[
        'status', 'tokens_input', 'tokens_output', 'result',
        'error_message', 'completed_at',
    ])


@shared_task(name='homework.tasks.reset_daily_api_key_usage')
def reset_daily_api_key_usage():
    """Сбрасывает дневные счётчики на всех Gemini-ключах. Запуск: ежедневно 00:05 UTC."""
    from .ai_grading_service import is_ai_grading_enabled
    from .models import GeminiAPIKey

    if not is_ai_grading_enabled():
        return 'AI grading disabled'

    today = timezone.now().date()
    updated = GeminiAPIKey.objects.exclude(last_reset_date=today).update(
        requests_used_today=0,
        tokens_used_today=0,
        last_reset_date=today,
    )
    # Снять disabled_until у ключей с восстановленными лимитами
    GeminiAPIKey.objects.filter(
        disabled_until__lt=timezone.now()
    ).update(disabled_until=None)

    return f'Reset {updated} keys'


@shared_task(name='homework.tasks.send_ai_usage_weekly_report')
def send_ai_usage_weekly_report():
    """Еженедельный отчёт по расходу AI-токенов в Telegram админу."""
    from .ai_grading_service import is_ai_grading_enabled
    from .models import GeminiAPIKey, AIGradingUsage, AIGradingJob
    from datetime import date, timedelta

    if not is_ai_grading_enabled():
        return 'AI grading disabled'

    today = date.today()
    month_start = today.replace(day=1)
    week_ago = today - timedelta(days=7)

    # Суммарный расход за месяц
    monthly_usage = AIGradingUsage.objects.filter(month=month_start)
    total_tokens = sum(u.tokens_used for u in monthly_usage)
    total_requests = sum(u.requests_count for u in monthly_usage)
    total_submissions = sum(u.submissions_graded for u in monthly_usage)

    # Топ учителей
    top_teachers = monthly_usage.order_by('-tokens_used')[:5]
    top_list = '\n'.join(
        f"  {u.teacher.email}: {u.tokens_used:,} tok"
        for u in top_teachers.select_related('teacher')
    ) or '  (нет данных)'

    # Состояние пула
    keys = GeminiAPIKey.objects.filter(is_active=True)
    total_daily_capacity = sum(k.daily_token_limit for k in keys)
    total_used_today = sum(k.tokens_used_today for k in keys)

    # Прогноз
    days_in_month = 30
    if total_requests > 0 and total_tokens > 0:
        avg_daily = total_tokens / max(1, (today - month_start).days or 1)
        days_remaining_capacity = total_daily_capacity / max(1, avg_daily) if avg_daily > 0 else 999
    else:
        avg_daily = 0
        days_remaining_capacity = 999

    # Jobs stats
    jobs_week = AIGradingJob.objects.filter(created_at__date__gte=week_ago)
    jobs_completed = jobs_week.filter(status='completed').count()
    jobs_failed = jobs_week.filter(status='failed').count()
    jobs_manual = jobs_week.filter(status='manual_review').count()
    jobs_pending = AIGradingJob.objects.filter(status='pending').count()

    message = (
        f"AI-проверка ДЗ: недельный отчёт\n\n"
        f"Месяц {month_start:%Y-%m}:\n"
        f"  Токены: {total_tokens:,}\n"
        f"  Запросы: {total_requests}\n"
        f"  Работы проверены: {total_submissions}\n\n"
        f"Топ учителей:\n{top_list}\n\n"
        f"Пул ключей:\n"
        f"  Активных: {keys.count()}\n"
        f"  Дневной лимит: {total_daily_capacity:,} tok\n"
        f"  Использовано сегодня: {total_used_today:,} tok\n\n"
        f"За неделю: {jobs_completed} OK, {jobs_failed} ошибок, "
        f"{jobs_manual} на ручную проверку\n"
        f"В очереди сейчас: {jobs_pending}\n\n"
        f"Прогноз: ср.расход {int(avg_daily):,} tok/день"
    )

    _send_admin_telegram(message)
    return f'Report sent: {total_tokens:,} tokens this month'


@shared_task(name='homework.tasks.check_ai_pool_capacity')
def check_ai_pool_capacity():
    """Проверяет оставшуюся ёмкость пула. Алерт если <20%."""
    from .ai_grading_service import is_ai_grading_enabled
    from .models import GeminiAPIKey

    if not is_ai_grading_enabled():
        return 'AI grading disabled'

    warning_percent = getattr(settings, 'AI_GRADING_POOL_WARNING_PERCENT', 20)
    keys = GeminiAPIKey.objects.filter(is_active=True)
    
    if not keys.exists():
        return 'No active keys'

    total_limit = sum(k.daily_token_limit for k in keys)
    total_used = sum(k.tokens_used_today for k in keys)
    
    if total_limit == 0:
        return 'No capacity'

    remaining_pct = ((total_limit - total_used) / total_limit) * 100

    if remaining_pct < warning_percent:
        message = (
            f"AI-проверка: мало ресурсов\n\n"
            f"Осталось {remaining_pct:.0f}% дневного лимита токенов!\n"
            f"Использовано: {total_used:,} / {total_limit:,}\n\n"
            f"Рекомендуется добавить ключей или дождаться сброса (00:00 UTC)."
        )
        _send_admin_telegram(message)
        return f'Alert sent: {remaining_pct:.0f}% remaining'

    return f'{remaining_pct:.0f}% remaining - OK'


# =============================================================================
# Notification helpers
# =============================================================================

def _send_student_ai_graded_notification(submission):
    """Уведомление ученику: AI проверил и отправил работу."""
    try:
        from accounts.notifications import send_telegram_notification
        student = submission.student
        hw_title = submission.homework.title
        score = submission.total_score or 0
        max_score = sum(q.points for q in submission.homework.questions.all()) or 100
        percent = round((score / max_score) * 100) if max_score > 0 else 0
        
        message = (
            f"ДЗ проверено\n"
            f"Ваша работа '{hw_title}' проверена.\n"
            f"Результат: {score}/{max_score} ({percent}%).\n"
            f"Откройте Lectio Space для подробностей."
        )
        send_telegram_notification(student, 'homework_graded', message)
    except Exception as e:
        logger.warning("Failed to send AI graded notification: %s", e)


def _send_teacher_ai_completed_notification(job, auto_sent: bool):
    """Уведомление учителю: AI проверил работу."""
    try:
        from accounts.notifications import send_telegram_notification
        teacher = job.teacher
        student = job.submission.student
        student_name = student.get_full_name() or student.email
        hw_title = job.homework.title
        score = job.submission.total_score or 0
        
        if auto_sent:
            message = (
                f"AI проверил ДЗ\n"
                f"{student_name}: '{hw_title}'\n"
                f"Результат: {score} баллов. Работа отправлена ученику.\n"
                f"Вы можете просмотреть и скорректировать оценку."
            )
        else:
            message = (
                f"AI проверил ДЗ — ждёт подтверждения\n"
                f"{student_name}: '{hw_title}'\n"
                f"Предварительный результат: {score} баллов.\n"
                f"Откройте Lectio Space, чтобы подтвердить или изменить оценку."
            )
        send_telegram_notification(teacher, 'homework_submitted', message)
    except Exception as e:
        logger.warning("Failed to send AI completed notification: %s", e)


def _send_teacher_low_confidence_alert(job):
    """Пинг учителю: AI не уверен в оценке."""
    try:
        from accounts.notifications import send_telegram_notification
        teacher = job.teacher
        student = job.submission.student
        student_name = student.get_full_name() or student.email
        hw_title = job.homework.title
        
        message = (
            f"AI не уверен в оценке\n"
            f"{student_name}: '{hw_title}'\n"
            f"AI оценил работу, но уверенность низкая.\n"
            f"Работа ожидает вашей ручной проверки."
        )
        send_telegram_notification(teacher, 'homework_submitted', message)
    except Exception as e:
        logger.warning("Failed to send low confidence alert: %s", e)


def _send_limit_exceeded_alert(job):
    """Пинг учителю: лимит AI-токенов исчерпан."""
    try:
        from accounts.notifications import send_telegram_notification
        teacher = job.teacher
        
        message = (
            f"Лимит AI-проверки исчерпан\n"
            f"Ваш месячный лимит AI-токенов достигнут.\n"
            f"Новые работы будут ожидать ручной проверки.\n"
            f"Лимит обновится 1-го числа следующего месяца."
        )
        send_telegram_notification(teacher, 'homework_submitted', message)
    except Exception as e:
        logger.warning("Failed to send limit exceeded alert: %s", e)


def _send_pool_exhausted_alert(pending_count: int):
    """Алерт админу: все ключи Gemini исчерпаны."""
    message = (
        f"AI пул ключей исчерпан\n\n"
        f"Все Gemini API ключи исчерпаны или отключены.\n"
        f"В очереди: {pending_count} работ.\n"
        f"Добавьте ключей в Django Admin или дождитесь сброса лимитов."
    )
    _send_admin_telegram(message)


def _send_admin_telegram(message: str):
    """Отправляет сообщение админу в Telegram."""
    try:
        from accounts.notifications import send_telegram_notification
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        admins = User.objects.filter(role='admin', telegram_chat_id__isnull=False).exclude(telegram_chat_id='')
        for admin in admins[:3]:  # Не больше 3 админов
            send_telegram_notification(admin, 'homework_submitted', message)
    except Exception as e:
        logger.warning("Failed to send admin telegram: %s", e)
