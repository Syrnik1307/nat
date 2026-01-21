from rest_framework import serializers
from .models import SupportTicket, SupportMessage, QuickSupportResponse, SystemStatus
from accounts.models import CustomUser


class SupportMessageSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    author_avatar = serializers.SerializerMethodField()
    
    class Meta:
        model = SupportMessage
        fields = [
            'id', 'message', 'is_staff_reply', 'created_at',
            'author_name', 'author_avatar', 'read_by_user', 'read_by_staff'
        ]
    
    def get_author_name(self, obj):
        if obj.author:
            return f"{obj.author.first_name} {obj.author.last_name}".strip() or obj.author.email
        return "Аноним"
    
    def get_author_avatar(self, obj):
        if obj.author and obj.author.avatar:
            return obj.author.avatar
        return None


class SupportTicketSerializer(serializers.ModelSerializer):
    messages = SupportMessageSerializer(many=True, read_only=True)
    user_email = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    sla_breached = serializers.ReadOnlyField()
    sla_deadline = serializers.ReadOnlyField()
    time_to_first_response = serializers.ReadOnlyField()
    category_display = serializers.SerializerMethodField()
    priority_display = serializers.SerializerMethodField()
    
    class Meta:
        model = SupportTicket
        fields = [
            'id', 'subject', 'description', 'status', 'priority', 'priority_display',
            'category', 'category_display', 'created_at', 'updated_at', 'resolved_at',
            'first_response_at', 'sla_breached', 'sla_deadline', 'time_to_first_response',
            'user_email', 'user_role', 'subscription_status', 'messages', 'unread_count',
            'page_url', 'error_message', 'browser_info', 'build_version'
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
    
    def get_unread_count(self, obj):
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return 0
        
        if request.user.role in ['teacher', 'admin']:
            # Для админов - непрочитанные пользователем
            return obj.messages.filter(is_staff_reply=False, read_by_staff=False).count()
        else:
            # Для пользователей - непрочитанные от поддержки
            return obj.messages.filter(is_staff_reply=True, read_by_user=False).count()


class SupportTicketCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания тикета с расширенным контекстом"""
    
    class Meta:
        model = SupportTicket
        fields = [
            'subject', 'description', 'category', 'priority',
            'email', 'name', 
            # Технический контекст (собирается автоматически с фронтенда)
            'user_agent', 'page_url', 'screenshot',
            'build_version', 'browser_info', 'screen_resolution',
            # Описание проблемы
            'error_message', 'steps_to_reproduce', 'expected_behavior', 'actual_behavior'
        ]
    
    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            validated_data['user'] = request.user
            validated_data['user_role'] = getattr(request.user, 'role', '')
            # Получаем статус подписки
            subscription = getattr(request.user, 'subscription', None)
            if subscription:
                validated_data['subscription_status'] = f"{subscription.status} (до {subscription.expires_at.strftime('%d.%m.%Y') if subscription.expires_at else 'N/A'})"
        return super().create(validated_data)


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
