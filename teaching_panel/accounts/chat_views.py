from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count, Max
from django.utils import timezone
from .models import Chat, Message, MessageReadStatus, CustomUser
from .chat_serializers import ChatSerializer, MessageSerializer, MessageReadStatusSerializer, UserUsernameSerializer


def _tenant_user_ids(request):
    """Возвращает список ID пользователей текущего тенанта или None если тенант не определён."""
    tenant = getattr(request, 'tenant', None)
    if tenant:
        from tenants.models import TenantMembership
        return list(TenantMembership.objects.filter(
            tenant=tenant, is_active=True
        ).values_list('user_id', flat=True))
    return None


class ChatViewSet(viewsets.ModelViewSet):
    """API для управления чатами"""
    
    permission_classes = [IsAuthenticated]
    serializer_class = ChatSerializer
    
    def get_queryset(self):
        """Возвращает чаты, в которых участвует текущий пользователь"""
        return Chat.objects.filter(
            participants=self.request.user
        ).prefetch_related('participants', 'messages').distinct()
    
    @action(detail=False, methods=['post'])
    def create_private(self, request):
        """Создать личный чат с пользователем"""
        other_user_id = request.data.get('user_id')
        
        if not other_user_id:
            return Response({'error': 'user_id обязателен'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            other_user = CustomUser.objects.get(id=other_user_id)
        except CustomUser.DoesNotExist:
            return Response({'error': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)
        
        # Проверка: пользователь должен быть в том же тенанте
        tenant_ids = _tenant_user_ids(request)
        if tenant_ids is not None and other_user.id not in tenant_ids:
            return Response({'error': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)
        
        # Проверяем, есть ли уже личный чат между этими пользователями
        existing_chat = Chat.objects.filter(
            chat_type='private',
            participants=request.user
        ).filter(
            participants=other_user
        ).first()
        
        if existing_chat:
            serializer = self.get_serializer(existing_chat)
            return Response(serializer.data)
        
        # Создаем новый чат
        chat = Chat.objects.create(
            chat_type='private',
            created_by=request.user
        )
        chat.participants.add(request.user, other_user)
        
        serializer = self.get_serializer(chat)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def create_group(self, request):
        """Создать групповой чат (только для учителей)"""
        if request.user.role != 'teacher':
            return Response({'error': 'Только учителя могут создавать групповые чаты'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        name = request.data.get('name')
        participant_ids = request.data.get('participant_ids', [])
        group_id = request.data.get('group_id')
        
        if not name:
            return Response({'error': 'name обязателен'}, status=status.HTTP_400_BAD_REQUEST)
        
        chat = Chat.objects.create(
            name=name,
            chat_type='group',
            created_by=request.user,
            group_id=group_id if group_id else None
        )
        
        # Добавляем участников (только из того же тенанта)
        if participant_ids:
            tenant_ids = _tenant_user_ids(request)
            if tenant_ids is not None:
                participant_ids = [pid for pid in participant_ids if int(pid) in tenant_ids]
            chat.participants.set(participant_ids)
        
        # Добавляем создателя
        chat.participants.add(request.user)
        
        serializer = self.get_serializer(chat)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def add_participants(self, request, pk=None):
        """Добавить участников в групповой чат"""
        chat = self.get_object()
        
        if chat.chat_type != 'group':
            return Response({'error': 'Можно добавлять участников только в групповые чаты'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        if chat.created_by != request.user:
            return Response({'error': 'Только создатель может добавлять участников'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        participant_ids = request.data.get('participant_ids', [])
        
        if not participant_ids:
            return Response({'error': 'participant_ids обязателен'}, status=status.HTTP_400_BAD_REQUEST)
        
        users = CustomUser.objects.filter(id__in=participant_ids)
        # Фильтр по тенанту
        tenant_ids = _tenant_user_ids(request)
        if tenant_ids is not None:
            users = users.filter(id__in=tenant_ids)
        chat.participants.add(*users)
        
        serializer = self.get_serializer(chat)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def remove_participant(self, request, pk=None):
        """Удалить участника из группового чата"""
        chat = self.get_object()
        
        if chat.chat_type != 'group':
            return Response({'error': 'Можно удалять участников только из групповых чатов'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        if chat.created_by != request.user:
            return Response({'error': 'Только создатель может удалять участников'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response({'error': 'user_id обязателен'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = CustomUser.objects.get(id=user_id)
            chat.participants.remove(user)
        except CustomUser.DoesNotExist:
            return Response({'error': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = self.get_serializer(chat)
        return Response(serializer.data)


class MessageViewSet(viewsets.ModelViewSet):
    """API для управления сообщениями"""
    
    permission_classes = [IsAuthenticated]
    serializer_class = MessageSerializer
    
    def get_queryset(self):
        """Возвращает сообщения из чатов пользователя"""
        chat_id = self.request.query_params.get('chat_id')
        
        queryset = Message.objects.filter(
            chat__participants=self.request.user
        ).select_related('sender', 'chat')
        
        if chat_id:
            queryset = queryset.filter(chat_id=chat_id)
        
        return queryset.order_by('created_at')
    
    def perform_create(self, serializer):
        """Создать сообщение и статусы прочтения для всех участников"""
        message = serializer.save(sender=self.request.user)
        
        # Создаем статусы прочтения для всех участников чата
        chat = message.chat
        for participant in chat.participants.all():
            MessageReadStatus.objects.create(
                message=message,
                user=participant,
                is_read=(participant == self.request.user)  # Отправитель автоматически прочитал
            )
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Отметить сообщение как прочитанное"""
        message = self.get_object()
        
        read_status, created = MessageReadStatus.objects.get_or_create(
            message=message,
            user=request.user,
            defaults={'is_read': True, 'read_at': timezone.now()}
        )
        
        if not created and not read_status.is_read:
            read_status.is_read = True
            read_status.read_at = timezone.now()
            read_status.save()
        
        return Response({'status': 'success'})
    
    @action(detail=False, methods=['post'])
    def mark_chat_as_read(self, request):
        """Отметить все сообщения в чате как прочитанные"""
        chat_id = request.data.get('chat_id')
        
        if not chat_id:
            return Response({'error': 'chat_id обязателен'}, status=status.HTTP_400_BAD_REQUEST)
        
        MessageReadStatus.objects.filter(
            message__chat_id=chat_id,
            user=request.user,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())
        
        return Response({'status': 'success'})


class UserSearchViewSet(viewsets.ReadOnlyModelViewSet):
    """API для поиска пользователей по короткому имени"""
    
    permission_classes = [IsAuthenticated]
    serializer_class = UserUsernameSerializer
    
    def get_queryset(self):
        query = self.request.query_params.get('q', '')
        
        if not query:
            return CustomUser.objects.none()
        
        qs = CustomUser.objects.filter(
            Q(username_handle__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        ).exclude(id=self.request.user.id)
        
        # Фильтрация по тенанту: ищем только среди участников тенанта
        tenant_ids = _tenant_user_ids(self.request)
        if tenant_ids is not None:
            qs = qs.filter(id__in=tenant_ids)
        
        return qs[:20]
