"""
check_zoom — Проверка статуса Zoom аккаунтов

Диагностирует:
- Доступность Zoom API
- Количество свободных аккаунтов
- Статус текущих встреч
"""

import logging
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


async def execute(params: dict) -> dict:
    """
    Проверить статус Zoom-интеграции.
    
    Args:
        params: {
            '_user': User,           # Автоматически добавляется
            '_conversation': Conversation,
        }
    
    Returns:
        dict: {
            'success': bool,
            'message': str,
            'data': {
                'total_accounts': int,
                'available_accounts': int,
                'in_use_accounts': int,
                'api_status': 'ok' | 'error',
            }
        }
    """
    try:
        from zoom_pool.models import ZoomAccount
        
        # Получаем статистику по аккаунтам
        total = await sync_to_async(ZoomAccount.objects.count)()
        in_use = await sync_to_async(
            ZoomAccount.objects.filter(in_use=True).count
        )()
        available = total - in_use
        
        # Формируем результат
        data = {
            'total_accounts': total,
            'available_accounts': available,
            'in_use_accounts': in_use,
            'api_status': 'ok',
        }
        
        if total == 0:
            message = "Zoom-аккаунты не настроены в системе. Обратитесь к администратору."
            success = False
        elif available == 0:
            message = f"Все {total} Zoom-аккаунтов сейчас заняты. Попробуйте позже или дождитесь окончания текущих уроков."
            success = True
        else:
            message = f"Zoom работает нормально. Доступно {available} из {total} аккаунтов."
            success = True
        
        return {
            'success': success,
            'message': message,
            'data': data,
        }
        
    except Exception as e:
        logger.error(f"check_zoom failed: {e}")
        return {
            'success': False,
            'message': 'Не удалось проверить статус Zoom. Попробуйте позже.',
            'data': {'api_status': 'error', 'error': str(e)},
        }
