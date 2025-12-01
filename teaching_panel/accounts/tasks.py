"""Celery tasks for subscription maintenance and notifications."""
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from .models import Subscription, NotificationLog
from .notifications import send_telegram_notification

REMINDER_DAYS = 3
REMINDER_COOLDOWN_HOURS = 24


@shared_task
def check_expiring_subscriptions():
    """Send Telegram reminders to teachers when their subscription is about to expire."""
    now = timezone.now()
    window_end = now + timedelta(days=REMINDER_DAYS)

    subscriptions = (
        Subscription.objects.select_related('user')
        .filter(
            status=Subscription.STATUS_ACTIVE,
            expires_at__isnull=False,
            expires_at__lte=window_end,
            expires_at__gte=now,
        )
    )

    sent = 0
    for sub in subscriptions:
        user = sub.user
        if not user:
            continue

        # Skip if we already notified the user recently
        recently_notified = NotificationLog.objects.filter(
            user=user,
            notification_type='subscription_expiring',
            created_at__gte=now - timedelta(hours=REMINDER_COOLDOWN_HOURS),
        ).exists()
        if recently_notified:
            continue

        days_left = max((sub.expires_at - now).days, 0)
        message = (
            "⚠️ Подписка Teaching Panel скоро истекает!\n"
            f"Осталось: {days_left} дн., до {sub.expires_at.strftime('%d.%m.%Y')}\n"
            "Продлите подписку, чтобы не потерять доступ к урокам и записям."
        )

        if send_telegram_notification(user, 'subscription_expiring', message):
            sent += 1

    return {
        'checked': subscriptions.count(),
        'sent': sent,
        'timestamp': now.isoformat(),
    }


@shared_task
def process_expired_subscriptions():
    """Mark subscriptions as expired once their expiration date has passed."""
    now = timezone.now()
    expired_qs = Subscription.objects.filter(
        expires_at__lt=now,
        status__in=[Subscription.STATUS_ACTIVE, Subscription.STATUS_PENDING],
    )
    updated = expired_qs.update(status=Subscription.STATUS_EXPIRED, auto_renew=False)

    return {
        'updated': updated,
        'timestamp': now.isoformat(),
    }
