"""
check_system_status — Проверка статуса системы

Диагностирует:
- Общий статус платформы
- Текущие инциденты
- Плановые работы
"""

import logging
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


async def execute(params: dict) -> dict:
    """
    Проверить текущий статус системы.
    
    Args:
        params: {
            '_user': User,
            '_conversation': Conversation,
        }
    
    Returns:
        dict: {
            'success': bool,
            'message': str,
            'data': {
                'status': 'operational' | 'degraded' | 'major_outage' | 'maintenance',
                'incident_title': str | None,
                'incident_started_at': str | None,
                'status_message': str,
            }
        }
    """
    try:
        from support.models import SystemStatus
        
        # Получаем текущий статус (singleton)
        status_obj = await sync_to_async(SystemStatus.get_current)()
        
        data = {
            'status': status_obj.status,
            'incident_title': status_obj.incident_title or None,
            'incident_started_at': (
                status_obj.incident_started_at.isoformat() 
                if status_obj.incident_started_at else None
            ),
            'status_message': status_obj.message,
        }
        
        # Формируем сообщение
        status_messages = {
            'operational': 'Все системы работают нормально.',
            'degraded': 'Наблюдаются частичные проблемы с некоторыми функциями.',
            'major_outage': 'Серьёзный сбой в работе системы. Мы работаем над решением.',
            'maintenance': 'Проводятся плановые технические работы.',
        }
        
        message = status_messages.get(status_obj.status, 'Статус неизвестен')
        
        if status_obj.incident_title:
            message += f"\n\nИнцидент: {status_obj.incident_title}"
        
        if status_obj.message:
            message += f"\n\n{status_obj.message}"
        
        return {
            'success': True,
            'message': message,
            'data': data,
        }
        
    except Exception as e:
        logger.error(f"check_system_status failed: {e}")
        return {
            'success': False,
            'message': 'Не удалось проверить статус системы',
            'data': {'error': str(e)},
        }
