"""
check_subscription — Проверка статуса подписки пользователя

Диагностирует:
- Активна ли подписка
- Дата окончания
- Лимиты хранилища
"""

import logging
from django.utils import timezone
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


async def execute(params: dict) -> dict:
    """
    Проверить статус подписки пользователя.
    
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
                'status': 'active' | 'expired' | 'none',
                'expires_at': str | None,
                'days_left': int | None,
                'storage_used_gb': float,
                'storage_total_gb': float,
            }
        }
    """
    user = params.get('_user')
    
    if not user:
        return {
            'success': False,
            'message': 'Не удалось определить пользователя',
            'data': {},
        }
    
    try:
        # Проверяем, есть ли подписка
        subscription = await sync_to_async(
            lambda: getattr(user, 'subscription', None)
        )()
        
        if not subscription:
            return {
                'success': True,
                'message': 'У вас нет активной подписки. Оформите подписку на странице /teacher/subscription',
                'data': {
                    'status': 'none',
                    'expires_at': None,
                    'days_left': None,
                },
            }
        
        # Получаем данные подписки
        status = await sync_to_async(lambda: subscription.status)()
        expires_at = await sync_to_async(lambda: subscription.expires_at)()
        
        # Вычисляем дни до окончания
        days_left = None
        if expires_at:
            delta = expires_at - timezone.now()
            days_left = max(0, delta.days)
        
        # Получаем данные о хранилище (если есть)
        storage_used = 0
        storage_total = 0
        try:
            from schedule.models import TeacherStorageQuota
            quota = await sync_to_async(
                TeacherStorageQuota.objects.filter(teacher=user).first
            )()
            if quota:
                storage_used = float(quota.used_gb)
                storage_total = float(quota.total_gb)
        except Exception:
            pass
        
        data = {
            'status': status,
            'expires_at': expires_at.isoformat() if expires_at else None,
            'days_left': days_left,
            'storage_used_gb': round(storage_used, 2),
            'storage_total_gb': round(storage_total, 2),
        }
        
        # Формируем сообщение
        if status == 'active':
            if days_left is not None and days_left <= 7:
                message = f"Ваша подписка активна, но истекает через {days_left} дней. Рекомендуем продлить."
            else:
                message = f"Ваша подписка активна до {expires_at.strftime('%d.%m.%Y') if expires_at else 'бессрочно'}."
            
            if storage_total > 0:
                usage_percent = (storage_used / storage_total) * 100
                message += f" Использовано {storage_used:.1f} из {storage_total:.1f} ГБ хранилища ({usage_percent:.0f}%)."
            
            success = True
        else:
            message = f"Ваша подписка неактивна (статус: {status}). Продлите подписку на странице /teacher/subscription"
            success = True
        
        return {
            'success': success,
            'message': message,
            'data': data,
        }
        
    except Exception as e:
        logger.error(f"check_subscription failed: {e}")
        return {
            'success': False,
            'message': 'Не удалось проверить статус подписки',
            'data': {'error': str(e)},
        }
