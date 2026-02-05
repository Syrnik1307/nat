"""Celery tasks for subscription maintenance and notifications."""
from datetime import timedelta
import logging

from celery import shared_task
from django.utils import timezone

from .models import Subscription, NotificationLog, NotificationSettings
from .notifications import send_telegram_notification

logger = logging.getLogger(__name__)

REMINDER_DAYS = 3
REMINDER_COOLDOWN_HOURS = 24


@shared_task(name='accounts.tasks.send_verification_email_task', bind=True, max_retries=3)
def send_verification_email_task(self, email: str, code: str, token: str):
    """
    Celery task для отправки email верификации.
    
    Args:
        email: Email адрес получателя
        code: 6-значный код верификации
        token: UUID токен для ссылки верификации
    """
    from .email_service import email_service
    
    try:
        logger.info(f'[Celery] Sending verification email to {email}')
        
        # Отправляем синхронно (внутри Celery worker это нормально)
        result = email_service.send_verification_email(
            email=email,
            code=code,
            token=token,
            async_send=False  # Синхронно, т.к. мы уже в фоновой задаче
        )
        
        if result['success']:
            logger.info(f'[Celery] Verification email sent successfully to {email}')
        else:
            logger.warning(f'[Celery] Failed to send verification email to {email}: {result["message"]}')
            # Повторяем при неудаче
            raise Exception(result['message'])
            
        return result
        
    except Exception as exc:
        logger.exception(f'[Celery] Error sending verification email to {email}: {exc}')
        # Повторяем с экспоненциальной задержкой
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(name='accounts.tasks.check_expiring_subscriptions')
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


@shared_task(name='accounts.tasks.process_expired_subscriptions')
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


@shared_task(name='accounts.tasks.sync_teacher_storage_usage')
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


@shared_task(name='accounts.tasks.check_consecutive_absences')
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


@shared_task(name='accounts.tasks.notify_recording_available')
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


# =============================================================================
# АНАЛИТИЧЕСКИЕ УВЕДОМЛЕНИЯ
# =============================================================================

PERFORMANCE_DROP_COOLDOWN_HOURS = 72
GROUP_HEALTH_COOLDOWN_HOURS = 48
GRADING_BACKLOG_COOLDOWN_HOURS = 24
INACTIVE_STUDENT_COOLDOWN_HOURS = 72
STUDENT_ABSENCE_COOLDOWN_HOURS = 48
STUDENT_INACTIVITY_COOLDOWN_HOURS = 168  # 1 неделя


@shared_task(name='accounts.tasks.check_performance_drops')
def check_performance_drops():
    """
    Проверяет падение успеваемости учеников и уведомляет учителей.
    
    Сравнивает средний балл за последние N работ с предыдущим окном.
    Запускается ежедневно.
    """
    import logging
    from django.contrib.auth import get_user_model
    from django.db.models import Avg
    from homework.models import StudentSubmission
    from schedule.models import Group
    
    logger = logging.getLogger(__name__)
    now = timezone.now()
    
    User = get_user_model()
    teachers = User.objects.filter(role='teacher', is_active=True)
    
    total_alerts = 0
    sent_notifications = 0
    
    for teacher in teachers:
        try:
            settings_obj, _ = NotificationSettings.objects.get_or_create(user=teacher)
            if not settings_obj.notify_performance_drop:
                continue
            
            drop_percent = settings_obj.performance_drop_percent or 20
            
            groups = Group.objects.filter(teacher=teacher)
            teacher_alerts = []
            
            for group in groups:
                students = group.students.filter(is_active=True)
                
                for student in students:
                    # Последние 5 работ vs предыдущие 5
                    recent_subs = StudentSubmission.objects.filter(
                        student=student,
                        homework__teacher=teacher,
                        status='graded',
                        total_score__isnull=False
                    ).order_by('-graded_at')[:10]
                    
                    if recent_subs.count() < 6:
                        continue
                    
                    recent_5 = list(recent_subs[:5])
                    prev_5 = list(recent_subs[5:10])
                    
                    if not prev_5:
                        continue
                    
                    recent_avg = sum(s.total_score for s in recent_5) / len(recent_5)
                    prev_avg = sum(s.total_score for s in prev_5) / len(prev_5)
                    
                    if prev_avg == 0:
                        continue
                    
                    drop = ((prev_avg - recent_avg) / prev_avg) * 100
                    
                    if drop >= drop_percent:
                        teacher_alerts.append({
                            'student_name': student.get_full_name() or student.email,
                            'group_name': group.name,
                            'prev_avg': round(prev_avg, 1),
                            'recent_avg': round(recent_avg, 1),
                            'drop_percent': round(drop, 0),
                        })
            
            if not teacher_alerts:
                continue
            
            total_alerts += len(teacher_alerts)
            
            # Проверяем cooldown
            recently_notified = NotificationLog.objects.filter(
                user=teacher,
                notification_type='performance_drop_alert',
                created_at__gte=now - timedelta(hours=PERFORMANCE_DROP_COOLDOWN_HOURS),
            ).exists()
            
            if recently_notified:
                continue
            
            # Формируем сообщение
            message_parts = ["📉 Внимание! Падение успеваемости\n"]
            for a in teacher_alerts[:5]:
                message_parts.append(
                    f"• {a['student_name']} ({a['group_name']}): "
                    f"{a['prev_avg']}→{a['recent_avg']} (−{a['drop_percent']:.0f}%)"
                )
            if len(teacher_alerts) > 5:
                message_parts.append(f"... и ещё {len(teacher_alerts) - 5}")
            
            message_parts.append("\nОткройте раздел Аналитика для подробностей.")
            message = "\n".join(message_parts)
            
            if send_telegram_notification(teacher, 'performance_drop_alert', message):
                sent_notifications += 1
                
        except Exception as e:
            logger.exception(f"Error checking performance for teacher {teacher.id}: {e}")
    
    return {
        'total_alerts': total_alerts,
        'sent_notifications': sent_notifications,
        'timestamp': now.isoformat(),
    }


@shared_task(name='accounts.tasks.check_group_health')
def check_group_health():
    """
    Проверяет 'здоровье' групп: посещаемость и успеваемость за неделю.
    
    Сравнивает текущую неделю с предыдущими 2-мя.
    Запускается раз в неделю (понедельник).
    """
    import logging
    from django.contrib.auth import get_user_model
    from django.db.models import Avg, Count
    from schedule.models import Group, Lesson
    from homework.models import StudentSubmission
    
    logger = logging.getLogger(__name__)
    now = timezone.now()
    
    User = get_user_model()
    teachers = User.objects.filter(role='teacher', is_active=True)
    
    total_alerts = 0
    sent_notifications = 0
    
    # Диапазоны недель
    this_week_start = now - timedelta(days=7)
    prev_weeks_start = now - timedelta(days=21)
    
    for teacher in teachers:
        try:
            settings_obj, _ = NotificationSettings.objects.get_or_create(user=teacher)
            if not settings_obj.notify_group_health:
                continue
            
            groups = Group.objects.filter(teacher=teacher)
            teacher_alerts = []
            
            for group in groups:
                # Посещаемость за эту неделю
                this_week_lessons = Lesson.objects.filter(
                    group=group,
                    start_time__gte=this_week_start,
                    start_time__lt=now
                )
                
                if not this_week_lessons.exists():
                    continue
                
                # Считаем посещаемость
                from accounts.models import AttendanceRecord
                
                this_week_attendance = AttendanceRecord.objects.filter(
                    lesson__in=this_week_lessons,
                    status='attended'
                ).count()
                
                total_possible = this_week_lessons.count() * group.students.count()
                if total_possible == 0:
                    continue
                
                this_week_rate = (this_week_attendance / total_possible) * 100
                
                # Сравниваем с предыдущими неделями
                prev_lessons = Lesson.objects.filter(
                    group=group,
                    start_time__gte=prev_weeks_start,
                    start_time__lt=this_week_start
                )
                
                if prev_lessons.exists():
                    prev_attendance = AttendanceRecord.objects.filter(
                        lesson__in=prev_lessons,
                        status='attended'
                    ).count()
                    prev_total = prev_lessons.count() * group.students.count()
                    prev_rate = (prev_attendance / prev_total) * 100 if prev_total > 0 else 0
                    
                    # Если падение более 15%
                    if prev_rate > 0 and (prev_rate - this_week_rate) > 15:
                        teacher_alerts.append({
                            'group_name': group.name,
                            'metric': 'посещаемость',
                            'prev_value': round(prev_rate, 0),
                            'current_value': round(this_week_rate, 0),
                        })
            
            if not teacher_alerts:
                continue
            
            total_alerts += len(teacher_alerts)
            
            # Проверяем cooldown
            recently_notified = NotificationLog.objects.filter(
                user=teacher,
                notification_type='group_health_alert',
                created_at__gte=now - timedelta(hours=GROUP_HEALTH_COOLDOWN_HOURS),
            ).exists()
            
            if recently_notified:
                continue
            
            # Формируем сообщение
            message_parts = ["📊 Внимание! Аномалии по группам\n"]
            for a in teacher_alerts[:3]:
                message_parts.append(
                    f"• {a['group_name']}: {a['metric']} {a['prev_value']}%→{a['current_value']}%"
                )
            if len(teacher_alerts) > 3:
                message_parts.append(f"... и ещё {len(teacher_alerts) - 3}")
            
            message_parts.append("\nОткройте раздел Аналитика для подробностей.")
            message = "\n".join(message_parts)
            
            if send_telegram_notification(teacher, 'group_health_alert', message):
                sent_notifications += 1
                
        except Exception as e:
            logger.exception(f"Error checking group health for teacher {teacher.id}: {e}")
    
    return {
        'total_alerts': total_alerts,
        'sent_notifications': sent_notifications,
        'timestamp': now.isoformat(),
    }


@shared_task(name='accounts.tasks.check_grading_backlog')
def check_grading_backlog():
    """
    Проверяет накопившиеся непроверенные ДЗ у учителей.
    
    Уведомляет, если N+ работ висят >48ч без проверки.
    Запускается ежедневно в 10:00.
    """
    import logging
    from django.contrib.auth import get_user_model
    from homework.models import StudentSubmission
    
    logger = logging.getLogger(__name__)
    now = timezone.now()
    
    User = get_user_model()
    teachers = User.objects.filter(role='teacher', is_active=True)
    
    total_backlog = 0
    sent_notifications = 0
    
    for teacher in teachers:
        try:
            settings_obj, _ = NotificationSettings.objects.get_or_create(user=teacher)
            if not settings_obj.notify_grading_backlog:
                continue
            
            threshold = settings_obj.grading_backlog_threshold or 5
            hours = settings_obj.grading_backlog_hours or 48
            cutoff = now - timedelta(hours=hours)
            
            # Работы, сданные более N часов назад и не проверенные
            pending = StudentSubmission.objects.filter(
                homework__teacher=teacher,
                status='submitted',
                submitted_at__lt=cutoff
            ).select_related('homework', 'student')
            
            count = pending.count()
            if count < threshold:
                continue
            
            total_backlog += count
            
            # Проверяем cooldown
            recently_notified = NotificationLog.objects.filter(
                user=teacher,
                notification_type='grading_backlog',
                created_at__gte=now - timedelta(hours=GRADING_BACKLOG_COOLDOWN_HOURS),
            ).exists()
            
            if recently_notified:
                continue
            
            # Формируем сообщение
            oldest = pending.order_by('submitted_at').first()
            oldest_days = (now - oldest.submitted_at).days if oldest else 0
            
            message = (
                f"📝 Непроверенные работы: {count} шт.\n\n"
                f"Самая старая ждёт {oldest_days} дн.\n"
                f"Порог: >{threshold} работ, >{hours}ч без проверки.\n\n"
                "Откройте раздел ДЗ для проверки."
            )
            
            if send_telegram_notification(teacher, 'grading_backlog', message):
                sent_notifications += 1
                
        except Exception as e:
            logger.exception(f"Error checking grading backlog for teacher {teacher.id}: {e}")
    
    return {
        'total_backlog': total_backlog,
        'sent_notifications': sent_notifications,
        'timestamp': now.isoformat(),
    }


@shared_task(name='accounts.tasks.check_inactive_students')
def check_inactive_students():
    """
    Проверяет неактивных учеников и уведомляет учителей.
    
    Ученик считается неактивным, если N дней нет сдач ДЗ и посещений.
    Запускается ежедневно.
    """
    import logging
    from django.contrib.auth import get_user_model
    from django.db.models import Max
    from homework.models import StudentSubmission
    from schedule.models import Group
    
    logger = logging.getLogger(__name__)
    now = timezone.now()
    
    User = get_user_model()
    teachers = User.objects.filter(role='teacher', is_active=True)
    
    total_inactive = 0
    sent_notifications = 0
    
    for teacher in teachers:
        try:
            settings_obj, _ = NotificationSettings.objects.get_or_create(user=teacher)
            if not settings_obj.notify_inactive_student:
                continue
            
            days = settings_obj.inactive_student_days or 7
            cutoff = now - timedelta(days=days)
            
            groups = Group.objects.filter(teacher=teacher)
            teacher_alerts = []
            
            for group in groups:
                students = group.students.filter(is_active=True)
                
                for student in students:
                    # Последняя сдача ДЗ
                    last_sub = StudentSubmission.objects.filter(
                        student=student,
                        homework__teacher=teacher
                    ).aggregate(last=Max('submitted_at'))['last']
                    
                    # Последнее посещение
                    from accounts.models import AttendanceRecord
                    last_attend = AttendanceRecord.objects.filter(
                        student=student,
                        status='attended',
                        lesson__group=group
                    ).aggregate(last=Max('lesson__start_time'))['last']
                    
                    # Берём максимум из двух дат
                    last_activity = max(filter(None, [last_sub, last_attend]), default=None)
                    
                    if last_activity and last_activity < cutoff:
                        inactive_days = (now - last_activity).days
                        teacher_alerts.append({
                            'student_name': student.get_full_name() or student.email,
                            'group_name': group.name,
                            'inactive_days': inactive_days,
                        })
            
            if not teacher_alerts:
                continue
            
            total_inactive += len(teacher_alerts)
            
            # Проверяем cooldown
            recently_notified = NotificationLog.objects.filter(
                user=teacher,
                notification_type='inactive_student_alert',
                created_at__gte=now - timedelta(hours=INACTIVE_STUDENT_COOLDOWN_HOURS),
            ).exists()
            
            if recently_notified:
                continue
            
            # Формируем сообщение
            message_parts = ["😴 Неактивные ученики\n"]
            for a in sorted(teacher_alerts, key=lambda x: -x['inactive_days'])[:5]:
                message_parts.append(
                    f"• {a['student_name']} ({a['group_name']}): {a['inactive_days']} дн."
                )
            if len(teacher_alerts) > 5:
                message_parts.append(f"... и ещё {len(teacher_alerts) - 5}")
            
            message_parts.append("\nСвяжитесь с ними или проверьте в Аналитике.")
            message = "\n".join(message_parts)
            
            if send_telegram_notification(teacher, 'inactive_student_alert', message):
                sent_notifications += 1
                
        except Exception as e:
            logger.exception(f"Error checking inactive students for teacher {teacher.id}: {e}")
    
    return {
        'total_inactive': total_inactive,
        'sent_notifications': sent_notifications,
        'timestamp': now.isoformat(),
    }


@shared_task(name='accounts.tasks.send_student_absence_warnings')
def send_student_absence_warnings():
    """
    Отправляет ученикам предупреждения о их пропусках.
    
    Мягкое напоминание при 2-3 пропусках подряд.
    Запускается ежедневно.
    """
    import logging
    from django.contrib.auth import get_user_model
    from schedule.models import Group
    
    logger = logging.getLogger(__name__)
    now = timezone.now()
    
    User = get_user_model()
    students = User.objects.filter(role='student', is_active=True)
    
    sent = 0
    
    for student in students:
        try:
            settings_obj, _ = NotificationSettings.objects.get_or_create(user=student)
            if not settings_obj.notify_student_absence_warning:
                continue
            
            # Проверяем cooldown
            recently_notified = NotificationLog.objects.filter(
                user=student,
                notification_type='student_absence_warning',
                created_at__gte=now - timedelta(hours=STUDENT_ABSENCE_COOLDOWN_HOURS),
            ).exists()
            
            if recently_notified:
                continue
            
            # Считаем пропуски подряд
            from accounts.models import AttendanceRecord
            
            recent_records = AttendanceRecord.objects.filter(
                student=student
            ).order_by('-lesson__start_time')[:5]
            
            consecutive_absences = 0
            for record in recent_records:
                if record.status == 'absent':
                    consecutive_absences += 1
                else:
                    break
            
            if consecutive_absences >= 2:
                message = (
                    f"📚 У вас {consecutive_absences} пропуска подряд.\n\n"
                    "Если возникли трудности — обратитесь к преподавателю.\n"
                    "Вы можете посмотреть записи уроков в разделе Записи."
                )
                
                if send_telegram_notification(student, 'student_absence_warning', message):
                    sent += 1
                    
        except Exception as e:
            logger.exception(f"Error sending absence warning to student {student.id}: {e}")
    
    return {
        'sent': sent,
        'timestamp': now.isoformat(),
    }


@shared_task(name='accounts.tasks.send_student_inactivity_nudges')
def send_student_inactivity_nudges():
    """
    Отправляет ученикам мягкие напоминания при длительной неактивности.
    
    Запускается раз в неделю.
    """
    import logging
    from django.contrib.auth import get_user_model
    from django.db.models import Max
    from homework.models import StudentSubmission
    
    logger = logging.getLogger(__name__)
    now = timezone.now()
    cutoff = now - timedelta(days=7)
    
    User = get_user_model()
    students = User.objects.filter(role='student', is_active=True)
    
    sent = 0
    
    for student in students:
        try:
            settings_obj, _ = NotificationSettings.objects.get_or_create(user=student)
            if not settings_obj.notify_inactivity_nudge:
                continue
            
            # Проверяем cooldown (1 неделя)
            recently_notified = NotificationLog.objects.filter(
                user=student,
                notification_type='student_inactivity_nudge',
                created_at__gte=now - timedelta(hours=STUDENT_INACTIVITY_COOLDOWN_HOURS),
            ).exists()
            
            if recently_notified:
                continue
            
            # Последняя активность
            last_sub = StudentSubmission.objects.filter(
                student=student
            ).aggregate(last=Max('submitted_at'))['last']
            
            from accounts.models import AttendanceRecord
            last_attend = AttendanceRecord.objects.filter(
                student=student,
                status='attended'
            ).aggregate(last=Max('lesson__start_time'))['last']
            
            last_activity = max(filter(None, [last_sub, last_attend]), default=None)
            
            if last_activity and last_activity < cutoff:
                days_inactive = (now - last_activity).days
                message = (
                    f"👋 Давно вас не видели!\n\n"
                    f"Последняя активность: {days_inactive} дн. назад.\n"
                    "Загляните в Teaching Panel — возможно, есть новые задания или записи уроков."
                )
                
                if send_telegram_notification(student, 'student_inactivity_nudge', message):
                    sent += 1
                    
        except Exception as e:
            logger.exception(f"Error sending inactivity nudge to student {student.id}: {e}")
    
    return {
        'sent': sent,
        'timestamp': now.isoformat(),
    }


TOP_RATING_COOLDOWN_HOURS = 720  # 30 дней — не спамим одним и тем же достижением


@shared_task(name='accounts.tasks.send_top_rating_notifications')
def send_top_rating_notifications():
    """
    Отправляет уведомления ученикам, попавшим в топ-3 рейтинга за прошлый месяц.
    
    Запускается 1 числа каждого месяца.
    Проверяет рейтинг за предыдущий месяц и отправляет поздравления топ-3.
    """
    import logging
    from datetime import date
    from dateutil.relativedelta import relativedelta
    from django.db.models import Sum
    
    from .attendance_service import RatingService
    from .notifications import notify_student_top_rating, get_season_info
    from schedule.models import Group
    
    logger = logging.getLogger(__name__)
    now = timezone.now()
    
    # Определяем прошлый месяц
    last_month = now - relativedelta(months=1)
    month_str = f"{last_month.year}-{last_month.month:02d}"
    month_label = last_month.strftime("%B %Y").capitalize()
    
    # Русские названия месяцев
    russian_months = {
        1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
        5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
        9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
    }
    month_label = f"{russian_months[last_month.month]} {last_month.year}"
    
    sent = 0
    groups_processed = 0
    
    # Получаем все группы (Group не имеет поля is_active)
    groups = Group.objects.all().prefetch_related('students')
    
    for group in groups:
        try:
            # Получаем рейтинг за прошлый месяц
            rating_data = RatingService.get_group_rating_for_period(group.id, month_str)
            
            if not rating_data or len(rating_data) == 0:
                continue
            
            groups_processed += 1
            
            # Уведомляем топ-3
            for rank, student_data in enumerate(rating_data[:3], start=1):
                student_id = student_data.get('student_id')
                total_points = student_data.get('total_points', 0)
                
                if not student_id or total_points == 0:
                    continue
                
                from django.contrib.auth import get_user_model
                User = get_user_model()
                
                try:
                    student = User.objects.get(id=student_id)
                except User.DoesNotExist:
                    continue
                
                # Проверяем, не отправляли ли уже это достижение
                from django.db.models import Q
                already_notified = NotificationLog.objects.filter(
                    Q(message__icontains=month_label) & Q(message__icontains=group.name),
                    user=student,
                    notification_type='achievement',
                    created_at__gte=now - timedelta(hours=TOP_RATING_COOLDOWN_HOURS),
                ).exists()
                
                if already_notified:
                    continue
                
                if notify_student_top_rating(
                    student=student,
                    rank=rank,
                    period_type='month',
                    period_label=month_label,
                    group_name=group.name,
                    total_points=total_points
                ):
                    sent += 1
                    logger.info(f"Sent top-{rank} notification to student {student.id} for group {group.id}")
                    
        except Exception as e:
            logger.exception(f"Error processing top rating for group {group.id}: {e}")
    
    return {
        'groups_processed': groups_processed,
        'notifications_sent': sent,
        'period': month_label,
        'timestamp': now.isoformat(),
    }


@shared_task(name='accounts.tasks.send_season_top_rating_notifications')
def send_season_top_rating_notifications():
    """
    Отправляет уведомления ученикам, попавшим в топ-3 рейтинга за прошлый сезон.
    
    Запускается 1 числа первого месяца нового сезона (март, июнь, сентябрь, декабрь).
    """
    import logging
    from dateutil.relativedelta import relativedelta
    
    from .attendance_service import RatingService
    from .notifications import notify_student_top_rating, get_season_info
    from schedule.models import Group
    
    logger = logging.getLogger(__name__)
    now = timezone.now()
    
    # Определяем текущий и прошлый сезон
    current_season, _, _, _ = get_season_info(now)
    
    # Определяем начальную дату прошлого сезона
    season_months = {
        'winter': ([12, 1, 2], "Зима"),
        'spring': ([3, 4, 5], "Весна"),
        'summer': ([6, 7, 8], "Лето"),
        'autumn': ([9, 10, 11], "Осень"),
    }
    
    # Прошлый сезон
    prev_seasons = ['autumn', 'winter', 'spring', 'summer']
    current_idx = prev_seasons.index(current_season) if current_season in prev_seasons else 0
    prev_season = prev_seasons[(current_idx - 1) % 4]
    
    prev_months, prev_season_name = season_months[prev_season]
    
    # Вычисляем год для прошлого сезона
    if prev_season == 'winter':
        # Зима охватывает два года
        year = now.year - 1 if now.month >= 3 else now.year - 1
        season_label = f"{prev_season_name} {year}-{year + 1}"
    else:
        year = now.year if now.month > prev_months[-1] else now.year - 1
        season_label = f"{prev_season_name} {year}"
    
    sent = 0
    groups_processed = 0
    
    # Получаем все группы (Group не имеет поля is_active)
    groups = Group.objects.all().prefetch_related('students')
    
    for group in groups:
        try:
            # Суммируем рейтинг за все месяцы сезона
            season_ratings = {}
            
            for month in prev_months:
                if prev_season == 'winter' and month == 12:
                    month_year = year
                elif prev_season == 'winter':
                    month_year = year + 1
                else:
                    month_year = year
                
                month_str = f"{month_year}-{month:02d}"
                
                try:
                    rating_data = RatingService.get_group_rating_for_period(group.id, month_str)
                    
                    if rating_data:
                        for student_data in rating_data:
                            sid = student_data.get('student_id')
                            if sid:
                                if sid not in season_ratings:
                                    season_ratings[sid] = {
                                        'student_id': sid,
                                        'student_name': student_data.get('student_name', ''),
                                        'total_points': 0,
                                    }
                                season_ratings[sid]['total_points'] += student_data.get('total_points', 0)
                except Exception:
                    pass
            
            if not season_ratings:
                continue
            
            groups_processed += 1
            
            # Сортируем по баллам и берём топ-3
            sorted_ratings = sorted(
                season_ratings.values(),
                key=lambda x: x['total_points'],
                reverse=True
            )[:3]
            
            for rank, student_data in enumerate(sorted_ratings, start=1):
                student_id = student_data.get('student_id')
                total_points = student_data.get('total_points', 0)
                
                if not student_id or total_points == 0:
                    continue
                
                from django.contrib.auth import get_user_model
                User = get_user_model()
                
                try:
                    student = User.objects.get(id=student_id)
                except User.DoesNotExist:
                    continue
                
                # Проверяем, не отправляли ли уже
                from django.db.models import Q
                already_notified = NotificationLog.objects.filter(
                    Q(message__icontains=season_label) & Q(message__icontains=group.name),
                    user=student,
                    notification_type='achievement',
                    created_at__gte=now - timedelta(hours=TOP_RATING_COOLDOWN_HOURS),
                ).exists()
                
                if already_notified:
                    continue
                
                if notify_student_top_rating(
                    student=student,
                    rank=rank,
                    period_type='season',
                    period_label=season_label,
                    group_name=group.name,
                    total_points=total_points
                ):
                    sent += 1
                    logger.info(f"Sent season top-{rank} notification to student {student.id} for group {group.id}")
                    
        except Exception as e:
            logger.exception(f"Error processing season top rating for group {group.id}: {e}")
    
    return {
        'groups_processed': groups_processed,
        'notifications_sent': sent,
        'period': season_label,
        'timestamp': now.isoformat(),
    }


# ==========================================================================
# Автопродление подписок и Zoom add-on
# ==========================================================================

@shared_task(name='accounts.tasks.process_auto_renewals')
def process_auto_renewals():
    """
    Обрабатывает автопродления подписок и Zoom add-on.
    
    Запускается ежедневно. Ищет подписки, которые:
    1. Истекают в ближайшие 24 часа
    2. Имеют auto_renew=True и сохранённый tbank_rebill_id
    
    Для Zoom add-on проверяет zoom_addon_auto_renew и zoom_addon_tbank_rebill_id.
    """
    import logging
    from .tbank_service import TBankService
    from .notifications import (
        notify_auto_renewal_success, 
        notify_auto_renewal_failed,
        notify_subscription_expiring_no_payment
    )
    
    logger = logging.getLogger(__name__)
    now = timezone.now()
    window_end = now + timedelta(hours=24)
    
    # Найти подписки для автопродления
    subscriptions = Subscription.objects.select_related('user').filter(
        status=Subscription.STATUS_ACTIVE,
        expires_at__isnull=False,
        expires_at__lte=window_end,
        expires_at__gte=now,
        auto_renew=True,
        tbank_rebill_id__isnull=False,
    ).exclude(tbank_rebill_id='')
    
    renewed = 0
    failed = 0
    churn_signals = 0
    
    for sub in subscriptions:
        # Определяем план (monthly или yearly) по текущей подписке
        days_remaining = (sub.expires_at - sub.created_at).days if sub.created_at else 30
        plan = 'yearly' if days_remaining > 60 else 'monthly'
        
        logger.info(f"Processing auto-renewal for subscription {sub.id}, user {sub.user.email}, plan={plan}")
        
        result = TBankService.charge_recurring(sub, plan, sub.tbank_rebill_id)
        
        if result and result.get('success'):
            logger.info(f"Auto-renewal initiated for subscription {sub.id}")
            # Уведомление придёт через вебхук после CONFIRMED статуса
            renewed += 1
        else:
            error_msg = result.get('error', 'Unknown error') if result else 'No response'
            logger.error(f"Auto-renewal failed for subscription {sub.id}: {error_msg}")
            
            # Отключаем автопродление при ошибке
            sub.auto_renew = False
            sub.save(update_fields=['auto_renew'])
            
            # Уведомление о неудачном автопродлении
            notify_auto_renewal_failed(
                subscription=sub, 
                user=sub.user, 
                renewal_type='subscription', 
                reason=error_msg
            )
            failed += 1
    
    # Отправляем churn signal для подписок без автопродления
    expiring_no_payment = Subscription.objects.select_related('user').filter(
        status=Subscription.STATUS_ACTIVE,
        expires_at__isnull=False,
        expires_at__lte=now + timedelta(days=3),
        expires_at__gte=now,
        auto_renew=False,
    )
    
    for sub in expiring_no_payment:
        # Проверяем, не отправляли ли уже
        already_notified = NotificationLog.objects.filter(
            user=sub.user,
            notification_type='churn_warning',
            created_at__gte=now - timedelta(hours=48),
        ).exists()
        
        if not already_notified:
            days_left = max((sub.expires_at - now).days, 0)
            notify_subscription_expiring_no_payment(sub, sub.user, days_left)
            
            # Логируем отправку
            NotificationLog.objects.create(
                user=sub.user,
                notification_type='churn_warning',
                message=f"Churn warning sent: {days_left} days left"
            )
            churn_signals += 1
    
    logger.info(f"[Celery] process_auto_renewals: renewed={renewed}, failed={failed}, churn_signals={churn_signals}")
    
    return {
        'renewed': renewed,
        'failed': failed,
        'churn_signals': churn_signals,
        'timestamp': now.isoformat(),
    }


@shared_task(name='accounts.tasks.process_zoom_addon_renewals')
def process_zoom_addon_renewals():
    """
    Обрабатывает автопродления Zoom add-on.
    
    Запускается ежедневно. Ищет подписки где zoom_addon_expires_at
    истекает в ближайшие 24 часа и есть zoom_addon_auto_renew=True.
    """
    import logging
    from .tbank_service import TBankService
    from .notifications import notify_auto_renewal_success, notify_auto_renewal_failed
    
    logger = logging.getLogger(__name__)
    now = timezone.now()
    window_end = now + timedelta(hours=24)
    
    subscriptions = Subscription.objects.select_related('user').filter(
        zoom_addon_expires_at__isnull=False,
        zoom_addon_expires_at__lte=window_end,
        zoom_addon_expires_at__gte=now,
        zoom_addon_auto_renew=True,
        zoom_addon_tbank_rebill_id__isnull=False,
    ).exclude(zoom_addon_tbank_rebill_id='')
    
    renewed = 0
    failed = 0
    
    for sub in subscriptions:
        logger.info(f"Processing Zoom add-on renewal for subscription {sub.id}")
        
        result = TBankService.charge_zoom_addon_recurring(sub, sub.zoom_addon_tbank_rebill_id)
        
        if result and result.get('success'):
            logger.info(f"Zoom add-on renewal initiated for subscription {sub.id}")
            renewed += 1
        else:
            error_msg = result.get('error', 'Unknown error') if result else 'No response'
            logger.error(f"Zoom add-on renewal failed for subscription {sub.id}: {error_msg}")
            
            # Отключаем автопродление
            sub.zoom_addon_auto_renew = False
            sub.save(update_fields=['zoom_addon_auto_renew'])
            
            notify_auto_renewal_failed(
                subscription=sub,
                user=sub.user,
                renewal_type='zoom_addon',
                reason=error_msg
            )
            failed += 1
    
    logger.info(f"[Celery] process_zoom_addon_renewals: renewed={renewed}, failed={failed}")
    
    return {
        'renewed': renewed,
        'failed': failed,
        'timestamp': now.isoformat(),
    }


# ==========================================================================
# Еженедельный отчёт о выручке
# ==========================================================================

@shared_task(name='accounts.tasks.send_weekly_revenue_report_task')
def send_weekly_revenue_report_task():
    """
    Отправляет еженедельный отчёт о выручке в Telegram.
    
    Запускается каждый понедельник в 10:00.
    Сравнивает текущую неделю с предыдущей.
    """
    import logging
    from .notifications import send_weekly_revenue_report
    
    logger = logging.getLogger(__name__)
    
    try:
        send_weekly_revenue_report()
        logger.info("[Celery] Weekly revenue report sent successfully")
        return {'status': 'sent', 'timestamp': timezone.now().isoformat()}
    except Exception as e:
        logger.exception(f"[Celery] Failed to send weekly revenue report: {e}")
        return {'status': 'error', 'error': str(e), 'timestamp': timezone.now().isoformat()}


# ==========================================================================
# Rate Limiting Auto-Recovery
# ==========================================================================

@shared_task(name='accounts.tasks.monitor_rate_limiting')
def monitor_rate_limiting():
    """
    Мониторит состояние rate limiting и отправляет алерты при проблемах.
    
    Запускается каждые 15 минут.
    - Проверяет количество активных блокировок
    - Отправляет алерт если блокировок слишком много
    - Автоматически сбрасывает лимиты при критическом количестве
    """
    from .bot_protection import get_rate_limit_stats, clear_all_rate_limits
    
    try:
        stats = get_rate_limit_stats()
        
        if not stats.get('success'):
            logger.warning(f"[Celery] monitor_rate_limiting: failed to get stats: {stats.get('error')}")
            return stats
        
        rate_stats = stats.get('stats', {})
        total_blocks = sum(rate_stats.values())
        
        logger.info(f"[Celery] Rate limiting stats: {rate_stats}")
        
        # Критический порог - слишком много блокировок
        CRITICAL_THRESHOLD = 100
        
        if total_blocks >= CRITICAL_THRESHOLD:
            logger.warning(f"[Celery] CRITICAL: {total_blocks} rate limit blocks detected!")
            
            # Отправляем алерт
            try:
                from support.telegram_utils import send_admin_notification
                send_admin_notification(
                    f"🚨 CRITICAL Rate Limiting Alert\n\n"
                    f"Обнаружено {total_blocks} активных блокировок!\n"
                    f"Статистика:\n"
                    f"- Регистрации: {rate_stats.get('registration_blocks', 0)}\n"
                    f"- Логины: {rate_stats.get('login_blocks', 0)}\n"
                    f"- Баны: {rate_stats.get('bans', 0)}\n"
                    f"- Throttle login: {rate_stats.get('throttle_login', 0)}\n"
                    f"- Throttle anon: {rate_stats.get('throttle_anon', 0)}\n\n"
                    f"Автоматический сброс запущен..."
                )
            except Exception as e:
                logger.warning(f"[Celery] Failed to send critical alert: {e}")
            
            # Автоматический сброс при критическом количестве
            clear_result = clear_all_rate_limits()
            logger.info(f"[Celery] Auto-cleared rate limits: {clear_result}")
            
            return {
                'status': 'critical_auto_cleared',
                'stats': rate_stats,
                'clear_result': clear_result,
                'timestamp': timezone.now().isoformat(),
            }
        
        return {
            'status': 'ok',
            'stats': rate_stats,
            'total_blocks': total_blocks,
            'timestamp': timezone.now().isoformat(),
        }
        
    except Exception as e:
        logger.exception(f"[Celery] monitor_rate_limiting error: {e}")
        return {'status': 'error', 'error': str(e)}


@shared_task(name='accounts.tasks.cleanup_old_rate_limits')
def cleanup_old_rate_limits():
    """
    Очищает устаревшие rate limit записи из Redis.
    
    Запускается раз в день в 4:00 ночи.
    Redis TTL должен автоматически удалять ключи, но это страховка.
    """
    from .bot_protection import get_rate_limit_stats
    
    try:
        # Получаем статистику до очистки
        before_stats = get_rate_limit_stats()
        
        # Redis TTL автоматически удаляет ключи, но проверим
        # Если ключей слишком много (более 500), делаем принудительную очистку
        if before_stats.get('success'):
            total = sum(before_stats.get('stats', {}).values())
            if total > 500:
                from .bot_protection import clear_all_rate_limits
                clear_result = clear_all_rate_limits()
                logger.info(f"[Celery] Forced cleanup of {total} rate limit keys: {clear_result}")
                return {
                    'status': 'force_cleared',
                    'before': before_stats.get('stats'),
                    'cleared': clear_result.get('deleted', 0),
                }
        
        logger.info(f"[Celery] Rate limit cleanup check complete: {before_stats.get('stats', {})}")
        return {
            'status': 'ok',
            'stats': before_stats.get('stats', {}),
        }
        
    except Exception as e:
        logger.exception(f"[Celery] cleanup_old_rate_limits error: {e}")
        return {'status': 'error', 'error': str(e)}
