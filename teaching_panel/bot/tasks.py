"""
Celery задачи для модуля bot
"""
import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)


@shared_task(name='bot.tasks.process_scheduled_messages')
def process_scheduled_messages():
    """
    Обрабатывает запланированные сообщения.
    
    Запускается каждую минуту через Celery Beat.
    Находит сообщения, время отправки которых наступило, и отправляет их.
    """
    from .models import ScheduledMessage
    from .services import BroadcastService
    
    now = timezone.now()
    
    # Находим сообщения к отправке
    messages = ScheduledMessage.objects.filter(
        scheduled_at__lte=now,
        status='pending',
    ).select_related('teacher')
    
    if not messages:
        return "No pending messages"
    
    service = BroadcastService()
    sent_count = 0
    error_count = 0
    
    for msg in messages:
        try:
            msg.status = 'processing'
            msg.save(update_fields=['status'])
            
            # Определяем получателей
            if msg.target_type == 'groups':
                group_ids = msg.target_ids or []
                result = async_to_sync(service.send_to_groups)(
                    group_ids=group_ids,
                    text=msg.content,
                    teacher_id=msg.teacher_id,
                    message_type=msg.message_type,
                )
            elif msg.target_type == 'users':
                user_ids = msg.target_ids or []
                result = async_to_sync(service.broadcast_to_users)(
                    telegram_ids=user_ids,
                    text=msg.content,
                    teacher_id=msg.teacher_id,
                    message_type=msg.message_type,
                )
            else:
                logger.warning(f"Unknown target_type: {msg.target_type}")
                msg.status = 'failed'
                msg.error_message = f"Unknown target_type: {msg.target_type}"
                msg.save()
                error_count += 1
                continue
            
            # Обновляем статус
            msg.status = 'sent'
            msg.sent_at = timezone.now()
            msg.sent_count = result.get('sent_count', 0)
            msg.failed_count = result.get('failed_count', 0)
            msg.save()
            
            sent_count += 1
            logger.info(f"Sent scheduled message {msg.id}: {result['sent_count']} recipients")
            
        except Exception as e:
            logger.error(f"Error processing scheduled message {msg.id}: {e}")
            msg.status = 'failed'
            msg.error_message = str(e)[:500]
            msg.save()
            error_count += 1
    
    return f"Processed: {sent_count} sent, {error_count} errors"


@shared_task(name='bot.tasks.cleanup_redis_dialog_states')
def cleanup_redis_dialog_states():
    """
    Очистка устаревших состояний диалогов в Redis.
    
    Запускается раз в 3 дня.
    Redis TTL должен автоматически удалять ключи, но эта задача
    служит дополнительной проверкой.
    """
    from .config import REDIS_URL
    import redis
    
    if not REDIS_URL:
        return "Redis not configured"
    
    try:
        r = redis.from_url(REDIS_URL)
        
        # Ищем все ключи dialog_state
        pattern = 'bot:dialog:*'
        keys = list(r.scan_iter(pattern, count=1000))
        
        # Ключи с TTL уже будут удалены Redis'ом
        # Проверяем ключи без TTL (не должно быть, но на всякий случай)
        orphaned = 0
        for key in keys:
            ttl = r.ttl(key)
            if ttl == -1:  # Ключ без TTL
                r.delete(key)
                orphaned += 1
        
        return f"Checked {len(keys)} keys, removed {orphaned} orphaned"
        
    except Exception as e:
        logger.error(f"Redis cleanup error: {e}")
        return f"Error: {e}"


@shared_task(name='bot.tasks.cleanup_old_broadcast_logs')
def cleanup_old_broadcast_logs():
    """
    Очистка старых логов рассылок (старше 30 дней).
    
    Запускается раз в неделю.
    """
    from .models import BroadcastLog, BroadcastRateLimit
    
    cutoff = timezone.now() - timedelta(days=30)
    
    # Удаляем старые логи
    deleted_logs = BroadcastLog.objects.filter(created_at__lt=cutoff).delete()
    
    # Удаляем старые rate limit записи
    rate_cutoff = timezone.now() - timedelta(hours=25)
    deleted_rates = BroadcastRateLimit.objects.filter(hour_start__lt=rate_cutoff).delete()
    
    return f"Deleted {deleted_logs[0]} logs, {deleted_rates[0]} rate limits"


@shared_task(name='bot.tasks.send_lesson_reminders')
def send_lesson_reminders():
    """
    Автоматическая отправка напоминаний об уроках.
    
    Запускается каждые 15 минут.
    Отправляет напоминания за 30 минут до начала урока.
    """
    from schedule.models import Lesson
    from .services import BroadcastService
    from .utils import render_template, get_default_template
    
    now = timezone.now()
    
    # Уроки, начинающиеся через 25-35 минут
    reminder_start = now + timedelta(minutes=25)
    reminder_end = now + timedelta(minutes=35)
    
    lessons = Lesson.objects.filter(
        start_time__gte=reminder_start,
        start_time__lte=reminder_end,
        is_cancelled=False,
        reminder_sent=False,  # Нужно добавить это поле в модель
    ).select_related('group', 'teacher').prefetch_related('group__students')
    
    if not lessons:
        return "No lessons to remind"
    
    service = BroadcastService()
    template = get_default_template('lesson_auto_reminder')
    
    sent_count = 0
    
    for lesson in lessons:
        try:
            message = render_template(
                template['content'],
                lesson_title=lesson.title,
                lesson_time=timezone.localtime(lesson.start_time).strftime('%H:%M'),
                group=lesson.group.name if lesson.group else '',
            )
            
            # Получаем telegram_ids учеников группы
            if lesson.group:
                students = lesson.group.students.filter(
                    is_active=True,
                    notification_consent=True,
                    telegram_id__isnull=False,
                ).exclude(telegram_id='')
                
                telegram_ids = [s.telegram_id for s in students if s.telegram_id]
                
                if telegram_ids:
                    result = async_to_sync(service.broadcast_to_users)(
                        telegram_ids=telegram_ids,
                        text=message,
                        teacher_id=lesson.teacher_id,
                        message_type='auto_lesson_reminder',
                    )
                    
                    # Помечаем, что напоминание отправлено
                    lesson.reminder_sent = True
                    lesson.save(update_fields=['reminder_sent'])
                    
                    sent_count += 1
            
        except Exception as e:
            logger.error(f"Error sending reminder for lesson {lesson.id}: {e}")
    
    return f"Sent {sent_count} lesson reminders"


@shared_task(name='bot.tasks.send_hw_deadline_reminders')
def send_hw_deadline_reminders():
    """
    Автоматическая отправка напоминаний о дедлайнах ДЗ.
    
    Запускается каждый час.
    Отправляет напоминания за 24 часа и за 2 часа до дедлайна.
    """
    from homework.models import Homework
    from .services import BroadcastService, HomeworkService
    from .utils import render_template, get_default_template
    
    now = timezone.now()
    
    # Напоминание за 24 часа (23-25 часов)
    deadline_24h_start = now + timedelta(hours=23)
    deadline_24h_end = now + timedelta(hours=25)
    
    # Напоминание за 2 часа (1.5-2.5 часа)
    deadline_2h_start = now + timedelta(hours=1, minutes=30)
    deadline_2h_end = now + timedelta(hours=2, minutes=30)
    
    service = BroadcastService()
    sent_count = 0
    
    # 24-часовые напоминания
    homeworks_24h = Homework.objects.filter(
        deadline__gte=deadline_24h_start,
        deadline__lte=deadline_24h_end,
        is_published=True,
        reminder_24h_sent=False,  # Нужно добавить поле
    )
    
    template_24h = get_default_template('hw_deadline_24h')
    
    for hw in homeworks_24h:
        try:
            # Получаем не сдавших
            not_submitted = async_to_sync(HomeworkService.get_not_submitted_students)(hw.id)
            telegram_ids = [tg for _, _, tg in not_submitted if tg]
            
            if telegram_ids:
                message = render_template(
                    template_24h['content'],
                    hw_title=hw.title,
                    deadline=timezone.localtime(hw.deadline).strftime('%d.%m в %H:%M'),
                )
                
                async_to_sync(service.broadcast_to_users)(
                    telegram_ids=telegram_ids,
                    text=message,
                    teacher_id=hw.teacher_id if hasattr(hw, 'teacher_id') else None,
                    message_type='auto_hw_reminder_24h',
                )
                
                hw.reminder_24h_sent = True
                hw.save(update_fields=['reminder_24h_sent'])
                sent_count += 1
                
        except Exception as e:
            logger.error(f"Error sending 24h reminder for hw {hw.id}: {e}")
    
    # 2-часовые напоминания
    homeworks_2h = Homework.objects.filter(
        deadline__gte=deadline_2h_start,
        deadline__lte=deadline_2h_end,
        is_published=True,
        reminder_2h_sent=False,  # Нужно добавить поле
    )
    
    template_2h = get_default_template('hw_deadline_2h')
    
    for hw in homeworks_2h:
        try:
            not_submitted = async_to_sync(HomeworkService.get_not_submitted_students)(hw.id)
            telegram_ids = [tg for _, _, tg in not_submitted if tg]
            
            if telegram_ids:
                message = render_template(
                    template_2h['content'],
                    hw_title=hw.title,
                )
                
                async_to_sync(service.broadcast_to_users)(
                    telegram_ids=telegram_ids,
                    text=message,
                    teacher_id=hw.teacher_id if hasattr(hw, 'teacher_id') else None,
                    message_type='auto_hw_reminder_2h',
                )
                
                hw.reminder_2h_sent = True
                hw.save(update_fields=['reminder_2h_sent'])
                sent_count += 1
                
        except Exception as e:
            logger.error(f"Error sending 2h reminder for hw {hw.id}: {e}")
    
    return f"Sent {sent_count} hw deadline reminders"
