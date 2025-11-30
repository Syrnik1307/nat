from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from .models import Subscription


def get_subscription(user) -> Subscription:
    """Возвращает или создает (trial) подписку пользователя."""
    sub = getattr(user, 'subscription', None)
    if sub:
        return sub
    # Создаем пробную подписку на 7 дней
    now = timezone.now()
    sub = Subscription.objects.create(
        user=user,
        plan=Subscription.PLAN_TRIAL,
        status=Subscription.STATUS_ACTIVE,
        expires_at=now + timezone.timedelta(days=7),
        auto_renew=False,
    )
    return sub


def is_subscription_active(user) -> bool:
    sub = get_subscription(user)
    return sub.is_active()


def require_active_subscription(user):
    sub = get_subscription(user)
    if not sub.is_active():
        raise PermissionDenied(detail='Подписка не активна. Оплатите чтобы продолжить.')
    return sub
