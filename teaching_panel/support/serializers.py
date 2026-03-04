from rest_framework import serializers
from .models import SupportTicket, SupportMessage, QuickSupportResponse, SystemStatus
from accounts.models import CustomUser

# Условный импорт — SupportAttachment доступен только при SUPPORT_V2_ENABLED
try:
    from .models import SupportAttachment
    _HAS_ATTACHMENT_MODEL = True
except ImportError:
    _HAS_ATTACHMENT_MODEL = False


class SupportAttachmentSerializer(serializers.Serializer):
    """Сериализатор для файловых вложений (только при SUPPORT_V2_ENABLED)."""
    id = serializers.CharField()
    original_name = serializers.CharField()
    mime_type = serializers.CharField()
    size = serializers.IntegerField()
    url = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField()

    def get_url(self, obj):
        return f'/api/support/attachments/{obj.id}/'


class SupportMessageSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    author_avatar = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()

    class Meta:
        model = SupportMessage
        fields = [
            'id', 'message', 'is_staff_reply', 'created_at',
            'author_name', 'author_avatar', 'read_by_user', 'read_by_staff',
            'attachments',
        ]

    def get_author_name(self, obj):
        if obj.author:
            return f"{obj.author.first_name} {obj.author.last_name}".strip() or obj.author.email
        return "Аноним"

    def get_author_avatar(self, obj):
        if obj.author and obj.author.avatar:
            return obj.author.avatar
        return None

    def get_attachments(self, obj):
        if not _HAS_ATTACHMENT_MODEL:
            return []
        qs = obj.file_attachments.all()
        return SupportAttachmentSerializer(qs, many=True).data


class SupportTicketSerializer(serializers.ModelSerializer):
    messages = SupportMessageSerializer(many=True, read_only=True)
    user_email = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    sla_breached = serializers.ReadOnlyField()
    sla_deadline = serializers.ReadOnlyField()
    time_to_first_response = serializers.ReadOnlyField()
    category_display = serializers.SerializerMethodField()
    priority_display = serializers.SerializerMethodField()
    ticket_attachments = serializers.SerializerMethodField()
    assigned_to_name = serializers.SerializerMethodField()

    class Meta:
        model = SupportTicket
        fields = [
            'id', 'subject', 'description', 'status', 'priority', 'priority_display',
            'category', 'category_display', 'created_at', 'updated_at', 'resolved_at',
            'first_response_at', 'sla_breached', 'sla_deadline', 'time_to_first_response',
            'user_email', 'user_role', 'subscription_status', 'messages', 'unread_count',
            'page_url', 'error_message', 'browser_info', 'build_version',
            'ticket_attachments', 'assigned_to', 'assigned_to_name', 'source',
        ]
        read_only_fields = ['created_at', 'updated_at', 'resolved_at', 'first_response_at']

    def get_user_email(self, obj):
        if obj.user:
            return obj.user.email
        return obj.email or 'Аноним'

    def get_category_display(self, obj):
        return dict(SupportTicket.CATEGORY_CHOICES).get(obj.category, obj.category)

    def get_priority_display(self, obj):
        return obj.get_priority_display()

    def get_assigned_to_name(self, obj):
        if obj.assigned_to:
            name = f"{obj.assigned_to.first_name} {obj.assigned_to.last_name}".strip()
            return name or obj.assigned_to.email
        return None

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return 0

        if request.user.role in ['teacher', 'admin']:
            return obj.messages.filter(is_staff_reply=False, read_by_staff=False).count()
        else:
            return obj.messages.filter(is_staff_reply=True, read_by_user=False).count()

    def get_ticket_attachments(self, obj):
        if not _HAS_ATTACHMENT_MODEL:
            return []
        qs = obj.attachments.all()
        return SupportAttachmentSerializer(qs, many=True).data


class SupportTicketCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания тикета с расширенным контекстом"""
    attachment_ids = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        write_only=True,
    )

    class Meta:
        model = SupportTicket
        fields = [
            'subject', 'description', 'category', 'priority',
            'email', 'name',
            # Технический контекст (собирается автоматически с фронтенда)
            'user_agent', 'page_url', 'screenshot',
            'build_version', 'browser_info', 'screen_resolution',
            # Описание проблемы
            'error_message', 'steps_to_reproduce', 'expected_behavior', 'actual_behavior',
            # Вложения
            'attachment_ids',
        ]
        extra_kwargs = {
            'category': {'required': False},
        }

    def create(self, validated_data):
        attachment_ids = validated_data.pop('attachment_ids', [])
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            validated_data['user'] = request.user
            validated_data['user_role'] = getattr(request.user, 'role', '')
            subscription = getattr(request.user, 'subscription', None)
            if subscription:
                validated_data['subscription_status'] = (
                    f"{subscription.status} "
                    f"(до {subscription.expires_at.strftime('%d.%m.%Y') if subscription.expires_at else 'N/A'})"
                )
        if not validated_data.get('category'):
            validated_data['category'] = 'other'

        ticket = super().create(validated_data)

        # Привязываем вложения к тикету
        if attachment_ids and _HAS_ATTACHMENT_MODEL:
            SupportAttachment.objects.filter(
                id__in=attachment_ids,
                ticket__isnull=True,
                message__isnull=True,
            ).update(ticket=ticket)

        return ticket


class SupportTicketListSerializer(serializers.ModelSerializer):
    """Облегчённый сериализатор для списка тикетов (без сообщений)."""
    user_email = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    category_display = serializers.SerializerMethodField()
    priority_display = serializers.SerializerMethodField()
    last_message_at = serializers.SerializerMethodField()
    assigned_to_name = serializers.SerializerMethodField()

    class Meta:
        model = SupportTicket
        fields = [
            'id', 'subject', 'status', 'priority', 'priority_display',
            'category', 'category_display', 'created_at', 'updated_at',
            'user_email', 'unread_count', 'last_message_at',
            'assigned_to', 'assigned_to_name', 'source',
            'sla_breached', 'sla_deadline',
        ]

    def get_user_email(self, obj):
        if obj.user:
            return obj.user.email
        return obj.email or 'Аноним'

    def get_category_display(self, obj):
        return dict(SupportTicket.CATEGORY_CHOICES).get(obj.category, obj.category)

    def get_priority_display(self, obj):
        return obj.get_priority_display()

    def get_assigned_to_name(self, obj):
        if obj.assigned_to:
            name = f"{obj.assigned_to.first_name} {obj.assigned_to.last_name}".strip()
            return name or obj.assigned_to.email
        return None

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return 0
        if request.user.role == 'admin':
            return obj.messages.filter(is_staff_reply=False, read_by_staff=False).count()
        return obj.messages.filter(is_staff_reply=True, read_by_user=False).count()

    def get_last_message_at(self, obj):
        last = obj.messages.order_by('-created_at').values_list('created_at', flat=True).first()
        return last


class QuickSupportResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuickSupportResponse
        fields = ['id', 'title', 'message', 'category']


class SystemStatusSerializer(serializers.ModelSerializer):
    """Сериализатор для статуса системы"""
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = SystemStatus
        fields = [
            'status', 'status_display', 'message',
            'incident_title', 'incident_started_at', 'updated_at'
        ]

    def get_status_display(self, obj):
        return obj.get_status_display()

