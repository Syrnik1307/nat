"""
Сервис планирования отложенных сообщений
"""
import logging
from typing import List, Optional
from datetime import datetime, timedelta

from asgiref.sync import sync_to_async
from django.utils import timezone

from ..models import ScheduledMessage

logger = logging.getLogger(__name__)


class SchedulerService:
    """Сервис для планирования отложенных сообщений"""
    
    @staticmethod
    async def schedule_message(
        teacher_id: int,
        content: str,
        scheduled_at: datetime,
        message_type: str = 'custom',
        group_ids: List[int] = None,
        student_ids: List[int] = None,
        lesson_id: int = None,
        homework_id: int = None,
    ) -> ScheduledMessage:
        """Планирует отложенное сообщение"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        def create():
            teacher = User.objects.get(id=teacher_id)
            
            msg = ScheduledMessage.objects.create(
                teacher=teacher,
                message_type=message_type,
                content=content,
                scheduled_at=scheduled_at,
                lesson_id=lesson_id,
                homework_id=homework_id,
            )
            
            if group_ids:
                msg.target_groups.set(group_ids)
            
            if student_ids:
                msg.target_students.set(student_ids)
            
            return msg
        
        return await sync_to_async(create)()
    
    @staticmethod
    async def get_teacher_scheduled(teacher_id: int, limit: int = 20) -> List[ScheduledMessage]:
        """Получает запланированные сообщения учителя"""
        def query():
            return list(
                ScheduledMessage.objects.filter(
                    teacher_id=teacher_id,
                    status='pending',
                ).select_related('lesson', 'homework').prefetch_related(
                    'target_groups'
                ).order_by('scheduled_at')[:limit]
            )
        
        return await sync_to_async(query)()
    
    @staticmethod
    async def cancel_scheduled(message_id: int, teacher_id: int) -> bool:
        """
        Отменяет запланированное сообщение.
        Возвращает True если успешно.
        """
        def cancel():
            try:
                msg = ScheduledMessage.objects.get(
                    id=message_id,
                    teacher_id=teacher_id,
                    status='pending',
                )
                return msg.cancel()
            except ScheduledMessage.DoesNotExist:
                return False
        
        return await sync_to_async(cancel)()
    
    @staticmethod
    async def get_scheduled_detail(message_id: int, teacher_id: int) -> Optional[ScheduledMessage]:
        """Получает детали запланированного сообщения"""
        def query():
            try:
                return ScheduledMessage.objects.select_related(
                    'lesson', 'homework'
                ).prefetch_related(
                    'target_groups', 'target_students'
                ).get(
                    id=message_id,
                    teacher_id=teacher_id,
                )
            except ScheduledMessage.DoesNotExist:
                return None
        
        return await sync_to_async(query)()
    
    @staticmethod
    def calculate_schedule_time(option: str) -> datetime:
        """
        Рассчитывает время отправки по выбранной опции.
        Опции: 'now', '15min', '30min', '1hour', '2hours', 'tomorrow_9', 'tomorrow_18'
        """
        now = timezone.now()
        
        options = {
            'now': now,
            '15min': now + timedelta(minutes=15),
            '30min': now + timedelta(minutes=30),
            '1hour': now + timedelta(hours=1),
            '2hours': now + timedelta(hours=2),
            '3hours': now + timedelta(hours=3),
        }
        
        if option in options:
            return options[option]
        
        # Завтра в определённое время
        if option == 'tomorrow_9':
            tomorrow = now.date() + timedelta(days=1)
            return timezone.make_aware(
                datetime.combine(tomorrow, datetime.min.time().replace(hour=9))
            )
        
        if option == 'tomorrow_18':
            tomorrow = now.date() + timedelta(days=1)
            return timezone.make_aware(
                datetime.combine(tomorrow, datetime.min.time().replace(hour=18))
            )
        
        # По умолчанию - сейчас
        return now
    
    @staticmethod
    async def cleanup_old_messages(days: int = 30) -> int:
        """
        Удаляет старые сообщения.
        Возвращает количество удалённых.
        """
        def cleanup():
            cutoff = timezone.now() - timedelta(days=days)
            deleted, _ = ScheduledMessage.objects.filter(
                status__in=['sent', 'cancelled', 'failed'],
                updated_at__lt=cutoff,
            ).delete()
            return deleted
        
        return await sync_to_async(cleanup)()
