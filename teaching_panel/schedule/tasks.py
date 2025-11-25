"""
Celery задачи для приложения schedule
"""
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import ZoomAccount, Lesson
from zoom_pool.models import ZoomAccount as PoolZoomAccount


@shared_task
def release_stuck_zoom_accounts():
    """
    Освобождение зависших Zoom-аккаунтов
    
    Задача запускается каждые 10 минут через Celery Beat.
    Находит аккаунты, которые:
    - Помечены как is_busy=True
    - Привязаны к уроку (current_lesson не None)
    - Урок закончился более 15 минут назад
    
    Освобождает такие аккаунты для повторного использования.
    """
    now = timezone.now()
    released_count = 0
    
    # Находим все занятые аккаунты с привязанными уроками
    stuck_accounts = ZoomAccount.objects.filter(
        is_busy=True,
        current_lesson__isnull=False
    ).select_related('current_lesson')
    
    for account in stuck_accounts:
        lesson = account.current_lesson
        
        # Проверяем, что урок закончился более 15 минут назад
        grace_period = timedelta(minutes=15)
        if lesson.end_time and lesson.end_time + grace_period < now:
            # Освобождаем аккаунт
            account.is_busy = False
            account.current_lesson = None
            account.save()
            
            released_count += 1
            
            # Логируем освобождение
            print(f"[Celery] Освобожден зависший аккаунт {account.name} "
                  f"(урок #{lesson.id} закончился в {lesson.end_time})")
    
    # Также проверяем аккаунты без привязанного урока, но is_busy=True
    # (это может произойти при сбое)
    orphaned_accounts = ZoomAccount.objects.filter(
        is_busy=True,
        current_lesson__isnull=True
    )
    
    orphaned_count = orphaned_accounts.count()
    if orphaned_count > 0:
        orphaned_accounts.update(is_busy=False)
        print(f"[Celery] Освобождено {orphaned_count} 'осиротевших' аккаунтов (is_busy=True без урока)")
    
    total_released = released_count + orphaned_count
    
    if total_released > 0:
        print(f"[Celery] Итого освобождено аккаунтов: {total_released}")
    
    return {
        'released_stuck': released_count,
        'released_orphaned': orphaned_count,
        'total': total_released,
        'timestamp': now.isoformat()
    }


@shared_task
def release_finished_zoom_accounts():
    """Освобождает аккаунты из нового пула zoom_pool, если встречи завершились.

    Логика:
    - Берём активные аккаунты с current_meetings > 0
    - Смотрим связанные уроки (поле Lesson.zoom_account)
    - Если урок закончился (end_time < now - 5 минут) → уменьшаем счётчик и обнуляем связь.
    - Счётчик снижается на количество завершённых уроков, но не ниже 0.
    """
    from schedule.models import Lesson
    
    now = timezone.now()
    processed = 0
    released_total = 0
    grace = timezone.timedelta(minutes=5)

    busy_accounts = PoolZoomAccount.objects.filter(current_meetings__gt=0)
    for account in busy_accounts:
        lessons = account.assigned_lessons.all()
        finished_count = 0
        for lesson in lessons:
            if lesson.end_time and lesson.end_time + grace < now:
                # Очищаем связь с аккаунтом
                lesson.zoom_account = None
                lesson.save()
                finished_count += 1
        
        if finished_count:
            old_value = account.current_meetings
            account.current_meetings = max(0, account.current_meetings - finished_count)
            account.save()
            released_total += (old_value - account.current_meetings)
        processed += 1

    if released_total:
        print(f"[Celery] release_finished_zoom_accounts: освобождено {released_total} встреч, аккаунтов обработано {processed}")
    return {
        'accounts_processed': processed,
        'meetings_released': released_total,
        'timestamp': now.isoformat()
    }


@shared_task
def send_lesson_reminder(lesson_id, minutes_before=15):
    """
    Отправка напоминания о начале урока (будущая функция)
    
    Args:
        lesson_id: ID урока
        minutes_before: за сколько минут до начала отправить
    """
    try:
        lesson = Lesson.objects.get(id=lesson_id)
        # TODO: Реализовать отправку email/push уведомлений
        print(f"[Celery] Напоминание об уроке {lesson.title} "
              f"для группы {lesson.group.name} через {minutes_before} минут")
        return {'status': 'sent', 'lesson_id': lesson_id}
    except Lesson.DoesNotExist:
        print(f"[Celery] Урок #{lesson_id} не найден")
        return {'status': 'error', 'message': 'Lesson not found'}


@shared_task
def schedule_upcoming_lesson_reminders():
    """Планировщик: находит уроки, которые начнутся через X минут и ставит задачу напоминания.
    Небольшой шаг для демонстрации. В реале можно хранить flag, чтобы не слать повторно."""
    window_minutes = 15
    now = timezone.now()
    target_start = now + timedelta(minutes=window_minutes)
    lessons = Lesson.objects.filter(start_time__gte=now, start_time__lte=target_start)
    scheduled = 0
    for lesson in lessons:
        send_lesson_reminder.delay(lesson.id, minutes_before=window_minutes)
        scheduled += 1
    if scheduled:
        print(f"[Celery] Запланировано напоминаний: {scheduled}")
    return {'scheduled': scheduled, 'timestamp': now.isoformat()}


@shared_task
def archive_zoom_recordings():
    """
    Архивирование Zoom записей в постоянное хранилище (S3/Azure Blob)
    
    Логика:
    1. Находит записи со статусом 'completed' без архива
    2. Скачивает с Zoom Cloud
    3. Загружает в S3/Azure Blob Storage
    4. Обновляет запись: archive_url, archive_key, archived_at, status='archived'
    5. Опционально: удаляет из Zoom Cloud для экономии
    
    Требует настройки:
    - AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_STORAGE_BUCKET_NAME
    - или AZURE_STORAGE_CONNECTION_STRING, AZURE_STORAGE_CONTAINER_NAME
    """
    from schedule.models import LessonRecording
    import logging
    import os
    
    logger = logging.getLogger(__name__)
    
    # Проверка конфигурации хранилища
    storage_type = os.getenv('RECORDING_STORAGE_TYPE', 'none')  # 's3', 'azure', or 'none'
    
    if storage_type == 'none':
        logger.info("[Celery] archive_zoom_recordings: архивирование отключено (RECORDING_STORAGE_TYPE=none)")
        return {'status': 'disabled', 'message': 'Storage not configured'}
    
    # Находим записи для архивирования
    recordings_to_archive = LessonRecording.objects.filter(
        status='completed',
        archive_url='',
    ).select_related('lesson')[:10]  # Лимит 10 за раз
    
    archived_count = 0
    failed_count = 0
    
    for recording in recordings_to_archive:
        try:
            logger.info(f"[Celery] Архивируем запись {recording.id} для урока {recording.lesson.id}")
            
            # TODO: Реализация загрузки в S3/Azure
            # if storage_type == 's3':
            #     archive_key = f"recordings/{recording.lesson.id}/{recording.zoom_recording_id}.mp4"
            #     upload_to_s3(recording.download_url, archive_key)
            #     recording.archive_url = f"https://{bucket}.s3.amazonaws.com/{archive_key}"
            # elif storage_type == 'azure':
            #     archive_key = f"recordings/{recording.lesson.id}/{recording.zoom_recording_id}.mp4"
            #     upload_to_azure(recording.download_url, archive_key)
            #     recording.archive_url = f"https://{account}.blob.core.windows.net/{container}/{archive_key}"
            
            # Для демонстрации - помечаем как архивированную
            recording.status = 'archived'
            recording.archived_at = timezone.now()
            # recording.archive_key = archive_key
            # recording.archive_url = archive_url
            recording.save()
            
            archived_count += 1
            logger.info(f"[Celery] Запись {recording.id} успешно архивирована")
            
        except Exception as e:
            logger.error(f"[Celery] Ошибка архивирования записи {recording.id}: {e}")
            recording.status = 'failed'
            recording.save()
            failed_count += 1
    
    result = {
        'archived': archived_count,
        'failed': failed_count,
        'timestamp': timezone.now().isoformat()
    }
    
    if archived_count > 0:
        logger.info(f"[Celery] archive_zoom_recordings: архивировано {archived_count}, ошибок {failed_count}")
    
    return result

