"""
Сервис рассылки сообщений
"""
import asyncio
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

from telegram import Bot
from telegram.error import TelegramError, Forbidden, BadRequest
from asgiref.sync import sync_to_async
from django.utils import timezone
from django.conf import settings

from ..config import TELEGRAM_LIMITS, BROADCAST_LIMITS
from ..models import BroadcastLog, ScheduledMessage

logger = logging.getLogger(__name__)


class BroadcastService:
    """Сервис для массовой рассылки сообщений"""
    
    def __init__(self, bot_token: str = None):
        from ..config import BOT_TOKEN
        self.bot_token = bot_token or BOT_TOKEN
        self._bot: Optional[Bot] = None
    
    @property
    def bot(self) -> Bot:
        if not self._bot:
            self._bot = Bot(token=self.bot_token)
        return self._bot
    
    async def send_to_user(
        self,
        telegram_id: str,
        text: str,
        parse_mode: str = 'Markdown',
        disable_preview: bool = True,
        reply_markup=None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Отправляет сообщение одному пользователю.
        Возвращает (success, error_message).
        """
        try:
            await self.bot.send_message(
                chat_id=telegram_id,
                text=text,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_preview,
                reply_markup=reply_markup,
            )
            return True, None
        except Forbidden as e:
            # Пользователь заблокировал бота
            logger.warning(f"User {telegram_id} blocked the bot: {e}")
            return False, 'blocked'
        except BadRequest as e:
            # Неверный chat_id или другая ошибка
            logger.warning(f"Bad request for {telegram_id}: {e}")
            return False, str(e)
        except TelegramError as e:
            logger.error(f"Telegram error for {telegram_id}: {e}")
            return False, str(e)
        except Exception as e:
            logger.error(f"Unexpected error for {telegram_id}: {e}")
            return False, str(e)
    
    async def broadcast_to_users(
        self,
        telegram_ids: List[str],
        text: str,
        teacher_id: int = None,
        message_type: str = 'custom',
        parse_mode: str = 'Markdown',
    ) -> Dict[str, Any]:
        """
        Массовая рассылка сообщений.
        Возвращает статистику: sent_count, failed_count, errors.
        """
        if not telegram_ids:
            return {'sent_count': 0, 'failed_count': 0, 'errors': []}
        
        # Ограничиваем количество получателей
        if len(telegram_ids) > BROADCAST_LIMITS['recipients_per_broadcast']:
            telegram_ids = telegram_ids[:BROADCAST_LIMITS['recipients_per_broadcast']]
            logger.warning(f"Broadcast truncated to {BROADCAST_LIMITS['recipients_per_broadcast']} recipients")
        
        # Создаём лог рассылки
        log = None
        if teacher_id:
            def create_log():
                from django.contrib.auth import get_user_model
                User = get_user_model()
                teacher = User.objects.get(id=teacher_id)
                return BroadcastLog.objects.create(
                    teacher=teacher,
                    message_type=message_type,
                    content_preview=text[:200],
                    target_count=len(telegram_ids),
                )
            log = await sync_to_async(create_log)()
        
        sent_count = 0
        failed_count = 0
        errors = []
        
        # Отправляем с задержкой для соблюдения лимитов Telegram
        delay_ms = TELEGRAM_LIMITS['bulk_delay_ms']
        
        for telegram_id in telegram_ids:
            success, error = await self.send_to_user(
                telegram_id=telegram_id,
                text=text,
                parse_mode=parse_mode,
            )
            
            if success:
                sent_count += 1
            else:
                failed_count += 1
                if error and error != 'blocked':
                    errors.append({'telegram_id': telegram_id, 'error': error})
            
            # Задержка между сообщениями
            if delay_ms > 0:
                await asyncio.sleep(delay_ms / 1000)
        
        # Обновляем лог
        if log:
            await sync_to_async(log.complete)(sent_count, failed_count)
        
        return {
            'sent_count': sent_count,
            'failed_count': failed_count,
            'errors': errors[:10],  # Ограничиваем количество ошибок в ответе
        }
    
    async def send_to_groups(
        self,
        group_ids: List[int],
        text: str,
        teacher_id: int = None,
        message_type: str = 'custom',
    ) -> Dict[str, Any]:
        """
        Рассылка по группам - отправляет всем ученикам групп.
        """
        from schedule.models import Group
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        def get_recipients():
            # Получаем уникальных учеников из всех групп
            students = User.objects.filter(
                enrolled_groups__id__in=group_ids,
                is_active=True,
                notification_consent=True,  # Только с согласием
                telegram_id__isnull=False,
            ).exclude(
                telegram_id=''
            ).distinct().values_list('telegram_id', flat=True)
            return list(students)
        
        telegram_ids = await sync_to_async(get_recipients)()
        
        return await self.broadcast_to_users(
            telegram_ids=telegram_ids,
            text=text,
            teacher_id=teacher_id,
            message_type=message_type,
        )
    
    async def send_to_students(
        self,
        student_ids: List[int],
        text: str,
        teacher_id: int = None,
        message_type: str = 'custom',
    ) -> Dict[str, Any]:
        """
        Рассылка конкретным ученикам.
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        def get_recipients():
            students = User.objects.filter(
                id__in=student_ids,
                is_active=True,
                notification_consent=True,
                telegram_id__isnull=False,
            ).exclude(
                telegram_id=''
            ).values_list('telegram_id', flat=True)
            return list(students)
        
        telegram_ids = await sync_to_async(get_recipients)()
        
        return await self.broadcast_to_users(
            telegram_ids=telegram_ids,
            text=text,
            teacher_id=teacher_id,
            message_type=message_type,
        )


async def process_scheduled_messages():
    """
    Обрабатывает запланированные сообщения.
    Вызывается периодически через Celery.
    """
    now = timezone.now()
    
    def get_pending_messages():
        return list(
            ScheduledMessage.objects.filter(
                status='pending',
                scheduled_at__lte=now,
            ).select_related('teacher').prefetch_related('target_groups', 'target_students')[:10]
        )
    
    messages = await sync_to_async(get_pending_messages)()
    
    if not messages:
        return
    
    service = BroadcastService()
    
    for msg in messages:
        try:
            await sync_to_async(msg.mark_sending)()
            
            # Собираем получателей
            def get_recipients():
                telegram_ids = set()
                
                # Из групп
                for group in msg.target_groups.all():
                    for student in group.students.filter(
                        is_active=True,
                        notification_consent=True,
                        telegram_id__isnull=False,
                    ).exclude(telegram_id=''):
                        telegram_ids.add(student.telegram_id)
                
                # Индивидуальные
                for student in msg.target_students.filter(
                    is_active=True,
                    notification_consent=True,
                    telegram_id__isnull=False,
                ).exclude(telegram_id=''):
                    telegram_ids.add(student.telegram_id)
                
                return list(telegram_ids)
            
            recipients = await sync_to_async(get_recipients)()
            
            if not recipients:
                await sync_to_async(msg.mark_sent)(0, 0)
                continue
            
            # Обновляем счётчик получателей
            msg.recipients_count = len(recipients)
            await sync_to_async(msg.save)(update_fields=['recipients_count'])
            
            # Отправляем
            result = await service.broadcast_to_users(
                telegram_ids=recipients,
                text=msg.content,
                teacher_id=msg.teacher_id,
                message_type=msg.message_type,
            )
            
            await sync_to_async(msg.mark_sent)(
                result['sent_count'],
                result['failed_count'],
            )
            
        except Exception as e:
            logger.error(f"Error processing scheduled message {msg.id}: {e}")
            msg.status = 'failed'
            msg.error_message = str(e)
            await sync_to_async(msg.save)(update_fields=['status', 'error_message'])
