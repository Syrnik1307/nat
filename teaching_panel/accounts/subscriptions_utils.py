import logging
from datetime import datetime

from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from .models import Subscription

logger = logging.getLogger(__name__)


def _is_february_2026_promo() -> bool:
    """Проверяет, действует ли февральская акция 2026 года.
    
    Акция: все регистрации в феврале 2026 получают бесплатную подписку до 1 марта 2026.
    Защитное условие: акция НЕ действует с марта 2026 и далее.
    """
    now = timezone.now()
    return now.year == 2026 and now.month == 2


def _get_february_2026_promo_expires_at():
    """Возвращает дату окончания февральской акции: 1 марта 2026, 00:00:00 UTC."""
    return timezone.make_aware(datetime(2026, 3, 1, 0, 0, 0))


def _ensure_subscription_instance(user) -> Subscription:
    """Безопасно получает подписку, создавая подписку в статусе 'pending' если её не было.
    
    Новые учителя НЕ получают автоматический триал — им нужно оплатить подписку,
    чтобы использовать Zoom и другие платные функции.
    
    ИСКЛЮЧЕНИЕ: Февраль 2026 — промо-акция для первых пользователей.
    Все регистрации в феврале 2026 получают бесплатную активную подписку до 1 марта 2026.
    """
    try:
        return user.subscription  # OneToOneField дескриптор
    except Subscription.DoesNotExist:
        now = timezone.now()
        
        # ===== ФЕВРАЛЬСКАЯ АКЦИЯ 2026 =====
        # Первые пользователи получают бесплатный доступ до 1 марта 2026
        if _is_february_2026_promo():
            promo_expires = _get_february_2026_promo_expires_at()
            promo_sub = Subscription.objects.create(
                user=user,
                plan=Subscription.PLAN_MONTHLY,
                status=Subscription.STATUS_ACTIVE,  # Сразу активная!
                expires_at=promo_expires,  # До 1 марта 2026
                auto_renew=False,
            )
            logger.info("FEBRUARY 2026 PROMO: Free subscription granted until March 1", extra={
                'user_id': user.id,
                'email': getattr(user, 'email', None),
                'expires_at': promo_expires.isoformat()
            })
            return promo_sub
        # ===== КОНЕЦ ФЕВРАЛЬСКОЙ АКЦИИ =====
        
        # Стандартная логика: создаём подписку со статусом PENDING (ожидает оплаты)
        # Учитель не сможет использовать Zoom пока не оплатит
        pending_sub = Subscription.objects.create(
            user=user,
            plan=Subscription.PLAN_MONTHLY,  # По умолчанию месячный план
            status=Subscription.STATUS_PENDING,  # НЕ активная — нужна оплата
            expires_at=now,  # Уже истекла — функции заблокированы
            auto_renew=False,
        )
        logger.info("Pending subscription created (payment required)", extra={
            'user_id': user.id,
            'email': getattr(user, 'email', None)
        })
        return pending_sub


def get_subscription(user) -> Subscription:
    sub = _ensure_subscription_instance(user)
    now = timezone.now()
    if sub.expires_at:
        if sub.status == Subscription.STATUS_PENDING and sub.expires_at > now:
            sub.status = Subscription.STATUS_ACTIVE
            sub.save(update_fields=['status', 'updated_at'])
        elif sub.status == Subscription.STATUS_ACTIVE and sub.expires_at <= now:
            sub.status = Subscription.STATUS_EXPIRED
            sub.save(update_fields=['status', 'updated_at'])
    return sub


def is_subscription_active(user) -> bool:
    return get_subscription(user).is_active()


def require_active_subscription(user):
    """Проверяет что у пользователя есть активная оплаченная подписка.
    
    Вызывает PermissionDenied если подписка не активна или не оплачена.
    """
    sub = get_subscription(user)
    if not sub.is_active():
        logger.warning(
            "Subscription blocked access user=%s status=%s expires=%s now=%s",
            getattr(user, 'email', user.id),
            sub.status,
            sub.expires_at,
            timezone.now()
        )
        # Разные сообщения в зависимости от статуса подписки
        if sub.status == Subscription.STATUS_PENDING:
            raise PermissionDenied(detail='Для запуска занятий необходимо оплатить подписку.')
        elif sub.status == Subscription.STATUS_EXPIRED:
            raise PermissionDenied(detail='Подписка истекла. Продлите подписку чтобы продолжить.')
        elif sub.status == Subscription.STATUS_CANCELLED:
            raise PermissionDenied(detail='Подписка отменена. Оформите новую подписку чтобы продолжить.')
        else:
            raise PermissionDenied(detail='Подписка не активна. Оплатите чтобы продолжить.')
    return sub
