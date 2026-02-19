"""
Webhook endpoint для Kinescope.

Kinescope отправляет POST-запросы при изменении статуса видео:
- video.status.done — видео обработано и готово к воспроизведению
- video.status.error — ошибка обработки

Документация: https://kinescope.io/dev/api/webhooks
"""
import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from core.models import CourseLesson

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def kinescope_webhook(request):
    """
    Обработка webhook-событий от Kinescope.

    Kinescope присылает JSON с информацией об изменении статуса видео.
    Мы обновляем video_status и embed URL у соответствующего урока.
    """
    # Проверка подписи (если настроен секрет)
    webhook_secret = getattr(settings, 'KINESCOPE_WEBHOOK_SECRET', '')
    if webhook_secret:
        signature = request.headers.get('X-Kinescope-Signature', '')
        expected = hmac.new(
            webhook_secret.encode(),
            request.body,
            hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            logger.warning('Kinescope webhook: invalid signature')
            return JsonResponse({'error': 'Invalid signature'}, status=403)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    event_type = payload.get('type', '')
    video_data = payload.get('data', {})
    video_id = video_data.get('id', '')

    if not video_id:
        logger.warning('Kinescope webhook: no video_id in payload')
        return JsonResponse({'status': 'ignored', 'reason': 'no video_id'})

    logger.info('Kinescope webhook: event=%s, video_id=%s', event_type, video_id)

    # Находим урок по kinescope_video_id
    try:
        lesson = CourseLesson.objects.get(kinescope_video_id=video_id)
    except CourseLesson.DoesNotExist:
        logger.info('Kinescope webhook: no lesson found for video_id=%s', video_id)
        return JsonResponse({'status': 'ignored', 'reason': 'lesson not found'})
    except CourseLesson.MultipleObjectsReturned:
        lesson = CourseLesson.objects.filter(kinescope_video_id=video_id).first()

    # Обработка событий
    if event_type in ('video.status.done', 'video.done'):
        lesson.video_status = CourseLesson.VideoStatus.READY
        embed_link = video_data.get('embed_link', '')
        if embed_link:
            lesson.kinescope_embed_url = embed_link
            lesson.video_url = embed_link
        duration = video_data.get('duration', 0)
        if duration:
            minutes = int(duration // 60)
            lesson.duration = f'{minutes} мин' if minutes else '< 1 мин'
        lesson.save(update_fields=[
            'video_status', 'kinescope_embed_url', 'video_url', 'duration',
        ])
        logger.info('Kinescope webhook: lesson %d marked as READY', lesson.id)

    elif event_type in ('video.status.error', 'video.error'):
        lesson.video_status = CourseLesson.VideoStatus.ERROR
        lesson.save(update_fields=['video_status'])
        logger.error('Kinescope webhook: lesson %d video processing ERROR', lesson.id)

    elif event_type in ('video.status.processing', 'video.processing'):
        lesson.video_status = CourseLesson.VideoStatus.PROCESSING
        lesson.save(update_fields=['video_status'])

    else:
        logger.info('Kinescope webhook: unhandled event type "%s"', event_type)

    return JsonResponse({'status': 'ok'})
