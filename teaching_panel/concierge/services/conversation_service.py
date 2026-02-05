"""
ConversationService — главный сервис обработки диалогов

Отвечает за:
- Создание новых диалогов
- Обработку входящих сообщений
- Pipeline: User -> AI -> Action/Escalate
- Эскалацию к оператору
"""

import logging
from typing import Optional
from django.utils import timezone
from django.db import transaction
from asgiref.sync import sync_to_async

from ..models import Conversation, Message

logger = logging.getLogger(__name__)


class ConversationService:
    """
    Главный сервис для работы с диалогами.
    
    Пример использования:
    
        service = ConversationService()
        
        # Создать диалог
        conversation = await service.create_conversation(
            user=request.user,
            page_url='/payments',
            page_title='Оплата'
        )
        
        # Обработать сообщение пользователя
        response = await service.process_user_message(
            conversation_id=conversation.id,
            content="Не могу оплатить подписку"
        )
    """
    
    # Максимум попыток AI уточнить перед эскалацией
    MAX_AI_RETRY_BEFORE_ESCALATE = 2
    
    # Таймаут ожидания ответа оператора (минуты)
    HUMAN_RESPONSE_REMINDER_MINUTES = 5
    
    async def create_conversation(
        self,
        user,
        page_url: str = '',
        page_title: str = '',
        user_agent: str = '',
        client_info: dict = None,
    ) -> Conversation:
        """
        Создать новый диалог.
        
        Args:
            user: Авторизованный пользователь
            page_url: URL страницы, откуда открыт виджет
            page_title: Название страницы
            user_agent: User-Agent браузера
            client_info: {browser, os, screen_resolution, timezone}
        
        Returns:
            Conversation: Созданный диалог
        """
        # Собираем контекст пользователя для AI
        user_context = await self._build_user_context(user)
        
        conversation = await sync_to_async(Conversation.objects.create)(
            user=user,
            page_url=page_url,
            page_title=page_title,
            user_agent=user_agent,
            client_info=client_info or {},
            user_context=user_context,
        )
        
        logger.info(f"Created conversation {conversation.id} for user {user.email}")
        
        # Отправляем приветственное сообщение
        await self._send_greeting(conversation)
        
        return conversation
    
    async def process_user_message(
        self,
        conversation_id: int,
        content: str,
        content_type: str = 'text',
        attachment_url: str = '',
        attachment_meta: dict = None,
    ) -> Message:
        """
        Обработать сообщение от пользователя.
        
        Pipeline:
        1. Сохранить сообщение в БД
        2. Определить язык (если первое сообщение)
        3. Если AI_MODE:
           - RAG поиск по базе знаний
           - AI принимает решение: ответить / действие / эскалация
        4. Если HUMAN_MODE:
           - Переслать в Telegram
        
        Args:
            conversation_id: ID диалога
            content: Текст сообщения
            content_type: text/image/voice/file
            attachment_url: URL вложения (если есть)
            attachment_meta: Метаданные вложения
        
        Returns:
            Message: Ответное сообщение (от AI или системное)
        """
        from .ai_service import AIService
        from .telegram_bridge import TelegramBridge
        
        conversation = await sync_to_async(
            Conversation.objects.select_related('user').get
        )(id=conversation_id)
        
        # 1. Сохраняем сообщение пользователя
        user_message = await self._save_message(
            conversation=conversation,
            sender_type=Message.SenderType.USER,
            sender_user=conversation.user,
            content=content,
            content_type=content_type,
            attachment_url=attachment_url,
            attachment_meta=attachment_meta or {},
        )
        
        # Обновляем время последнего сообщения
        conversation.last_user_message_at = timezone.now()
        await sync_to_async(conversation.save)(update_fields=['last_user_message_at', 'updated_at'])
        
        # 2. Определяем язык по первому сообщению
        if conversation.messages.count() <= 2:  # greeting + первое сообщение
            language = await self._detect_language(content)
            if language != conversation.language:
                conversation.language = language
                await sync_to_async(conversation.save)(update_fields=['language'])
        
        # 3. Обработка в зависимости от статуса
        if conversation.status == Conversation.Status.HUMAN_MODE:
            # Уже подключён человек — форвардим в Telegram
            await TelegramBridge.forward_user_message(conversation, user_message)
            return user_message  # Ответ придёт асинхронно
        
        # 4. AI Pipeline
        history = await self._get_recent_history(conversation, limit=10)
        
        ai_response = await AIService.process(
            conversation=conversation,
            message=user_message,
            history=history,
        )
        
        # 5. Обрабатываем решение AI
        if ai_response.decision == 'answer':
            return await self._handle_ai_answer(conversation, ai_response)
        
        elif ai_response.decision == 'clarify':
            return await self._handle_ai_clarify(conversation, ai_response)
        
        elif ai_response.decision == 'action':
            return await self._handle_ai_action(conversation, user_message, ai_response)
        
        elif ai_response.decision == 'escalate':
            return await self._handle_escalation(conversation, ai_response.reason)
        
        else:
            # Неизвестное решение — эскалируем
            logger.warning(f"Unknown AI decision: {ai_response.decision}")
            return await self._handle_escalation(conversation, "AI returned unknown decision")
    
    async def process_admin_message(
        self,
        conversation_id: int,
        admin_user,
        content: str,
        telegram_message_id: int = None,
    ) -> Message:
        """
        Обработать сообщение от оператора (из Telegram).
        
        Args:
            conversation_id: ID диалога
            admin_user: Пользователь-админ
            content: Текст сообщения
            telegram_message_id: ID сообщения в Telegram
        
        Returns:
            Message: Сохранённое сообщение
        """
        conversation = await sync_to_async(Conversation.objects.get)(id=conversation_id)
        
        message = await self._save_message(
            conversation=conversation,
            sender_type=Message.SenderType.ADMIN,
            sender_user=admin_user,
            content=content,
            telegram_message_id=telegram_message_id,
        )
        
        # Обновляем assigned_admin если ещё не назначен
        if not conversation.assigned_admin:
            conversation.assigned_admin = admin_user
            await sync_to_async(conversation.save)(update_fields=['assigned_admin'])
        
        conversation.last_admin_message_at = timezone.now()
        await sync_to_async(conversation.save)(update_fields=['last_admin_message_at', 'updated_at'])
        
        # TODO: Уведомить web-клиент через SSE/WebSocket
        
        logger.info(f"Admin {admin_user.email} replied to conversation {conversation_id}")
        
        return message
    
    # =========================================================================
    # Private methods
    # =========================================================================
    
    async def _build_user_context(self, user) -> dict:
        """Собрать контекст пользователя для AI"""
        context = {
            'role': user.role,
            'email': user.email,
            'name': user.get_full_name(),
        }
        
        # Добавляем информацию о подписке (если teacher)
        if user.role == 'teacher':
            try:
                subscription = await sync_to_async(
                    lambda: user.subscription if hasattr(user, 'subscription') else None
                )()
                if subscription:
                    context['subscription'] = {
                        'status': subscription.status,
                        'expires_at': subscription.expires_at.isoformat() if subscription.expires_at else None,
                    }
            except Exception:
                pass
        
        return context
    
    async def _send_greeting(self, conversation: Conversation) -> Message:
        """Отправить приветственное сообщение"""
        # Выбираем приветствие в зависимости от языка и контекста
        if conversation.page_title:
            greeting_ru = f"Привет! Я вижу, что вы на странице «{conversation.page_title}». Чем могу помочь?"
            greeting_en = f"Hi! I see you're on the «{conversation.page_title}» page. How can I help you?"
        else:
            greeting_ru = "Привет! Я AI-ассистент Lectio. Чем могу помочь?"
            greeting_en = "Hi! I'm Lectio AI assistant. How can I help you?"
        
        # По умолчанию русский
        greeting = greeting_ru if conversation.language == 'ru' else greeting_en
        
        return await self._save_message(
            conversation=conversation,
            sender_type=Message.SenderType.AI,
            content=greeting,
            ai_confidence=1.0,
        )
    
    async def _save_message(
        self,
        conversation: Conversation,
        sender_type: str,
        content: str,
        sender_user=None,
        content_type: str = 'text',
        attachment_url: str = '',
        attachment_meta: dict = None,
        ai_confidence: float = None,
        ai_sources: list = None,
        ai_model: str = '',
        telegram_message_id: int = None,
    ) -> Message:
        """Сохранить сообщение в БД"""
        message = await sync_to_async(Message.objects.create)(
            conversation=conversation,
            sender_type=sender_type,
            sender_user=sender_user,
            content=content,
            content_type=content_type,
            attachment_url=attachment_url,
            attachment_meta=attachment_meta or {},
            ai_confidence=ai_confidence,
            ai_sources=ai_sources or [],
            ai_model=ai_model,
            telegram_message_id=telegram_message_id,
        )
        
        # Инкрементируем счётчик AI сообщений
        if sender_type == Message.SenderType.AI:
            conversation.ai_messages_count += 1
            await sync_to_async(conversation.save)(update_fields=['ai_messages_count'])
        
        return message
    
    async def _get_recent_history(self, conversation: Conversation, limit: int = 10) -> list:
        """Получить последние сообщения для контекста AI"""
        messages = await sync_to_async(list)(
            conversation.messages.order_by('-created_at')[:limit]
        )
        return list(reversed(messages))
    
    async def _detect_language(self, text: str) -> str:
        """Определить язык сообщения"""
        # Простая эвристика: если больше кириллицы — русский
        cyrillic_count = sum(1 for char in text if '\u0400' <= char <= '\u04ff')
        latin_count = sum(1 for char in text if 'a' <= char.lower() <= 'z')
        
        if cyrillic_count > latin_count:
            return 'ru'
        elif latin_count > 0:
            return 'en'
        return 'ru'  # По умолчанию
    
    async def _handle_ai_answer(self, conversation: Conversation, ai_response) -> Message:
        """Обработать ответ AI"""
        return await self._save_message(
            conversation=conversation,
            sender_type=Message.SenderType.AI,
            content=ai_response.text,
            ai_confidence=ai_response.confidence,
            ai_sources=ai_response.sources,
            ai_model=ai_response.model,
        )
    
    async def _handle_ai_clarify(self, conversation: Conversation, ai_response) -> Message:
        """AI просит уточнить — увеличиваем счётчик попыток"""
        conversation.ai_retry_count += 1
        await sync_to_async(conversation.save)(update_fields=['ai_retry_count'])
        
        # Если превысили лимит — эскалируем
        if conversation.ai_retry_count >= self.MAX_AI_RETRY_BEFORE_ESCALATE:
            return await self._handle_escalation(
                conversation, 
                f"AI не смог помочь после {conversation.ai_retry_count} уточнений"
            )
        
        return await self._save_message(
            conversation=conversation,
            sender_type=Message.SenderType.AI,
            content=ai_response.text,
            ai_confidence=ai_response.confidence,
        )
    
    async def _handle_ai_action(self, conversation: Conversation, trigger_message: Message, ai_response) -> Message:
        """AI решил выполнить действие"""
        from .action_executor import ActionExecutor
        
        result = await ActionExecutor.execute(
            action_name=ai_response.action_name,
            conversation=conversation,
            trigger_message=trigger_message,
            params=ai_response.action_params,
        )
        
        # AI формирует ответ на основе результата
        from .ai_service import AIService
        
        follow_up = await AIService.generate_action_response(
            conversation=conversation,
            action_name=ai_response.action_name,
            action_result=result,
        )
        
        return await self._save_message(
            conversation=conversation,
            sender_type=Message.SenderType.AI,
            content=follow_up.text,
            ai_confidence=follow_up.confidence,
        )
    
    async def _handle_escalation(self, conversation: Conversation, reason: str) -> Message:
        """Эскалировать к человеку"""
        from .telegram_bridge import TelegramBridge
        
        # Меняем статус
        conversation.status = Conversation.Status.HUMAN_MODE
        conversation.ai_escalated_at = timezone.now()
        conversation.ai_escalation_reason = reason
        await sync_to_async(conversation.save)(
            update_fields=['status', 'ai_escalated_at', 'ai_escalation_reason', 'updated_at']
        )
        
        # Создаём топик в Telegram и уведомляем админов
        await TelegramBridge.create_support_thread(conversation)
        
        # Сообщение пользователю
        if conversation.language == 'en':
            message = "I'm connecting you with a support specialist. Please wait, we'll respond shortly."
        else:
            message = "Подключаю специалиста поддержки. Пожалуйста, подождите — мы скоро ответим."
        
        logger.info(f"Escalated conversation {conversation.id}: {reason}")
        
        return await self._save_message(
            conversation=conversation,
            sender_type=Message.SenderType.SYSTEM,
            content=message,
        )
