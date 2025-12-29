import logging

from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from .models import Subscription

logger = logging.getLogger(__name__)


def _ensure_subscription_instance(user) -> Subscription:
    """Безопасно получает подписку, создавая подписку в статусе 'pending' если её не было.
    
    Новые учителя НЕ получают автоматический триал — им нужно оплатить подписку,
    чтобы использовать Zoom и другие платные функции.
    """
    try:
        return user.subscription  # OneToOneField дескриптор
    except Subscription.DoesNotExist:
        now = timezone.now()
        # Создаём подписку со статусом PENDING (ожидает оплаты)
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
    return _ensure_subscription_instance(user)


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
