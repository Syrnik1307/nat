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


# ============================================================================
# НОВЫЕ ЗАДАЧИ ДЛЯ ОБРАБОТКИ ЗАПИСЕЙ УРОКОВ С GOOGLE DRIVE
# ============================================================================

@shared_task
def process_zoom_recording(recording_id):
    """
    Главная задача: скачать запись с Zoom и загрузить в Google Drive
    
    Args:
        recording_id: ID объекта LessonRecording
    """
    import os
    import requests
    import logging
    from .models import LessonRecording, TeacherStorageQuota
    from .gdrive_utils import get_gdrive_manager
    from django.conf import settings
    
    logger = logging.getLogger(__name__)
    
    try:
        # Получаем объект записи
        recording = LessonRecording.objects.select_related('lesson__group__teacher').get(id=recording_id)
        
        logger.info(f"Processing recording {recording_id} for lesson {recording.lesson.id}")
        
        # Проверяем что урок существует
        if not recording.lesson:
            logger.error(f"Recording {recording_id} has no associated lesson")
            recording.status = 'failed'
            recording.save()
            return
        
        # Получаем преподавателя
        teacher = recording.lesson.group.teacher
        
        # Проверяем квоту хранилища преподавателя
        try:
            quota = teacher.storage_quota
        except TeacherStorageQuota.DoesNotExist:
            # Создаем квоту с базовыми параметрами (5 ГБ)
            quota = TeacherStorageQuota.objects.create(
                teacher=teacher,
                total_quota_bytes=5 * 1024 ** 3  # 5 GB
            )
            logger.info(f"Created storage quota for teacher {teacher.id}")
        
        # Проверяем превышение квоты
        if quota.quota_exceeded:
            logger.warning(f"Teacher {teacher.id} quota exceeded. Skipping recording {recording_id}")
            recording.status = 'failed'
            recording.save()
            
            # Отправляем уведомление преподавателю о превышении квоты
            _notify_teacher_quota_exceeded(teacher, quota)
            return
        
        # 1. Скачиваем файл с Zoom
        temp_file_path = _download_from_zoom(recording)
        
        if not temp_file_path:
            logger.error(f"Failed to download recording {recording_id} from Zoom")
            recording.status = 'failed'
            recording.save()
            return
        
        # Проверяем размер файла перед загрузкой
        file_size = os.path.getsize(temp_file_path)
        recording.file_size = file_size
        recording.save()
        
        # Проверяем доступное место
        if not quota.can_upload(file_size):
            logger.warning(f"Teacher {teacher.id} insufficient space. Need {file_size} bytes, available {quota.available_bytes}")
            recording.status = 'failed'
            recording.save()
            _cleanup_temp_file(temp_file_path)
            _notify_teacher_quota_exceeded(teacher, quota)
            return
        
        # 2. Загружаем в Google Drive
        gdrive_file = _upload_to_gdrive(recording, temp_file_path)
        
        if not gdrive_file:
            logger.error(f"Failed to upload recording {recording_id} to Google Drive")
            recording.status = 'failed'
            recording.save()
            # Удаляем временный файл
            _cleanup_temp_file(temp_file_path)
            return
        
        # 3. Обновляем запись в БД
        recording.gdrive_file_id = gdrive_file['file_id']
        recording.gdrive_folder_id = gdrive_file['folder_id']
        recording.play_url = gdrive_file.get('embed_link', '')
        recording.download_url = gdrive_file.get('download_link', '')
        recording.thumbnail_url = gdrive_file.get('thumbnail_link', '')
        recording.status = 'ready'
        
        # Устанавливаем дату удаления
        days_available = recording.lesson.recording_available_for_days or 90
        recording.available_until = timezone.now() + timedelta(days=days_available)
        
        recording.save()
        
        # 4. Обновляем квоту преподавателя
        quota.add_recording(file_size)
        logger.info(f"Updated quota for teacher {teacher.id}: {quota.used_gb:.2f}/{quota.total_gb:.2f} GB")
        
        # Проверяем порог предупреждения
        if quota.usage_percent >= 80 and quota.warning_sent:
            _notify_teacher_quota_warning(teacher, quota)
        
        logger.info(f"Successfully processed recording {recording_id}")
        
        # 5. Удаляем временный файл
        _cleanup_temp_file(temp_file_path)
        
        # 6. Удаляем запись с Zoom (освобождаем место)
        _delete_from_zoom(recording)
        
        # 7. Отправляем уведомление ученикам (опционально)
        _notify_students_about_recording(recording)
        
    except LessonRecording.DoesNotExist:
        logger.error(f"Recording {recording_id} not found")
    except Exception as e:
        logger.exception(f"Error processing recording {recording_id}: {e}")
        try:
            recording = LessonRecording.objects.get(id=recording_id)
            recording.status = 'failed'
            recording.save()
        except:
            pass


def _download_from_zoom(recording):
    """Скачивает файл записи с Zoom"""
    import os
    import requests
    import logging
    from django.conf import settings
    
    logger = logging.getLogger(__name__)
    
    try:
        download_url = recording.download_url
        
        if not download_url:
            logger.error(f"No download URL for recording {recording.id}")
            return None
        
        # Получаем Zoom access token
        zoom_token = _get_zoom_access_token()
        
        if not zoom_token:
            logger.error("Failed to get Zoom access token")
            return None
        
        # Формируем заголовки для авторизации
        headers = {
            'Authorization': f'Bearer {zoom_token}',
            'User-Agent': 'TeachingPanel/1.0'
        }
        
        # Создаем временную директорию если не существует
        temp_dir = os.path.join(settings.BASE_DIR, 'temp_recordings')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Формируем имя файла
        lesson = recording.lesson
        file_extension = 'mp4'  # По умолчанию
        
        if recording.recording_type == 'audio_only':
            file_extension = 'm4a'
        
        filename = f"lesson_{lesson.id}_{recording.zoom_recording_id}.{file_extension}"
        temp_file_path = os.path.join(temp_dir, filename)
        
        logger.info(f"Downloading recording from Zoom to {temp_file_path}")
        
        # Скачиваем файл с прогресс-баром
        response = requests.get(download_url, headers=headers, stream=True, timeout=300)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(temp_file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # Логируем прогресс каждые 10MB
                    if downloaded % (10 * 1024 * 1024) == 0:
                        progress = (downloaded / total_size * 100) if total_size > 0 else 0
                        logger.info(f"Download progress: {progress:.1f}% ({downloaded}/{total_size} bytes)")
        
        logger.info(f"Successfully downloaded {downloaded} bytes to {temp_file_path}")
        
        return temp_file_path
    
    except requests.RequestException as e:
        logger.exception(f"Error downloading from Zoom: {e}")
        return None
    except Exception as e:
        logger.exception(f"Unexpected error during download: {e}")
        return None


def _upload_to_gdrive(recording, file_path):
    """Загружает файл в Google Drive"""
    import logging
    from .gdrive_utils import get_gdrive_manager
    
    logger = logging.getLogger(__name__)
    
    try:
        gdrive = get_gdrive_manager()
        
        lesson = recording.lesson
        
        # Формируем имя файла для Drive
        file_name = f"{lesson.subject.name} - {lesson.start_time.strftime('%Y-%m-%d %H:%M')}"
        
        if lesson.group:
            file_name = f"{lesson.group.name} - {file_name}"
        
        # Определяем MIME type
        mime_type = 'video/mp4'
        if file_path.endswith('.m4a'):
            mime_type = 'audio/mp4'
        
        logger.info(f"Uploading to Google Drive: {file_name}")
        
        # Загружаем файл
        result = gdrive.upload_file(
            file_path=file_path,
            file_name=file_name,
            mime_type=mime_type
        )
        
        if result:
            logger.info(f"Successfully uploaded to Google Drive: {result['file_id']}")
            
            # Получаем ссылки для воспроизведения
            result['embed_link'] = gdrive.get_embed_link(result['file_id'])
            result['download_link'] = gdrive.get_direct_download_link(result['file_id'])
            
            return result
        else:
            return None
    
    except Exception as e:
        logger.exception(f"Error uploading to Google Drive: {e}")
        return None


def _delete_from_zoom(recording):
    """Удаляет запись с Zoom после успешной загрузки в Drive"""
    import requests
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        zoom_recording_id = recording.zoom_recording_id
        
        if not zoom_recording_id:
            logger.warning(f"No Zoom recording ID for recording {recording.id}")
            return
        
        # Получаем Zoom access token
        zoom_token = _get_zoom_access_token()
        
        if not zoom_token:
            logger.error("Failed to get Zoom access token for deletion")
            return
        
        # DELETE запрос к Zoom API
        url = f"https://api.zoom.us/v2/recordings/{zoom_recording_id}"
        
        headers = {
            'Authorization': f'Bearer {zoom_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.delete(url, headers=headers, timeout=30)
        
        if response.status_code == 204:
            logger.info(f"Successfully deleted recording {zoom_recording_id} from Zoom")
        elif response.status_code == 404:
            logger.info(f"Recording {zoom_recording_id} already deleted from Zoom")
        else:
            logger.warning(f"Failed to delete from Zoom (status {response.status_code}): {response.text}")
    
    except Exception as e:
        logger.exception(f"Error deleting from Zoom: {e}")


def _get_zoom_access_token():
    """Получает Zoom access token для API запросов"""
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # Используем существующую систему zoom_pool
        from zoom_pool.models import ZoomAccount
        
        # Получаем активный аккаунт с токеном
        zoom_account = ZoomAccount.objects.filter(
            is_active=True,
            access_token__isnull=False
        ).first()
        
        if zoom_account:
            # Проверяем что токен не истек
            if zoom_account.token_expires_at and zoom_account.token_expires_at > timezone.now():
                return zoom_account.access_token
            else:
                # Токен истек — обновляем
                zoom_account.refresh_access_token()
                return zoom_account.access_token
        
        logger.error("No active Zoom account found")
        return None
    
    except Exception as e:
        logger.exception(f"Error getting Zoom access token: {e}")
        return None


def _cleanup_temp_file(file_path):
    """Удаляет временный файл"""
    import os
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Deleted temporary file: {file_path}")
    except Exception as e:
        logger.warning(f"Failed to delete temp file {file_path}: {e}")


def _notify_students_about_recording(recording):
    """Отправляет уведомления ученикам о доступности записи урока"""
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        lesson = recording.lesson
        
        # Получаем учеников группы
        if not lesson.group:
            logger.info(f"Lesson {lesson.id} has no group, skipping notifications")
            return
        
        students = lesson.group.students.filter(is_active=True)
        
        logger.info(f"Notifying {students.count()} students about recording for lesson {lesson.id}")
        
        # TODO: Интегрировать с системой уведомлений
        # Можно использовать email, Telegram, push-уведомления и т.д.
        
        logger.info(f"Would send {students.count()} notifications for recording {recording.id}")
    
    except Exception as e:
        logger.exception(f"Error notifying students: {e}")


@shared_task
def cleanup_old_recordings():
    """
    Периодическая задача: удаляет старые записи из Google Drive
    Запускается по расписанию (например, раз в день)
    """
    import logging
    from .models import LessonRecording, TeacherStorageQuota
    from .gdrive_utils import get_gdrive_manager
    
    logger = logging.getLogger(__name__)
    
    try:
        # Находим записи с истекшим сроком
        expired_recordings = LessonRecording.objects.select_related(
            'lesson__group__teacher'
        ).filter(
            status='ready',
            available_until__lte=timezone.now()
        )
        
        count = expired_recordings.count()
        
        if count == 0:
            logger.info("No expired recordings to clean up")
            return {'deleted': 0, 'timestamp': timezone.now().isoformat()}
        
        logger.info(f"Cleaning up {count} expired recordings")
        
        gdrive = get_gdrive_manager()
        deleted_count = 0
        
        for recording in expired_recordings:
            try:
                # Удаляем из Google Drive
                if recording.gdrive_file_id:
                    gdrive.delete_file(recording.gdrive_file_id)
                    logger.info(f"Deleted file {recording.gdrive_file_id} from Google Drive")
                
                # Обновляем квоту преподавателя
                teacher = recording.lesson.group.teacher
                try:
                    quota = teacher.storage_quota
                    quota.remove_recording(recording.file_size or 0)
                    logger.info(f"Updated quota for teacher {teacher.id}: {quota.used_gb:.2f}/{quota.total_gb:.2f} GB")
                except TeacherStorageQuota.DoesNotExist:
                    logger.warning(f"No quota found for teacher {teacher.id}")
                
                # Обновляем статус в БД
                recording.status = 'deleted'
                recording.save()
                
                deleted_count += 1
            
            except Exception as e:
                logger.warning(f"Failed to delete recording {recording.id}: {e}")
        
        logger.info(f"Successfully cleaned up {deleted_count}/{count} recordings")
        
        return {
            'deleted': deleted_count,
            'failed': count - deleted_count,
            'timestamp': timezone.now().isoformat()
        }
    
    except Exception as e:
        logger.exception(f"Error during cleanup: {e}")
        return {'error': str(e), 'timestamp': timezone.now().isoformat()}


def _notify_teacher_quota_exceeded(teacher, quota):
    """Уведомление преподавателя о превышении квоты"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.warning(f"Teacher {teacher.id} ({teacher.email}) quota exceeded: {quota.used_gb:.2f}/{quota.total_gb:.2f} GB")
    
    # TODO: Отправить email/уведомление преподавателю
    # Пример:
    # send_email(
    #     to=teacher.email,
    #     subject='Превышен лимит хранилища',
    #     template='quota_exceeded',
    #     context={'teacher': teacher, 'quota': quota}
    # )


def _notify_teacher_quota_warning(teacher, quota):
    """Предупреждение преподавателя о приближении к лимиту (80%)"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"Teacher {teacher.id} ({teacher.email}) quota warning: {quota.used_gb:.2f}/{quota.total_gb:.2f} GB ({quota.usage_percent:.1f}%)")
    
    # TODO: Отправить email/уведомление преподавателю
    # Пример:
    # send_email(
    #     to=teacher.email,
    #     subject='Внимание: заканчивается место для записей',
    #     template='quota_warning',
    #     context={'teacher': teacher, 'quota': quota}
    # )
