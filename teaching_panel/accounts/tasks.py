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


STORAGE_WARNING_THRESHOLD_PERCENT = 90
STORAGE_LIMIT_COOLDOWN_HOURS = 24


@shared_task
def sync_teacher_storage_usage():
    """
    Периодически пересчитывает использование хранилища для всех учителей.
    
    Запускается 4 раза в день (каждые 6 часов).
    При превышении лимита отправляет уведомление учителю.
    """
    import logging
    from decimal import Decimal
    from django.conf import settings
    from django.contrib.auth import get_user_model
    
    logger = logging.getLogger(__name__)
    now = timezone.now()
    
    # Проверяем что Google Drive включен
    if not getattr(settings, 'USE_GDRIVE_STORAGE', False):
        logger.info("[Celery] sync_teacher_storage_usage: Google Drive storage disabled")
        return {'status': 'disabled', 'reason': 'USE_GDRIVE_STORAGE=False'}
    
    User = get_user_model()
    teachers = User.objects.filter(role='teacher', is_active=True)
    
    updated = 0
    warnings_sent = 0
    errors = 0
    
    for teacher in teachers:
        try:
            subscription = getattr(teacher, 'subscription', None)
            if not subscription:
                continue
            
            # Пропускаем если нет папки на Google Drive
            if not subscription.gdrive_folder_id:
                continue
            
            # Получаем реальный размер с Google Drive
            from .gdrive_folder_service import get_teacher_storage_usage
            storage_stats = get_teacher_storage_usage(subscription)
            
            if 'error' in storage_stats:
                logger.warning(f"Failed to get storage for teacher {teacher.id}: {storage_stats.get('error')}")
                errors += 1
                continue
            
            # used_storage_gb уже обновлён внутри get_teacher_storage_usage
            updated += 1
            
            # Проверяем лимит и отправляем уведомление
            usage_percent = storage_stats.get('usage_percent', 0)
            
            if usage_percent >= 100:
                # Лимит исчерпан — уведомляем
                _notify_storage_limit_exceeded(teacher, subscription, storage_stats)
                warnings_sent += 1
            elif usage_percent >= STORAGE_WARNING_THRESHOLD_PERCENT:
                # Приближается к лимиту — предупреждаем
                _notify_storage_warning(teacher, subscription, storage_stats)
                warnings_sent += 1
                
        except Exception as e:
            logger.exception(f"Error syncing storage for teacher {teacher.id}: {e}")
            errors += 1
    
    logger.info(f"[Celery] sync_teacher_storage_usage: updated={updated}, warnings={warnings_sent}, errors={errors}")
    
    return {
        'updated': updated,
        'warnings_sent': warnings_sent,
        'errors': errors,
        'timestamp': now.isoformat(),
    }


def _notify_storage_limit_exceeded(teacher, subscription, stats):
    """Отправляет уведомление о превышении лимита хранилища."""
    now = timezone.now()
    
    # Проверяем cooldown (не спамим)
    recently_notified = NotificationLog.objects.filter(
        user=teacher,
        notification_type='storage_limit_exceeded',
        created_at__gte=now - timedelta(hours=STORAGE_LIMIT_COOLDOWN_HOURS),
    ).exists()
    
    if recently_notified:
        return False
    
    used_gb = stats.get('used_gb', 0)
    limit_gb = stats.get('limit_gb', 10)
    
    message = (
        "🚨 Хранилище заполнено!\n\n"
        f"Использовано: {used_gb:.2f} ГБ из {limit_gb} ГБ (100%)\n\n"
        "Новые записи уроков не будут сохраняться.\n"
        "Удалите старые записи или докупите место в настройках подписки."
    )
    
    send_telegram_notification(teacher, 'storage_limit_exceeded', message)
    return True


def _notify_storage_warning(teacher, subscription, stats):
    """Отправляет предупреждение о приближении к лимиту (90%+)."""
    now = timezone.now()
    
    # Проверяем cooldown
    recently_notified = NotificationLog.objects.filter(
        user=teacher,
        notification_type='storage_warning',
        created_at__gte=now - timedelta(hours=STORAGE_LIMIT_COOLDOWN_HOURS * 2),  # 48 часов для предупреждений
    ).exists()
    
    if recently_notified:
        return False
    
    used_gb = stats.get('used_gb', 0)
    limit_gb = stats.get('limit_gb', 10)
    available_gb = stats.get('available_gb', 0)
    usage_percent = stats.get('usage_percent', 0)
    
    message = (
        "⚠️ Хранилище почти заполнено!\n\n"
        f"Использовано: {used_gb:.2f} ГБ из {limit_gb} ГБ ({usage_percent:.0f}%)\n"
        f"Осталось: {available_gb:.2f} ГБ\n\n"
        "Рекомендуем удалить старые записи или докупить место."
    )
    
    send_telegram_notification(teacher, 'storage_warning', message)
    return True


ABSENCE_ALERT_THRESHOLD = 3  # Минимальное количество пропусков подряд для алерта
ABSENCE_ALERT_COOLDOWN_HOURS = 48  # Интервал между повторными уведомлениями


@shared_task
def check_consecutive_absences():
    """
    Проверяет учеников с 3+ пропусками подряд и отправляет уведомления учителям.
    
    Запускается ежедневно в 10:00.
    """
    import logging
    from django.contrib.auth import get_user_model
    from schedule.models import Group
    from .attendance_service import RatingService
    
    logger = logging.getLogger(__name__)
    now = timezone.now()
    
    User = get_user_model()
    teachers = User.objects.filter(role='teacher', is_active=True)
    
    total_alerts = 0
    sent_notifications = 0
    
    for teacher in teachers:
        groups = Group.objects.filter(teacher=teacher)
        
        teacher_alerts = []
        for group in groups:
            try:
                alerts = RatingService.get_students_with_consecutive_absences(
                    group_id=group.id,
                    min_absences=ABSENCE_ALERT_THRESHOLD
                )
                for alert in alerts:
                    alert['group_name'] = group.name
                    teacher_alerts.append(alert)
            except Exception as e:
                logger.error(f"Error checking absences for group {group.id}: {e}")
                continue
        
        if not teacher_alerts:
            continue
        
        total_alerts += len(teacher_alerts)
        
        # Проверяем cooldown для этого учителя
        recently_notified = NotificationLog.objects.filter(
            user=teacher,
            notification_type='absence_alert',
            created_at__gte=now - timedelta(hours=ABSENCE_ALERT_COOLDOWN_HOURS),
        ).exists()
        
        if recently_notified:
            logger.info(f"Skipping absence alert for teacher {teacher.id} - recently notified")
            continue
        
        # Формируем сообщение
        critical = [a for a in teacher_alerts if a['severity'] == 'critical']
        warning = [a for a in teacher_alerts if a['severity'] == 'warning']
        
        message_parts = ["🔔 Внимание! Ученики пропускают занятия\n"]
        
        if critical:
            message_parts.append(f"🚨 Критично ({len(critical)}):")
            for a in critical[:5]:  # Максимум 5 критичных
                message_parts.append(
                    f"  • {a['student_name']} ({a['group_name']}) — {a['consecutive_absences']} пропусков подряд"
                )
            if len(critical) > 5:
                message_parts.append(f"  ... и ещё {len(critical) - 5}")
        
        if warning:
            message_parts.append(f"\n⚠️ Предупреждение ({len(warning)}):")
            for a in warning[:5]:  # Максимум 5 предупреждений
                message_parts.append(
                    f"  • {a['student_name']} ({a['group_name']}) — {a['consecutive_absences']} пропусков"
                )
            if len(warning) > 5:
                message_parts.append(f"  ... и ещё {len(warning) - 5}")
        
        message_parts.append("\nОткройте раздел Аналитика для подробностей.")
        
        message = "\n".join(message_parts)
        
        if send_telegram_notification(teacher, 'absence_alert', message):
            sent_notifications += 1
            logger.info(f"Sent absence alert to teacher {teacher.id} with {len(teacher_alerts)} alerts")
    
    return {
        'total_alerts': total_alerts,
        'sent_notifications': sent_notifications,
        'timestamp': now.isoformat(),
    }


@shared_task
def notify_recording_available(recording_id):
    """
    Отправляет уведомление ученикам о доступности записи урока.
    
    Вызывается после обработки записи (process_zoom_recording).
    """
    import logging
    from schedule.models import LessonRecording
    
    logger = logging.getLogger(__name__)
    
    try:
        recording = LessonRecording.objects.select_related(
            'lesson', 'lesson__group'
        ).get(id=recording_id)
    except LessonRecording.DoesNotExist:
        logger.warning(f"Recording {recording_id} not found")
        return {'status': 'error', 'message': 'Recording not found'}
    
    lesson = recording.lesson
    if not lesson or not lesson.group:
        return {'status': 'skipped', 'reason': 'no-group'}
    
    students = lesson.group.students.filter(is_active=True)
    if not students.exists():
        return {'status': 'skipped', 'reason': 'no-students'}
    
    lesson_title = lesson.title or "Занятие"
    lesson_date = lesson.start_time.strftime('%d.%m.%Y') if lesson.start_time else ""
    group_name = lesson.group.name
    
    message = (
        "📹 Запись урока доступна!\n\n"
        f"Урок: {lesson_title}\n"
        f"Группа: {group_name}\n"
        f"Дата: {lesson_date}\n\n"
        "Зайдите в раздел Записи, чтобы посмотреть."
    )
    
    sent = 0
    for student in students:
        if send_telegram_notification(student, 'recording_available', message):
            sent += 1
    
    logger.info(f"Sent recording notification to {sent}/{students.count()} students for lesson {lesson.id}")
    
    return {
        'status': 'success',
        'recording_id': recording_id,
        'sent': sent,
        'total_students': students.count(),
    }
