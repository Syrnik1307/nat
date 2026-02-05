"""
check_lesson — Проверка статуса урока

Диагностирует:
- Существует ли урок
- Статус урока (запланирован, идёт, завершён)
- Проблемы с Zoom-ссылкой
"""

import logging
from django.utils import timezone
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


async def execute(params: dict) -> dict:
    """
    Проверить статус конкретного урока.
    
    Args:
        params: {
            '_user': User,
            '_conversation': Conversation,
            'lesson_id': int — ID урока
        }
    
    Returns:
        dict: {
            'success': bool,
            'message': str,
            'data': {
                'lesson_id': int,
                'title': str,
                'status': str,
                'scheduled_at': str,
                'has_zoom_link': bool,
                'zoom_status': str,
            }
        }
    """
    user = params.get('_user')
    lesson_id = params.get('lesson_id')
    
    if not lesson_id:
        return {
            'success': False,
            'message': 'Укажите ID урока для проверки',
            'data': {},
        }
    
    try:
        from schedule.models import Lesson
        
        # Получаем урок
        try:
            lesson = await sync_to_async(
                Lesson.objects.select_related('teacher', 'group', 'zoom_account').get
            )(id=lesson_id)
        except Lesson.DoesNotExist:
            return {
                'success': False,
                'message': f'Урок #{lesson_id} не найден',
                'data': {'lesson_id': lesson_id},
            }
        
        # Проверяем доступ
        has_access = False
        if user.role == 'teacher' and lesson.teacher_id == user.id:
            has_access = True
        elif user.role == 'admin':
            has_access = True
        elif user.role == 'student':
            groups = await sync_to_async(lambda: list(user.student_groups.all()))()
            if lesson.group in groups:
                has_access = True
        
        if not has_access:
            return {
                'success': False,
                'message': 'У вас нет доступа к этому уроку',
                'data': {'lesson_id': lesson_id},
            }
        
        # Определяем статус
        now = timezone.now()
        scheduled = lesson.scheduled_start
        
        if lesson.status == 'completed':
            status = 'completed'
            status_text = 'Урок завершён'
        elif lesson.status == 'in_progress':
            status = 'in_progress'
            status_text = 'Урок идёт прямо сейчас'
        elif scheduled and scheduled > now:
            status = 'scheduled'
            delta = scheduled - now
            hours = delta.seconds // 3600
            minutes = (delta.seconds % 3600) // 60
            if delta.days > 0:
                status_text = f'Урок запланирован через {delta.days} дней'
            elif hours > 0:
                status_text = f'Урок начнётся через {hours} ч {minutes} мин'
            else:
                status_text = f'Урок начнётся через {minutes} мин'
        else:
            status = 'unknown'
            status_text = 'Статус урока неизвестен'
        
        # Проверяем Zoom
        has_zoom = bool(lesson.zoom_join_url)
        zoom_status = 'ok' if has_zoom else 'no_link'
        
        if lesson.zoom_account:
            if lesson.zoom_account.in_use and lesson.status != 'in_progress':
                zoom_status = 'account_busy'
        
        data = {
            'lesson_id': lesson.id,
            'title': lesson.title or 'Без названия',
            'status': status,
            'scheduled_at': scheduled.isoformat() if scheduled else None,
            'has_zoom_link': has_zoom,
            'zoom_status': zoom_status,
            'teacher': lesson.teacher.get_full_name() if lesson.teacher else None,
            'group': lesson.group.name if lesson.group else None,
        }
        
        # Формируем сообщение
        message = f"Урок #{lesson_id}: {lesson.title or 'Без названия'}\n"
        message += f"Статус: {status_text}\n"
        
        if not has_zoom and status == 'scheduled':
            message += "\nZoom-ссылка ещё не создана. Она появится при запуске урока."
        elif zoom_status == 'account_busy':
            message += "\nЗакреплённый Zoom-аккаунт сейчас занят другим уроком."
        elif has_zoom:
            message += "\nZoom-ссылка готова."
        
        return {
            'success': True,
            'message': message,
            'data': data,
        }
        
    except Exception as e:
        logger.error(f"check_lesson failed: {e}")
        return {
            'success': False,
            'message': 'Не удалось проверить статус урока',
            'data': {'error': str(e)},
        }
