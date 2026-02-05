"""
TelegramBridge — синхронизация с Telegram

Отвечает за:
- Создание топиков в группе поддержки
- Пересылку сообщений User -> Telegram
- Обработку ответов Admin -> Web
- Уведомления о новых диалогах
"""

import logging
import os
import httpx
from typing import Optional
from django.conf import settings
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


class TelegramBridge:
    """
    Мост между Web-чатом и Telegram.
    
    Использует Telegram Bot API для:
    - Отправки сообщений в группу поддержки
    - Создания топиков (threads) для каждого диалога
    - Получения ответов через webhook
    """
    
    # Таймаут для API запросов
    TIMEOUT_SECONDS = 10
    
    @classmethod
    def _get_bot_token(cls) -> Optional[str]:
        """Получить токен бота"""
        return os.getenv('SUPPORT_BOT_TOKEN') or os.getenv('CONCIERGE_BOT_TOKEN')
    
    @classmethod
    def _get_chat_id(cls) -> Optional[str]:
        """Получить ID чата/группы поддержки"""
        return os.getenv('SUPPORT_NOTIFICATIONS_CHAT_ID') or os.getenv('CONCIERGE_CHAT_ID')
    
    @classmethod
    async def create_support_thread(cls, conversation) -> Optional[int]:
        """
        Создать топик (thread) в группе поддержки для нового диалога.
        
        Args:
            conversation: Объект Conversation
        
        Returns:
            int: ID созданного топика или None
        """
        token = cls._get_bot_token()
        chat_id = cls._get_chat_id()
        
        if not token or not chat_id:
            logger.warning("Telegram bot not configured, skipping thread creation")
            return None
        
        # Формируем название топика
        user_name = conversation.user.get_full_name() or conversation.user.email
        thread_name = f"#{conversation.id} {user_name}"[:128]  # Лимит Telegram
        
        try:
            async with httpx.AsyncClient(timeout=cls.TIMEOUT_SECONDS) as client:
                # Создаём топик (только для supergroup с topics enabled)
                response = await client.post(
                    f'https://api.telegram.org/bot{token}/createForumTopic',
                    json={
                        'chat_id': chat_id,
                        'name': thread_name,
                        'icon_custom_emoji_id': '5368324170671202286',  # 💬 emoji
                    },
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('ok'):
                        thread_id = data['result']['message_thread_id']
                        
                        # Сохраняем thread_id
                        conversation.telegram_thread_id = thread_id
                        await sync_to_async(conversation.save)(update_fields=['telegram_thread_id'])
                        
                        # Отправляем информацию о диалоге в топик
                        await cls._send_conversation_info(conversation, thread_id)
                        
                        logger.info(f"Created Telegram thread {thread_id} for conversation {conversation.id}")
                        return thread_id
                
                # Если топики не поддерживаются — отправляем в общий чат
                logger.info("Forum topics not available, sending to main chat")
                await cls._send_to_main_chat(conversation)
                return None
                
        except Exception as e:
            logger.error(f"Failed to create Telegram thread: {e}")
            # Fallback: отправляем в общий чат
            await cls._send_to_main_chat(conversation)
            return None
    
    @classmethod
    async def forward_user_message(cls, conversation, message) -> bool:
        """
        Переслать сообщение пользователя в Telegram.
        
        Args:
            conversation: Объект Conversation
            message: Объект Message
        
        Returns:
            bool: Успешно ли отправлено
        """
        token = cls._get_bot_token()
        chat_id = cls._get_chat_id()
        
        if not token or not chat_id:
            logger.warning("Telegram bot not configured")
            return False
        
        # Формируем текст
        text = f"💬 *Пользователь:*\n{message.content}"
        
        try:
            async with httpx.AsyncClient(timeout=cls.TIMEOUT_SECONDS) as client:
                payload = {
                    'chat_id': chat_id,
                    'text': text,
                    'parse_mode': 'Markdown',
                }
                
                # Если есть топик — отправляем в него
                if conversation.telegram_thread_id:
                    payload['message_thread_id'] = conversation.telegram_thread_id
                
                response = await client.post(
                    f'https://api.telegram.org/bot{token}/sendMessage',
                    json=payload,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('ok'):
                        # Сохраняем ID сообщения в Telegram
                        message.telegram_message_id = data['result']['message_id']
                        await sync_to_async(message.save)(update_fields=['telegram_message_id'])
                        return True
                
                logger.error(f"Failed to send message to Telegram: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending message to Telegram: {e}")
            return False
    
    @classmethod
    async def send_reminder(cls, conversation) -> bool:
        """
        Отправить напоминание оператору о неотвеченном диалоге.
        
        Args:
            conversation: Объект Conversation
        
        Returns:
            bool: Успешно ли отправлено
        """
        token = cls._get_bot_token()
        chat_id = cls._get_chat_id()
        
        if not token or not chat_id:
            return False
        
        # Вычисляем время ожидания
        from django.utils import timezone
        wait_minutes = 0
        if conversation.last_user_message_at:
            delta = timezone.now() - conversation.last_user_message_at
            wait_minutes = int(delta.total_seconds() / 60)
        
        text = (
            f"⏰ *Напоминание*\n\n"
            f"Диалог #{conversation.id} ожидает ответа уже {wait_minutes} мин.\n"
            f"Пользователь: {conversation.user.email}"
        )
        
        try:
            async with httpx.AsyncClient(timeout=cls.TIMEOUT_SECONDS) as client:
                payload = {
                    'chat_id': chat_id,
                    'text': text,
                    'parse_mode': 'Markdown',
                }
                
                if conversation.telegram_thread_id:
                    payload['message_thread_id'] = conversation.telegram_thread_id
                
                response = await client.post(
                    f'https://api.telegram.org/bot{token}/sendMessage',
                    json=payload,
                )
                
                return response.status_code == 200
                
        except Exception as e:
            logger.error(f"Error sending reminder: {e}")
            return False
    
    # =========================================================================
    # Private methods
    # =========================================================================
    
    @classmethod
    async def _send_conversation_info(cls, conversation, thread_id: int):
        """Отправить информацию о диалоге в топик"""
        token = cls._get_bot_token()
        chat_id = cls._get_chat_id()
        
        # Контекст пользователя
        ctx = conversation.user_context
        role = ctx.get('role', 'unknown')
        sub_status = ctx.get('subscription', {}).get('status', 'unknown')
        
        text = (
            f"🆕 *Новый диалог #{conversation.id}*\n\n"
            f"👤 *Пользователь:* {conversation.user.get_full_name() or conversation.user.email}\n"
            f"📧 *Email:* {conversation.user.email}\n"
            f"🎭 *Роль:* {role}\n"
            f"💳 *Подписка:* {sub_status}\n"
            f"📍 *Страница:* {conversation.page_title or conversation.page_url or 'неизвестно'}\n\n"
            f"⚠️ *Причина эскалации:*\n{conversation.ai_escalation_reason or 'Не указана'}\n\n"
            f"Чтобы ответить — просто напишите сообщение в этот топик."
        )
        
        try:
            async with httpx.AsyncClient(timeout=cls.TIMEOUT_SECONDS) as client:
                await client.post(
                    f'https://api.telegram.org/bot{token}/sendMessage',
                    json={
                        'chat_id': chat_id,
                        'message_thread_id': thread_id,
                        'text': text,
                        'parse_mode': 'Markdown',
                    },
                )
        except Exception as e:
            logger.error(f"Failed to send conversation info: {e}")
    
    @classmethod
    async def _send_to_main_chat(cls, conversation):
        """Отправить в основной чат (без топиков)"""
        token = cls._get_bot_token()
        chat_id = cls._get_chat_id()
        
        if not token or not chat_id:
            return
        
        ctx = conversation.user_context
        role = ctx.get('role', 'unknown')
        
        # Получаем последние сообщения
        from ..models import Message
        messages = await sync_to_async(list)(
            conversation.messages.order_by('-created_at')[:5]
        )
        
        history = '\n'.join([
            f"{'👤' if m.sender_type == 'user' else '🤖'} {m.content[:200]}"
            for m in reversed(messages)
        ])
        
        text = (
            f"🆕 *Новый запрос в поддержку #{conversation.id}*\n\n"
            f"👤 {conversation.user.email} ({role})\n"
            f"📍 {conversation.page_title or 'Неизвестная страница'}\n\n"
            f"📝 *Диалог:*\n{history}\n\n"
            f"⚠️ *Причина эскалации:*\n{conversation.ai_escalation_reason or 'AI не справился'}\n\n"
            f"Ответить: /reply\\_{conversation.id} <текст>"
        )
        
        try:
            async with httpx.AsyncClient(timeout=cls.TIMEOUT_SECONDS) as client:
                await client.post(
                    f'https://api.telegram.org/bot{token}/sendMessage',
                    json={
                        'chat_id': chat_id,
                        'text': text,
                        'parse_mode': 'Markdown',
                    },
                )
        except Exception as e:
            logger.error(f"Failed to send to main chat: {e}")
