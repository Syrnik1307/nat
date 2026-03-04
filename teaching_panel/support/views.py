import os
import uuid
import mimetypes

from django.conf import settings
from django.http import FileResponse, Http404
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SupportTicket, SupportMessage, QuickSupportResponse
from accounts.telegram_utils import generate_link_code_for_user
from .serializers import (
    SupportTicketSerializer,
    SupportTicketCreateSerializer,
    SupportTicketListSerializer,
    SupportMessageSerializer,
    QuickSupportResponseSerializer
)
from .telegram_notifications import notify_admins_new_message

# Условный импорт для feature-flagged функциональности
try:
    from .models import SupportAttachment
    _HAS_ATTACHMENT = True
except ImportError:
    _HAS_ATTACHMENT = False


# ======================== Константы ========================

ALLOWED_MIME_TYPES = {
    'image/png', 'image/jpeg', 'image/gif', 'image/webp',
    'image/svg+xml', 'application/pdf',
}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_FILES_PER_TICKET = 10


class SupportTicketViewSet(viewsets.ModelViewSet):
    """API для работы с тикетами поддержки"""
    
    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return [IsAuthenticated()]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return SupportTicketCreateSerializer
        if self.action == 'list':
            return SupportTicketListSerializer
        return SupportTicketSerializer
    
    def get_queryset(self):
        user = self.request.user
        
        if not user.is_authenticated:
            return SupportTicket.objects.none()
        
        qs = SupportTicket.objects.all()

        # Только админы видят все тикеты (они - поддержка)
        if user.role != 'admin':
            qs = qs.filter(user=user)

        # Фильтры (для админ-панели)
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        priority_filter = self.request.query_params.get('priority')
        if priority_filter:
            qs = qs.filter(priority=priority_filter)

        assigned_filter = self.request.query_params.get('assigned_to')
        if assigned_filter == 'me':
            qs = qs.filter(assigned_to=user)
        elif assigned_filter == 'unassigned':
            qs = qs.filter(assigned_to__isnull=True)

        return qs.order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def add_message(self, request, pk=None):
        """Добавить сообщение к тикету"""
        ticket = self.get_object()
        message_text = request.data.get('message', '').strip()
        attachment_ids = request.data.get('attachment_ids', [])
        
        if not message_text and not attachment_ids:
            return Response(
                {'detail': 'Сообщение не может быть пустым'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Определяем, это ответ от поддержки или от пользователя
        # Только admin является поддержкой
        is_staff_reply = request.user.role == 'admin'
        
        message = SupportMessage.objects.create(
            ticket=ticket,
            author=request.user,
            message=message_text,
            is_staff_reply=is_staff_reply,
            read_by_staff=is_staff_reply,  # Если пишет поддержка, сразу помечаем как прочитанное
            read_by_user=not is_staff_reply  # Если пишет пользователь, он уже прочитал
        )

        # Привязываем вложения к сообщению
        if attachment_ids and _HAS_ATTACHMENT:
            SupportAttachment.objects.filter(
                id__in=attachment_ids,
                ticket__isnull=True,
                message__isnull=True,
            ).update(ticket=ticket, message=message)
        
        # Обновляем статус тикета
        if is_staff_reply:
            ticket.status = 'waiting_user'
            ticket.record_first_response()
        else:
            if ticket.status == 'waiting_user':
                ticket.status = 'in_progress'
        
        ticket.save()
        
        # Если это ответ пользователя (не staff), уведомляем админов
        if not message.is_staff_reply:
            notify_admins_new_message(ticket=ticket, message=message)
        
        serializer = SupportMessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Пометить все сообщения как прочитанные"""
        ticket = self.get_object()
        is_staff = request.user.role == 'admin'
        
        if is_staff:
            ticket.messages.filter(read_by_staff=False).update(read_by_staff=True)
        else:
            ticket.messages.filter(read_by_user=False).update(read_by_user=True)
        
        return Response({'detail': 'Отмечено как прочитанное'})
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Пометить тикет как решённый (могут и пользователь, и админ)"""
        ticket = self.get_object()
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

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """Назначить тикет на себя (только админы)"""
        if request.user.role != 'admin':
            return Response({'detail': 'Недостаточно прав'}, status=status.HTTP_403_FORBIDDEN)
        ticket = self.get_object()
        ticket.assigned_to = request.user
        if ticket.status == 'new':
            ticket.status = 'in_progress'
        ticket.save()
        serializer = self.get_serializer(ticket)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def set_priority(self, request, pk=None):
        """Изменить приоритет (только админы)"""
        if request.user.role != 'admin':
            return Response({'detail': 'Недостаточно прав'}, status=status.HTTP_403_FORBIDDEN)
        ticket = self.get_object()
        new_priority = request.data.get('priority')
        if new_priority not in dict(SupportTicket.PRIORITY_CHOICES):
            return Response({'detail': 'Неверный приоритет'}, status=status.HTTP_400_BAD_REQUEST)
        ticket.priority = new_priority
        ticket.save(update_fields=['priority'])
        serializer = self.get_serializer(ticket)
        return Response(serializer.data)


# ======================== File Attachments (SUPPORT_V2 only) ========================

class SupportAttachmentUploadView(APIView):
    """Загрузка файлов для тикетов поддержки.

    POST /api/support/attachments/upload/
    Принимает multipart/form-data с полем 'file'.
    Возвращает {id, url, original_name, size}.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        if not _HAS_ATTACHMENT:
            return Response(
                {'detail': 'Вложения не поддерживаются'},
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )

        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response({'detail': 'Файл не передан'}, status=status.HTTP_400_BAD_REQUEST)

        # Валидация размера
        if uploaded_file.size > MAX_FILE_SIZE:
            return Response(
                {'detail': f'Файл слишком большой. Максимум {MAX_FILE_SIZE // (1024*1024)} МБ'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Валидация типа
        content_type = uploaded_file.content_type or ''
        if content_type not in ALLOWED_MIME_TYPES:
            guessed, _ = mimetypes.guess_type(uploaded_file.name or '')
            if guessed not in ALLOWED_MIME_TYPES:
                return Response(
                    {'detail': 'Недопустимый тип файла. Разрешены: PNG, JPG, GIF, WebP, PDF'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            content_type = guessed

        # Сохранение на диск
        file_id = uuid.uuid4().hex
        ext = os.path.splitext(uploaded_file.name or '')[1].lower()[:10]
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'support_files')
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, f'{file_id}{ext}')

        with open(file_path, 'wb') as dst:
            for chunk in uploaded_file.chunks():
                dst.write(chunk)

        attachment = SupportAttachment.objects.create(
            id=file_id,
            uploaded_by=request.user,
            original_name=uploaded_file.name or 'file',
            mime_type=content_type,
            size=uploaded_file.size,
            local_path=file_path,
        )

        return Response({
            'id': attachment.id,
            'url': f'/api/support/attachments/{attachment.id}/',
            'original_name': attachment.original_name,
            'size': attachment.size,
        }, status=status.HTTP_201_CREATED)


class SupportAttachmentDownloadView(APIView):
    """Прокси для скачивания вложений.

    GET /api/support/attachments/<id>/
    Отдаёт файл с Content-Disposition: inline.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, attachment_id):
        if not _HAS_ATTACHMENT:
            raise Http404

        try:
            attachment = SupportAttachment.objects.get(id=attachment_id)
        except SupportAttachment.DoesNotExist:
            raise Http404

        # Проверка доступа: автор загрузки, владелец тикета или админ
        user = request.user
        can_access = (
            user.role == 'admin'
            or attachment.uploaded_by == user
            or (attachment.ticket and attachment.ticket.user == user)
        )
        if not can_access:
            return Response({'detail': 'Доступ запрещён'}, status=status.HTTP_403_FORBIDDEN)

        if not attachment.local_path or not os.path.exists(attachment.local_path):
            raise Http404

        return FileResponse(
            open(attachment.local_path, 'rb'),
            content_type=attachment.mime_type,
            filename=attachment.original_name,
        )


# ======================== Standalone endpoints ========================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_quick_responses(request):
    """Получить список быстрых ответов"""
    if request.user.role != 'admin':
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
    
    if user.role == 'admin':
        # Для админов-поддержки - новые тикеты и непрочитанные сообщения
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_telegram_support_link(request):
    """Вернуть deep-link на Telegram бота поддержки.

    - Если Telegram уже привязан, возвращаем start=support.
    - Если не привязан, генерируем одноразовый TelegramLinkCode и используем start=support_<CODE>.
    """
    import os
    # Используем отдельного бота поддержки, а не основного бота
    username = os.getenv('SUPPORT_BOT_USERNAME', '').lstrip('@').strip()
    if not username:
        # Fallback на основного бота если SUPPORT_BOT_USERNAME не настроен
        username = (getattr(settings, 'TELEGRAM_BOT_USERNAME', '') or '').lstrip('@').strip()
    
    if not username:
        return Response(
            {'detail': 'SUPPORT_BOT_USERNAME не настроен'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    user = request.user
    if getattr(user, 'telegram_verified', False) and getattr(user, 'telegram_id', None):
        start_param = 'support'
    else:
        code_obj = generate_link_code_for_user(user, ttl_minutes=10)
        start_param = f"support_{code_obj.code}"

    url = f"https://t.me/{username}?start={start_param}"
    return Response({'url': url, 'start': start_param})


# ============ Статус системы и Health ============

from .models import SystemStatus
from .serializers import SystemStatusSerializer


@api_view(['GET'])
@permission_classes([AllowAny])
def system_status(request):
    """Публичный статус системы для /status страницы"""
    status_obj = SystemStatus.get_current()
    serializer = SystemStatusSerializer(status_obj)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Health check для мониторинга.
    
    Проверяет:
    - База данных доступна
    - Redis доступен (если используется)
    """
    from django.db import connection
    from django.core.cache import cache
    import time
    
    health = {
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'checks': {}
    }
    
    # Проверка БД
    try:
        start = time.time()
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        health['checks']['database'] = {
            'status': 'ok',
            'latency_ms': round((time.time() - start) * 1000, 2)
        }
    except Exception as e:
        health['status'] = 'unhealthy'
        health['checks']['database'] = {
            'status': 'error',
            'error': str(e)
        }
    
    # Проверка Redis/Cache
    try:
        start = time.time()
        cache.set('health_check', 'ok', 10)
        result = cache.get('health_check')
        if result == 'ok':
            health['checks']['cache'] = {
                'status': 'ok',
                'latency_ms': round((time.time() - start) * 1000, 2)
            }
        else:
            health['checks']['cache'] = {'status': 'degraded'}
    except Exception as e:
        health['checks']['cache'] = {
            'status': 'skipped',
            'note': 'Cache not configured'
        }
    
    # Общий статус системы
    system = SystemStatus.get_current()
    health['system_status'] = system.status
    if system.status != 'operational':
        health['incident'] = {
            'title': system.incident_title,
            'message': system.message,
            'started_at': system.incident_started_at.isoformat() if system.incident_started_at else None
        }
    
    http_status = 200 if health['status'] == 'healthy' else 503
    return Response(health, status=http_status)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def support_stats(request):
    """Статистика поддержки для админов"""
    if request.user.role != 'admin':
        return Response({'detail': 'Доступ запрещён'}, status=status.HTTP_403_FORBIDDEN)
    
    from django.db.models import Count, Avg, F
    from datetime import timedelta
    
    now = timezone.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)
    
    # Общая статистика
    open_tickets = SupportTicket.objects.filter(status__in=['new', 'in_progress', 'waiting_user'])
    
    stats = {
        'open_total': open_tickets.count(),
        'by_priority': {
            item['priority']: item['count']
            for item in open_tickets.values('priority').annotate(count=Count('id'))
        },
        'by_status': {
            item['status']: item['count']
            for item in open_tickets.values('status').annotate(count=Count('id'))
        },
        'new_today': SupportTicket.objects.filter(created_at__gte=today).count(),
        'resolved_today': SupportTicket.objects.filter(resolved_at__gte=today).count(),
        'sla_breached': open_tickets.filter(
            first_response_at__isnull=True,
            created_at__lt=now - timedelta(minutes=120)  # P1 SLA как базовый
        ).count(),
    }
    
    return Response(stats)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ticket_categories(request):
    """Список категорий тикетов для формы"""
    return Response([
        {'value': k, 'label': v}
        for k, v in SupportTicket.CATEGORY_CHOICES
    ])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ticket_priorities(request):
    """Список приоритетов с SLA"""
    return Response([
        {
            'value': k,
            'label': v,
            'sla_minutes': SupportTicket.PRIORITY_SLA.get(k, 480)
        }
        for k, v in SupportTicket.PRIORITY_CHOICES
    ])
