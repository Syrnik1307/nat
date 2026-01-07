"""
Zoom Webhook Handler для автоматической обработки записей уроков
"""
import hashlib
import hmac
import json
import logging
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import Lesson, LessonRecording
from .tasks import process_zoom_recording

logger = logging.getLogger(__name__)


def verify_zoom_webhook(request):
    """
    Проверяет подлинность webhook запроса от Zoom
    https://marketplace.zoom.us/docs/api-reference/webhook-reference/#verify-webhook-events
    """
    # Получаем секретный токен из настроек Zoom
    secret_token = getattr(settings, 'ZOOM_WEBHOOK_SECRET_TOKEN', None)
    
    if not secret_token:
        logger.warning("ZOOM_WEBHOOK_SECRET_TOKEN not configured in settings")
        return False
    
    # Получаем подпись из заголовка
    timestamp = request.headers.get('x-zm-request-timestamp', '')
    signature = request.headers.get('x-zm-signature', '')
    
    if not timestamp or not signature:
        logger.warning("Missing Zoom webhook headers")
        return False
    
    # Формируем строку для проверки: v0:timestamp:request_body
    message = f'v0:{timestamp}:{request.body.decode("utf-8")}'
    
    # Вычисляем HMAC SHA256
    hash_for_verify = hmac.new(
        secret_token.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # Формируем ожидаемую подпись
    expected_signature = f'v0={hash_for_verify}'
    
    # Сравниваем подписи (защита от timing attacks)
    return hmac.compare_digest(signature, expected_signature)


@csrf_exempt
@require_POST
def zoom_webhook(request):
    """
    Главный endpoint для приема webhook от Zoom
    URL: /api/zoom/webhook/
    """
    try:
        # Парсим JSON payload
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            logger.error("Invalid JSON in webhook payload")
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        
        # Получаем тип события
        event_type = payload.get('event')
        
        logger.info(f"Received Zoom webhook: {event_type}")
        
        # Zoom требует ответить на URL validation challenge
        # При валидации Zoom НЕ отправляет подпись, поэтому пропускаем проверку
        if event_type == 'endpoint.url_validation':
            return handle_url_validation(payload)
        
        # Для всех остальных событий проверяем подпись
        if not verify_zoom_webhook(request):
            logger.warning(f"Invalid Zoom webhook signature from {request.META.get('REMOTE_ADDR')}")
            return JsonResponse({'error': 'Invalid signature'}, status=403)
        
        # Обрабатываем событие завершения записи
        elif event_type == 'recording.completed':
            return handle_recording_completed(payload)
        
        # Обрабатываем удаление записи (если нужно синхронизировать)
        elif event_type == 'recording.trashed':
            return handle_recording_trashed(payload)
        
        # Неизвестное событие — логируем но не обрабатываем
        else:
            logger.info(f"Unhandled Zoom webhook event: {event_type}")
            return JsonResponse({'status': 'ignored'}, status=200)
    
    except Exception as e:
        logger.exception(f"Error processing Zoom webhook: {e}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


def handle_url_validation(payload):
    """
    Обработка Zoom URL validation challenge
    При первой настройке webhook Zoom отправляет этот запрос
    """
    plain_token = payload.get('payload', {}).get('plainToken')
    
    if not plain_token:
        logger.error("Missing plainToken in URL validation request")
        return JsonResponse({'error': 'Missing plainToken'}, status=400)
    
    # Zoom требует зашифровать токен с помощью секрета
    secret_token = getattr(settings, 'ZOOM_WEBHOOK_SECRET_TOKEN', '')
    
    encrypted_token = hmac.new(
        secret_token.encode('utf-8'),
        plain_token.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    logger.info("Zoom webhook URL validation successful")
    
    return JsonResponse({
        'plainToken': plain_token,
        'encryptedToken': encrypted_token
    })


def handle_recording_completed(payload):
    """
    Обработка события recording.completed
    Запускает фоновую задачу для скачивания и загрузки в Google Drive
    """
    try:
        # Извлекаем данные о записи
        recording_data = payload.get('payload', {}).get('object', {})
        
        meeting_id = recording_data.get('id')  # UUID встречи
        meeting_uuid = recording_data.get('uuid')
        topic = recording_data.get('topic', 'Unknown')
        start_time = recording_data.get('start_time')
        
        # Получаем список файлов записи
        recording_files = recording_data.get('recording_files', [])
        
        if not recording_files:
            logger.warning(f"No recording files found for meeting {meeting_id}")
            return JsonResponse({'status': 'no_files'}, status=200)
        
        logger.info(f"Processing {len(recording_files)} recording files for meeting {meeting_id}")
        
        # Находим урок по Zoom meeting ID
        try:
            lesson = Lesson.objects.get(zoom_meeting_id=meeting_id)
        except Lesson.DoesNotExist:
            logger.warning(f"Lesson not found for Zoom meeting {meeting_id}")
            return JsonResponse({'status': 'lesson_not_found'}, status=200)
        except Lesson.MultipleObjectsReturned:
            logger.error(f"Multiple lessons found for Zoom meeting {meeting_id}")
            lesson = Lesson.objects.filter(zoom_meeting_id=meeting_id).first()
        
        # Проверяем что запись включена для этого урока
        if not lesson.record_lesson:
            logger.info(f"Recording disabled for lesson {lesson.id}, skipping")
            return JsonResponse({'status': 'recording_disabled'}, status=200)
        
        # Обрабатываем каждый файл записи
        processed_count = 0
        
        for file_data in recording_files:
            file_type = file_data.get('file_type', '').lower()
            
            # Пропускаем chat, timeline и другие не-видео/не-транскрипт файлы
            if file_type not in ['mp4', 'm4a', 'transcript']:
                continue
            
            recording_id = file_data.get('id')
            download_url = file_data.get('download_url')
            play_url = file_data.get('play_url')
            file_size = file_data.get('file_size', 0)
            recording_type = file_data.get('recording_type', '')  # shared_screen_with_speaker_view, etc
            
            if not download_url:
                logger.warning(f"No download URL for recording file {recording_id}")
                continue
            
            # Создаем или обновляем запись LessonRecording
            lesson_recording, created = LessonRecording.objects.get_or_create(
                lesson=lesson,
                zoom_recording_id=recording_id,
                defaults={
                    'download_url': download_url,
                    'play_url': play_url or '',
                    'file_size': file_size,
                    'recording_type': recording_type,
                    'status': 'processing',
                    'storage_provider': 'gdrive'
                }
            )
            
            if not created:
                # Обновляем существующую запись
                lesson_recording.download_url = download_url
                lesson_recording.play_url = play_url or ''
                lesson_recording.file_size = file_size
                lesson_recording.status = 'processing'
                lesson_recording.save()

            # Применяем настройки приватности из урока если они есть
            privacy_type = LessonRecording.Visibility.LESSON_GROUP
            allowed_groups = []
            allowed_students = []
            
            # Пытаемся извлечь настройки приватности из notes урока
            if lesson.notes and 'Privacy:' in lesson.notes:
                import json
                try:
                    # Извлекаем JSON строку из notes
                    privacy_json = lesson.notes.split('Privacy: ', 1)[1].strip()
                    privacy_settings = json.loads(privacy_json)
                    
                    privacy_type_str = privacy_settings.get('privacy_type', 'all')
                    if privacy_type_str == 'groups':
                        privacy_type = LessonRecording.Visibility.CUSTOM_GROUPS
                        allowed_groups = privacy_settings.get('allowed_groups', [])
                    elif privacy_type_str == 'students':
                        privacy_type = LessonRecording.Visibility.CUSTOM_STUDENTS
                        allowed_students = privacy_settings.get('allowed_students', [])
                    elif privacy_type_str == 'all':
                        privacy_type = LessonRecording.Visibility.ALL_TEACHER_GROUPS
                except (json.JSONDecodeError, IndexError) as e:
                    logger.warning(f"Failed to parse privacy settings from lesson notes: {e}")

            lesson_recording.apply_privacy(
                privacy_type=privacy_type,
                group_ids=allowed_groups,
                student_ids=allowed_students,
                teacher=lesson.teacher
            )
            
            logger.info(f"{'Created' if created else 'Updated'} LessonRecording {lesson_recording.id}")
            
            # Запускаем фоновую задачу для обработки
            process_zoom_recording.delay(lesson_recording.id)
            
            processed_count += 1
        
        logger.info(f"Queued {processed_count} recording(s) for processing")
        
        return JsonResponse({
            'status': 'success',
            'lesson_id': lesson.id,
            'processed_files': processed_count
        })
    
    except Exception as e:
        logger.exception(f"Error handling recording.completed: {e}")
        return JsonResponse({'error': str(e)}, status=500)


def handle_recording_trashed(payload):
    """
    Обработка события recording.trashed
    Помечаем запись как deleted в нашей БД
    """
    try:
        recording_data = payload.get('payload', {}).get('object', {})
        meeting_id = recording_data.get('id')
        
        # Обновляем статус всех записей этой встречи
        updated = LessonRecording.objects.filter(
            lesson__zoom_meeting_id=meeting_id
        ).update(status='deleted')
        
        logger.info(f"Marked {updated} recording(s) as deleted for meeting {meeting_id}")
        
        return JsonResponse({
            'status': 'success',
            'updated_count': updated
        })
    
    except Exception as e:
        logger.exception(f"Error handling recording.trashed: {e}")
        return JsonResponse({'error': str(e)}, status=500)
