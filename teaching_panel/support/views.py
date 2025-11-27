from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone

from .models import SupportTicket, SupportMessage, QuickSupportResponse
from .serializers import (
    SupportTicketSerializer,
    SupportTicketCreateSerializer,
    SupportMessageSerializer,
    QuickSupportResponseSerializer
)


class SupportTicketViewSet(viewsets.ModelViewSet):
    """API для работы с тикетами поддержки"""
    
    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return [IsAuthenticated()]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return SupportTicketCreateSerializer
        return SupportTicketSerializer
    
    def get_queryset(self):
        user = self.request.user
        
        if not user.is_authenticated:
            return SupportTicket.objects.none()
        
        # Админы и учителя видят все тикеты
        if user.role in ['admin', 'teacher']:
            return SupportTicket.objects.all().order_by('-created_at')
        
        # Обычные пользователи видят только свои
        return SupportTicket.objects.filter(user=user).order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def add_message(self, request, pk=None):
        """Добавить сообщение к тикету"""
        ticket = self.get_object()
        message_text = request.data.get('message', '').strip()
        
        if not message_text:
            return Response(
                {'detail': 'Сообщение не может быть пустым'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Определяем, это ответ от поддержки или от пользователя
        is_staff_reply = request.user.role in ['admin', 'teacher']
        
        message = SupportMessage.objects.create(
            ticket=ticket,
            author=request.user,
            message=message_text,
            is_staff_reply=is_staff_reply,
            read_by_staff=is_staff_reply,  # Если пишет поддержка, сразу помечаем как прочитанное
            read_by_user=not is_staff_reply  # Если пишет пользователь, он уже прочитал
        )
        
        # Обновляем статус тикета
        if is_staff_reply:
            ticket.status = 'waiting_user'
        else:
            if ticket.status == 'waiting_user':
                ticket.status = 'in_progress'
        
        ticket.save()
        
        # Если это ответ пользователя (не staff), уведомляем админов
        if not message.is_staff_reply:
            _notify_admins_new_message(ticket, message)
        
        serializer = SupportMessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Пометить все сообщения как прочитанные"""
        ticket = self.get_object()
        is_staff = request.user.role in ['admin', 'teacher']
        
        if is_staff:
            ticket.messages.filter(read_by_staff=False).update(read_by_staff=True)
        else:
            ticket.messages.filter(read_by_user=False).update(read_by_user=True)
        
        return Response({'detail': 'Отмечено как прочитанное'})
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Пометить тикет как решённый"""
        ticket = self.get_object()
        
        # Только поддержка может закрывать тикеты
        if request.user.role not in ['admin', 'teacher']:
            return Response(
                {'detail': 'Недостаточно прав'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        ticket.mark_resolved()
        
        serializer = self.get_serializer(ticket)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def reopen(self, request, pk=None):
        """Переоткрыть тикет"""
        ticket = self.get_object()
        ticket.status = 'in_progress'
        ticket.resolved_at = None
        ticket.save()
        
        serializer = self.get_serializer(ticket)
        return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_quick_responses(request):
    """Получить список быстрых ответов"""
    if request.user.role not in ['admin', 'teacher']:
        return Response(
            {'detail': 'Доступно только для поддержки'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    responses = QuickSupportResponse.objects.filter(is_active=True)
    serializer = QuickSupportResponseSerializer(responses, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_unread_count(request):
    """Получить количество непрочитанных сообщений поддержки"""
    user = request.user
    
    if user.role in ['admin', 'teacher']:
        # Для админов - новые тикеты и непрочитанные сообщения
        new_tickets = SupportTicket.objects.filter(status='new').count()
        unread_messages = SupportMessage.objects.filter(
            is_staff_reply=False,
            read_by_staff=False
        ).count()
        
        return Response({
            'new_tickets': new_tickets,
            'unread_messages': unread_messages,
            'total': new_tickets + unread_messages
        })
    else:
        # Для пользователей - непрочитанные ответы от поддержки
        unread = SupportMessage.objects.filter(
            ticket__user=user,
            is_staff_reply=True,
            read_by_user=False
        ).count()
        
        return Response({'unread': unread})


def _notify_admins_new_message(ticket, message):
    """Уведомление админов о новом сообщении от пользователя"""
    import os
    import requests
    from accounts.models import CustomUser
    
    token = os.getenv('SUPPORT_BOT_TOKEN')
    if not token:
        return
    
    # Получаем админов с Telegram, которым назначен этот тикет (или всех, если не назначен)
    if ticket.assigned_to and ticket.assigned_to.telegram_id:
        admins = [ticket.assigned_to]
    else:
        admins = CustomUser.objects.filter(is_staff=True, telegram_id__isnull=False)
    
    if not admins:
        return
    
    user_info = message.ticket.user.get_full_name() if message.ticket.user else 'Пользователь'
    
    text = (
        f"💬 *Новое сообщение в тикете #{ticket.id}*\n\n"
        f"📝 *Тема:* {ticket.subject}\n"
        f"👤 *От:* {user_info}\n"
        f"💌 *Сообщение:*\n{message.message[:300]}{'...' if len(message.message) > 300 else ''}\n\n"
        f"Для ответа: /view\\_{ticket.id}"
    )
    
    for admin in admins:
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            data = {
                'chat_id': admin.telegram_id,
                'text': text,
                'parse_mode': 'Markdown'
            }
            requests.post(url, json=data, timeout=5)
        except Exception as e:
            print(f"Не удалось отправить уведомление: {e}")
