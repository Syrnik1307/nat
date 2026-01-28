"""
Проверка прав доступа для команд бота
"""
import logging
from functools import wraps
from typing import Optional, Callable, Set
from telegram import Update
from telegram.ext import ContextTypes
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


async def get_user_by_telegram_id(telegram_id: str) -> Optional[User]:
    """Получает пользователя по Telegram ID"""
    try:
        return await sync_to_async(User.objects.get)(telegram_id=telegram_id)
    except User.DoesNotExist:
        return None


def require_linked_account(func: Callable):
    """Декоратор: требует привязанный аккаунт"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        telegram_id = str(update.effective_user.id)
        user = await get_user_by_telegram_id(telegram_id)
        
        if not user:
            await update.effective_message.reply_text(
                "❌ Ваш Telegram не привязан к аккаунту.\n\n"
                "Откройте Teaching Panel → Профиль → Безопасность → Привязать Telegram"
            )
            return
        
        # Добавляем пользователя в контекст
        context.user_data['db_user'] = user
        return await func(update, context, *args, **kwargs)
    
    return wrapper


def require_role(*allowed_roles: str):
    """Декоратор: требует определённую роль"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            telegram_id = str(update.effective_user.id)
            user = context.user_data.get('db_user') or await get_user_by_telegram_id(telegram_id)
            
            if not user:
                await update.effective_message.reply_text(
                    "❌ Ваш Telegram не привязан к аккаунту."
                )
                return
            
            if user.role not in allowed_roles:
                role_names = {
                    'teacher': 'преподавателей',
                    'student': 'учеников',
                    'admin': 'администраторов',
                }
                allowed_names = ', '.join(role_names.get(r, r) for r in allowed_roles)
                await update.effective_message.reply_text(
                    f"❌ Эта команда доступна только для {allowed_names}."
                )
                return
            
            context.user_data['db_user'] = user
            return await func(update, context, *args, **kwargs)
        
        return wrapper
    return decorator


def require_teacher(func: Callable):
    """Декоратор: только для учителей"""
    return require_role('teacher', 'admin')(func)


def require_student(func: Callable):
    """Декоратор: только для учеников"""
    return require_role('student')(func)


def require_notification_consent(func: Callable):
    """Декоратор: проверяет согласие на уведомления"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = context.user_data.get('db_user')
        
        if user and not user.notification_consent:
            await update.effective_message.reply_text(
                "⚠️ Вы не дали согласие на получение уведомлений.\n\n"
                "Чтобы получать напоминания об уроках и ДЗ, "
                "включите уведомления в настройках профиля Teaching Panel."
            )
            return
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper


async def check_broadcast_permission(user: User) -> tuple[bool, str]:
    """
    Проверяет, может ли пользователь делать рассылку.
    Возвращает (can_broadcast, reason).
    """
    from django.utils import timezone
    from ..models import BroadcastRateLimit
    from ..config import BROADCAST_LIMITS
    
    now = timezone.now()
    hour_key = now.strftime('%Y-%m-%d-%H')
    day_key = now.strftime('%Y-%m-%d')
    
    def check_limits():
        # Получаем или создаём запись лимитов
        rate_limit, created = BroadcastRateLimit.objects.get_or_create(
            teacher=user,
            hour_key=hour_key,
            defaults={'day_key': day_key}
        )
        
        # Обновляем day_key если новый день
        if rate_limit.day_key != day_key:
            rate_limit.day_key = day_key
            rate_limit.daily_count = 0
            rate_limit.save(update_fields=['day_key', 'daily_count'])
        
        # Проверяем cooldown
        if rate_limit.last_broadcast_at:
            elapsed = (now - rate_limit.last_broadcast_at).total_seconds()
            if elapsed < BROADCAST_LIMITS['cooldown_seconds']:
                remaining = int(BROADCAST_LIMITS['cooldown_seconds'] - elapsed)
                return False, f"Подождите {remaining} сек. перед следующей рассылкой"
        
        # Проверяем часовой лимит
        if rate_limit.hourly_count >= BROADCAST_LIMITS['per_hour']:
            return False, f"Достигнут лимит: {BROADCAST_LIMITS['per_hour']} рассылок в час"
        
        # Проверяем дневной лимит
        # Суммируем все записи за сегодня
        daily_total = BroadcastRateLimit.objects.filter(
            teacher=user,
            day_key=day_key
        ).values_list('hourly_count', flat=True)
        
        total_today = sum(daily_total)
        if total_today >= BROADCAST_LIMITS['per_day']:
            return False, f"Достигнут лимит: {BROADCAST_LIMITS['per_day']} рассылок в день"
        
        return True, ""
    
    return await sync_to_async(check_limits)()


async def record_broadcast(user: User, recipients_count: int) -> None:
    """Записывает факт рассылки для учёта лимитов"""
    from django.utils import timezone
    from ..models import BroadcastRateLimit
    
    now = timezone.now()
    hour_key = now.strftime('%Y-%m-%d-%H')
    day_key = now.strftime('%Y-%m-%d')
    
    def update_limits():
        rate_limit, _ = BroadcastRateLimit.objects.get_or_create(
            teacher=user,
            hour_key=hour_key,
            defaults={'day_key': day_key}
        )
        rate_limit.hourly_count += 1
        rate_limit.daily_count += 1
        rate_limit.last_broadcast_at = now
        rate_limit.save(update_fields=['hourly_count', 'daily_count', 'last_broadcast_at'])
    
    await sync_to_async(update_limits)()
