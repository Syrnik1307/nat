import logging

from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from .models import Subscription

logger = logging.getLogger(__name__)


def _ensure_subscription_instance(user) -> Subscription:
    """Безопасно получает подписку, создавая триальный план если её не было."""
    try:
        return user.subscription  # OneToOneField дескриптор
    except Subscription.DoesNotExist:
        now = timezone.now()
        trial = Subscription.objects.create(
            user=user,
            plan=Subscription.PLAN_TRIAL,
            status=Subscription.STATUS_ACTIVE,
            expires_at=now + timezone.timedelta(days=7),
            auto_renew=False,
        )
        logger.info("Trial subscription provisioned", extra={
            'user_id': user.id,
            'email': getattr(user, 'email', None)
        })
        return trial


def get_subscription(user) -> Subscription:
    return _ensure_subscription_instance(user)


def is_subscription_active(user) -> bool:
    return get_subscription(user).is_active()


def require_active_subscription(user):
    sub = get_subscription(user)
    if not sub.is_active():
        logger.warning(
            "Subscription blocked access user=%s status=%s expires=%s now=%s",
            getattr(user, 'email', user.id),
            sub.status,
            sub.expires_at,
            timezone.now()
        )
        raise PermissionDenied(detail='Подписка не активна. Оплатите чтобы продолжить.')
    return sub
