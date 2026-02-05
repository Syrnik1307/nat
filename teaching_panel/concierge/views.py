"""
API Views для Lectio Concierge
"""

import logging
import asyncio
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.pagination import CursorPagination
from django.http import StreamingHttpResponse
from django.utils import timezone
from asgiref.sync import async_to_sync

from .models import Conversation, Message, ActionDefinition
from .serializers import (
    ConversationSerializer,
    ConversationDetailSerializer,
    ConversationCreateSerializer,
    MessageSerializer,
    MessageCreateSerializer,
    ConversationRatingSerializer,
    ActionDefinitionSerializer,
)

logger = logging.getLogger(__name__)


class MessagePagination(CursorPagination):
    """Курсорная пагинация для сообщений"""
    page_size = 50
    ordering = '-created_at'
    cursor_query_param = 'cursor'


class ConversationViewSet(viewsets.ModelViewSet):
    """
    API для работы с диалогами.
    
    Endpoints:
    - POST /api/concierge/conversations/ — создать диалог
    - GET /api/concierge/conversations/ — список диалогов (свои)
    - GET /api/concierge/conversations/{id}/ — детали диалога
    - POST /api/concierge/conversations/{id}/messages/ — отправить сообщение
    - GET /api/concierge/conversations/{id}/messages/ — история сообщений
    - POST /api/concierge/conversations/{id}/rate/ — оценить диалог
    - POST /api/concierge/conversations/{id}/close/ — закрыть диалог
    """
    
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        # Админы видят все диалоги
        if user.role == 'admin':
            return Conversation.objects.all().order_by('-updated_at')
        
        # Остальные — только свои
        return Conversation.objects.filter(user=user).order_by('-updated_at')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ConversationCreateSerializer
        if self.action == 'retrieve':
            return ConversationDetailSerializer
        return ConversationSerializer
    
    def create(self, request, *args, **kwargs):
        """Создать новый диалог"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        from .services.conversation_service import ConversationService
        
        service = ConversationService()
        
        # Запускаем async в sync контексте
        conversation = async_to_sync(service.create_conversation)(
            user=request.user,
            page_url=serializer.validated_data.get('page_url', ''),
            page_title=serializer.validated_data.get('page_title', ''),
            user_agent=serializer.validated_data.get('user_agent', ''),
            client_info=serializer.validated_data.get('client_info', {}),
        )
        
        return Response(
            ConversationDetailSerializer(conversation).data,
            status=status.HTTP_201_CREATED,
        )
    
    @action(detail=True, methods=['get', 'post'])
    def messages(self, request, pk=None):
        """Получить/отправить сообщения"""
        conversation = self.get_object()
        
        if request.method == 'GET':
            # Получить историю сообщений
            messages = conversation.messages.all().order_by('created_at')
            
            # Пагинация (простая, не курсорная для GET)
            page = self.paginate_queryset(messages)
            if page is not None:
                serializer = MessageSerializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = MessageSerializer(messages, many=True)
            return Response(serializer.data)
        
        else:  # POST
            # Отправить сообщение
            serializer = MessageCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            from .services.conversation_service import ConversationService
            
            service = ConversationService()
            
            response_message = async_to_sync(service.process_user_message)(
                conversation_id=conversation.id,
                content=serializer.validated_data['content'],
                content_type=serializer.validated_data.get('content_type', 'text'),
                attachment_url=serializer.validated_data.get('attachment_url', ''),
                attachment_meta=serializer.validated_data.get('attachment_meta', {}),
            )
            
            # Возвращаем все новые сообщения (user + AI response)
            new_messages = conversation.messages.filter(
                created_at__gte=response_message.created_at - timezone.timedelta(seconds=5)
            ).order_by('created_at')
            
            return Response(
                MessageSerializer(new_messages, many=True).data,
                status=status.HTTP_201_CREATED,
            )
    
    @action(detail=True, methods=['post'])
    def rate(self, request, pk=None):
        """Оценить диалог"""
        conversation = self.get_object()
        
        serializer = ConversationRatingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        conversation.user_rating = serializer.validated_data['rating']
        conversation.user_feedback = serializer.validated_data.get('feedback', '')
        conversation.save(update_fields=['user_rating', 'user_feedback', 'updated_at'])
        
        return Response({'detail': 'Спасибо за оценку!'})
    
    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Закрыть диалог"""
        conversation = self.get_object()
        conversation.close()
        
        return Response({'detail': 'Диалог закрыт'})
    
    @action(detail=True, methods=['post'])
    def escalate(self, request, pk=None):
        """Принудительно эскалировать к человеку"""
        conversation = self.get_object()
        
        if conversation.status != Conversation.Status.AI_MODE:
            return Response(
                {'detail': 'Диалог уже эскалирован или закрыт'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        from .services.conversation_service import ConversationService
        
        service = ConversationService()
        
        async_to_sync(service._handle_escalation)(
            conversation, 
            reason='Пользователь запросил оператора',
        )
        
        return Response({'detail': 'Оператор подключён'})
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Отметить все сообщения как прочитанные"""
        conversation = self.get_object()
        
        conversation.messages.filter(
            sender_type__in=['ai', 'admin', 'system'],
            read_at__isnull=True,
        ).update(read_at=timezone.now())
        
        return Response({'detail': 'Отмечено как прочитанное'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def available_actions(request, conversation_id):
    """Получить список доступных действий для диалога"""
    actions = ActionDefinition.objects.filter(is_active=True)
    serializer = ActionDefinitionSerializer(actions, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def execute_action(request, conversation_id, action_name):
    """Выполнить действие вручную"""
    try:
        conversation = Conversation.objects.get(id=conversation_id, user=request.user)
    except Conversation.DoesNotExist:
        return Response(
            {'detail': 'Диалог не найден'},
            status=status.HTTP_404_NOT_FOUND,
        )
    
    from .services.action_executor import ActionExecutor
    
    params = request.data.get('params', {})
    
    result = async_to_sync(ActionExecutor.execute)(
        action_name=action_name,
        conversation=conversation,
        params=params,
    )
    
    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def message_stream(request, conversation_id):
    """
    SSE endpoint для real-time обновлений.
    
    Пример использования:
        const eventSource = new EventSource('/api/concierge/conversations/123/stream/');
        eventSource.onmessage = (event) => {
            const message = JSON.parse(event.data);
            // Добавить сообщение в UI
        };
    """
    try:
        conversation = Conversation.objects.get(id=conversation_id)
        
        # Проверяем доступ
        if conversation.user_id != request.user.id and request.user.role != 'admin':
            return Response(
                {'detail': 'Доступ запрещён'},
                status=status.HTTP_403_FORBIDDEN,
            )
    except Conversation.DoesNotExist:
        return Response(
            {'detail': 'Диалог не найден'},
            status=status.HTTP_404_NOT_FOUND,
        )
    
    def event_stream():
        """Генератор SSE событий"""
        import time
        import json
        
        last_id = int(request.GET.get('last_id', 0))
        
        # Отправляем keepalive каждые 15 секунд
        last_keepalive = time.time()
        
        while True:
            # Проверяем новые сообщения
            new_messages = Message.objects.filter(
                conversation_id=conversation_id,
                id__gt=last_id,
            ).order_by('created_at')
            
            for msg in new_messages:
                data = {
                    'id': msg.id,
                    'sender_type': msg.sender_type,
                    'content': msg.content,
                    'content_type': msg.content_type,
                    'created_at': msg.created_at.isoformat(),
                }
                yield f"data: {json.dumps(data)}\n\n"
                last_id = msg.id
            
            # Keepalive
            if time.time() - last_keepalive > 15:
                yield f": keepalive\n\n"
                last_keepalive = time.time()
            
            time.sleep(0.5)
    
    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream',
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'  # Для nginx
    
    return response


# =========================================================================
# Admin API (для операторов из Telegram webhook)
# =========================================================================

@api_view(['POST'])
@permission_classes([])  # Проверка через secret token
def telegram_webhook(request):
    """
    Webhook для получения сообщений из Telegram.
    
    Вызывается Telegram Bot API при новых сообщениях.
    """
    import os
    import hashlib
    import hmac
    
    # Проверяем секрет (если настроен)
    secret = os.getenv('CONCIERGE_WEBHOOK_SECRET')
    if secret:
        # Telegram отправляет X-Telegram-Bot-Api-Secret-Token
        token = request.headers.get('X-Telegram-Bot-Api-Secret-Token', '')
        if not hmac.compare_digest(token, secret):
            logger.warning("Invalid webhook secret")
            return Response({'error': 'Invalid secret'}, status=status.HTTP_403_FORBIDDEN)
    
    update = request.data
    logger.info(f"Telegram webhook received: {update.get('update_id')}")
    
    # Обрабатываем сообщение
    message = update.get('message')
    if not message:
        return Response({'ok': True})
    
    thread_id = message.get('message_thread_id')
    text = message.get('text', '')
    from_user = message.get('from', {})
    telegram_id = from_user.get('id')
    
    if not thread_id or not text or not telegram_id:
        return Response({'ok': True})
    
    # Находим диалог по thread_id
    try:
        conversation = Conversation.objects.get(telegram_thread_id=thread_id)
    except Conversation.DoesNotExist:
        logger.warning(f"Conversation not found for thread {thread_id}")
        return Response({'ok': True})
    
    # Находим админа по telegram_id
    from accounts.models import CustomUser
    try:
        admin_user = CustomUser.objects.get(telegram_id=telegram_id, is_staff=True)
    except CustomUser.DoesNotExist:
        logger.warning(f"Admin not found for telegram_id {telegram_id}")
        return Response({'ok': True})
    
    # Сохраняем сообщение
    from .services.conversation_service import ConversationService
    
    service = ConversationService()
    async_to_sync(service.process_admin_message)(
        conversation_id=conversation.id,
        admin_user=admin_user,
        content=text,
        telegram_message_id=message.get('message_id'),
    )
    
    return Response({'ok': True})


@api_view(['POST'])
@permission_classes([IsAdminUser])
def reindex_knowledge_base(request):
    """Переиндексировать базу знаний (только для админов)"""
    from .services.knowledge_service import KnowledgeService
    
    stats = async_to_sync(KnowledgeService.index_all_documents)()
    
    return Response({
        'message': 'Индексация завершена',
        'stats': stats,
    })
