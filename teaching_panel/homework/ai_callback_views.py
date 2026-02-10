"""
Callback endpoint — принимает результаты AI-проверки от worker-а.

Аутентификация: HMAC-SHA256 подпись (не JWT — worker не имеет пользователя).
URL: POST /api/internal/ai-grading/callback/

Этот endpoint вызывается ТОЛЬКО из AI worker, не из фронтенда.
"""

import hmac
import hashlib
import json
import logging
from decimal import Decimal

from django.conf import settings
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

logger = logging.getLogger(__name__)


def verify_hmac_signature(request) -> bool:
    """Проверяет HMAC-SHA256 подпись из заголовка X-AI-Signature."""
    signature = request.headers.get('X-AI-Signature', '')
    if not signature:
        logger.warning("AI callback: missing X-AI-Signature header")
        return False

    secret = settings.AI_CALLBACK_SECRET
    expected = hmac.new(
        secret.encode('utf-8'),
        request.body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(signature, expected)


@api_view(['POST'])
@authentication_classes([])  # Не JWT — HMAC auth
@permission_classes([AllowAny])  # Проверяем вручную через HMAC
def ai_grading_callback(request):
    """
    Принимает результат AI-проверки от worker-а.
    
    Успешный результат: обновляет Answer с оценкой.
    Ошибка: помечает Answer для ручной проверки.
    """
    # 1. Проверка HMAC подписи
    if not verify_hmac_signature(request):
        logger.error("AI callback: HMAC verification failed")
        return Response({'error': 'Invalid signature'}, status=403)

    data = request.data
    task_id = data.get('task_id', 'unknown')
    status = data.get('status')

    logger.info(f"AI callback received: task={task_id}, status={status}")

    try:
        if status == 'completed':
            return _handle_completed(data)
        elif status == 'failed':
            return _handle_failed(data)
        else:
            logger.warning(f"AI callback: unknown status '{status}' for task {task_id}")
            return Response({'error': f'Unknown status: {status}'}, status=400)
    except Exception as e:
        logger.exception(f"AI callback processing error: task={task_id}")
        return Response({'error': str(e)}, status=500)


def _handle_completed(data: dict) -> Response:
    """Обрабатывает успешный результат AI-проверки."""
    from homework.models import Answer

    result = data.get('result', {})
    answer_id = result.get('answer_id')

    if not answer_id:
        return Response({'error': 'Missing answer_id'}, status=400)

    try:
        answer = Answer.objects.select_related(
            'submission', 'question'
        ).get(id=answer_id)
    except Answer.DoesNotExist:
        logger.error(f"AI callback: Answer {answer_id} not found")
        return Response({'error': 'Answer not found'}, status=404)

    # Обновляем поля Answer
    metadata = result.get('ai_metadata', {})
    confidence = result.get('confidence', 0.0)

    answer.auto_score = result.get('score')
    answer.ai_confidence = confidence
    answer.needs_manual_review = result.get('needs_manual_review', confidence < 0.7)
    answer.ai_grading_status = 'completed'
    answer.ai_checked_at = timezone.now()
    answer.ai_provider_used = metadata.get('provider', '')
    answer.ai_tokens_used = metadata.get('input_tokens', 0) + metadata.get('output_tokens', 0)
    answer.ai_latency_ms = metadata.get('latency_ms')

    # Стоимость
    cost = metadata.get('cost_rubles')
    if cost is not None:
        answer.ai_cost_rubles = Decimal(str(cost))

    # Feedback с пометкой AI
    feedback = result.get('feedback', '')
    answer.teacher_feedback = f"[AI оценка, уверенность: {confidence:.0%}] {feedback}"

    answer.save(update_fields=[
        'auto_score', 'ai_confidence', 'needs_manual_review',
        'ai_grading_status', 'ai_checked_at', 'ai_provider_used',
        'ai_tokens_used', 'ai_latency_ms', 'ai_cost_rubles',
        'teacher_feedback',
    ])

    # Пересчитываем total_score на submission
    answer.submission.recalculate_total()

    # Уведомляем студента (если все ответы проверены)
    _maybe_notify_student(answer.submission)

    logger.info(
        f"AI grading completed: answer={answer_id}, "
        f"score={answer.auto_score}/{answer.question.points}, "
        f"confidence={confidence:.0%}, provider={answer.ai_provider_used}"
    )

    return Response({'status': 'ok', 'answer_id': answer_id})


def _handle_failed(data: dict) -> Response:
    """Обрабатывает ошибку AI-проверки → ручная проверка."""
    from homework.models import Answer

    fallback = data.get('fallback', {})
    error_info = data.get('error', {})
    answer_id = fallback.get('answer_id')

    if not answer_id:
        return Response({'error': 'Missing answer_id in fallback'}, status=400)

    try:
        answer = Answer.objects.get(id=answer_id)
    except Answer.DoesNotExist:
        logger.error(f"AI callback failed: Answer {answer_id} not found")
        return Response({'error': 'Answer not found'}, status=404)

    error_code = error_info.get('code', 'UNKNOWN')
    error_msg = error_info.get('message', 'Unknown error')

    answer.ai_grading_status = 'failed'
    answer.needs_manual_review = True
    answer.teacher_feedback = f"[AI недоступен: {error_code}] Требуется ручная проверка"
    answer.ai_checked_at = timezone.now()
    answer.save(update_fields=[
        'ai_grading_status', 'needs_manual_review',
        'teacher_feedback', 'ai_checked_at',
    ])

    logger.warning(
        f"AI grading failed: answer={answer_id}, "
        f"error={error_code}: {error_msg}, "
        f"retries={error_info.get('retries_attempted', 0)}"
    )

    return Response({'status': 'ok', 'answer_id': answer_id, 'fallback': True})


def _maybe_notify_student(submission):
    """Уведомляет студента, если все ответы уже проверены (AI или учитель)."""
    from homework.models import Answer

    pending_count = Answer.objects.filter(
        submission=submission,
        auto_score__isnull=True,
        teacher_score__isnull=True,
    ).exclude(
        ai_grading_status='pending'
    ).exclude(
        ai_grading_status='processing'
    ).count()

    if pending_count == 0:
        from homework.tasks import notify_student_graded
        notify_student_graded.delay(submission.id)
