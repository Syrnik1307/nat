from rest_framework import serializers
from .models import SupportTicket, SupportMessage, QuickSupportResponse
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
    
    class Meta:
        model = SupportTicket
        fields = [
            'id', 'subject', 'description', 'status', 'priority',
            'category', 'created_at', 'updated_at', 'resolved_at',
            'user_email', 'messages', 'unread_count'
        ]
        read_only_fields = ['created_at', 'updated_at', 'resolved_at']
    
    def get_user_email(self, obj):
        if obj.user:
            return obj.user.email
        return obj.email or 'Аноним'
    
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
    class Meta:
        model = SupportTicket
        fields = [
            'subject', 'description', 'category', 'priority',
            'email', 'name', 'user_agent', 'page_url', 'screenshot'
        ]
    
    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            validated_data['user'] = request.user
        return super().create(validated_data)


class QuickSupportResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuickSupportResponse
        fields = ['id', 'title', 'message', 'category']
