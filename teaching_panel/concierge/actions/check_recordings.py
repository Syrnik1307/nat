"""
check_recordings — Проверка доступности записей уроков

Диагностирует:
- Количество записей пользователя
- Статус обработки записей
- Ошибки в записях
"""

import logging
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


async def execute(params: dict) -> dict:
    """
    Проверить статус записей уроков пользователя.
    
    Args:
        params: {
            '_user': User,
            '_conversation': Conversation,
            'lesson_id': int (опционально) — конкретный урок
        }
    
    Returns:
        dict: {
            'success': bool,
            'message': str,
            'data': {
                'total_recordings': int,
                'ready_recordings': int,
                'processing_recordings': int,
                'error_recordings': int,
                'recent_errors': list,
            }
        }
    """
    user = params.get('_user')
    lesson_id = params.get('lesson_id')
    
    if not user:
        return {
            'success': False,
            'message': 'Не удалось определить пользователя',
            'data': {},
        }
    
    try:
        from schedule.models import LessonRecording, Lesson
        
        # Базовый queryset — записи уроков пользователя
        if user.role == 'teacher':
            # Учитель видит записи своих уроков
            lessons = Lesson.objects.filter(teacher=user)
            recordings_qs = LessonRecording.objects.filter(lesson__in=lessons)
        else:
            # Студент видит записи уроков своих групп
            groups = await sync_to_async(lambda: list(user.student_groups.all()))()
            lessons = Lesson.objects.filter(group__in=groups)
            recordings_qs = LessonRecording.objects.filter(lesson__in=lessons)
        
        # Если указан конкретный урок
        if lesson_id:
            recordings_qs = recordings_qs.filter(lesson_id=lesson_id)
        
        # Считаем статистику
        total = await sync_to_async(recordings_qs.count)()
        ready = await sync_to_async(
            recordings_qs.filter(status='ready').count
        )()
        processing = await sync_to_async(
            recordings_qs.filter(status__in=['pending', 'processing', 'downloading']).count
        )()
        errors = await sync_to_async(
            recordings_qs.filter(status='error').count
        )()
        
        # Получаем последние ошибки
        recent_errors = []
        if errors > 0:
            error_recs = await sync_to_async(list)(
                recordings_qs.filter(status='error')
                .select_related('lesson')
                .order_by('-created_at')[:3]
            )
            for rec in error_recs:
                recent_errors.append({
                    'recording_id': rec.id,
                    'lesson_id': rec.lesson_id,
                    'lesson_title': rec.lesson.title if rec.lesson else 'Без названия',
                    'error': rec.error_message or 'Неизвестная ошибка',
                })
        
        data = {
            'total_recordings': total,
            'ready_recordings': ready,
            'processing_recordings': processing,
            'error_recordings': errors,
            'recent_errors': recent_errors,
        }
        
        # Формируем сообщение
        if total == 0:
            if lesson_id:
                message = f"Для урока #{lesson_id} нет записей."
            else:
                message = "У вас пока нет записей уроков."
            success = True
        elif errors > 0:
            message = f"Найдено {errors} записей с ошибками из {total}. "
            if recent_errors:
                message += f"Последняя ошибка: {recent_errors[0]['error'][:100]}"
            success = True
        elif processing > 0:
            message = f"{processing} записей сейчас обрабатываются. Обычно это занимает 5-15 минут."
            success = True
        else:
            message = f"Все {ready} записей доступны для просмотра."
            success = True
        
        return {
            'success': success,
            'message': message,
            'data': data,
        }
        
    except Exception as e:
        logger.error(f"check_recordings failed: {e}")
        return {
            'success': False,
            'message': 'Не удалось проверить записи уроков',
            'data': {'error': str(e)},
        }
