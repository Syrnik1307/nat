"""
Serializers для Lectio Concierge API
"""

from rest_framework import serializers
from .models import Conversation, Message, ActionDefinition


class MessageSerializer(serializers.ModelSerializer):
    """Сериализатор сообщения"""
    
    sender_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            'id',
            'sender_type',
            'sender_name',
            'content',
            'content_type',
            'attachment_url',
            'attachment_meta',
            'ai_confidence',
            'created_at',
            'read_at',
        ]
        read_only_fields = ['id', 'sender_name', 'ai_confidence', 'created_at', 'read_at']
    
    def get_sender_name(self, obj):
        if obj.sender_type == 'user':
            return obj.sender_user.get_full_name() if obj.sender_user else 'Пользователь'
        elif obj.sender_type == 'ai':
            return 'Lectio AI'
        elif obj.sender_type == 'admin':
            return obj.sender_user.get_full_name() if obj.sender_user else 'Оператор'
        elif obj.sender_type == 'system':
            return 'Система'
        return obj.sender_type


class ConversationSerializer(serializers.ModelSerializer):
    """Сериализатор диалога"""
    
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id',
            'uuid',
            'status',
            'language',
            'page_url',
            'page_title',
            'user_email',
            'user_name',
            'ai_messages_count',
            'created_at',
            'updated_at',
            'last_message',
            'unread_count',
            'user_rating',
        ]
        read_only_fields = [
            'id', 'uuid', 'user_email', 'user_name', 
            'ai_messages_count', 'created_at', 'updated_at',
            'last_message', 'unread_count',
        ]
    
    def get_last_message(self, obj):
        last = obj.messages.order_by('-created_at').first()
        if last:
            return {
                'content': last.content[:100],
                'sender_type': last.sender_type,
                'created_at': last.created_at,
            }
        return None
    
    def get_unread_count(self, obj):
        # Для пользователя — непрочитанные сообщения от AI/admin
        return obj.messages.filter(
            sender_type__in=['ai', 'admin', 'system'],
            read_at__isnull=True,
        ).count()
    
    def get_user_name(self, obj):
        return obj.user.get_full_name() if obj.user else None


class ConversationCreateSerializer(serializers.Serializer):
    """Сериализатор для создания диалога"""
    
    page_url = serializers.URLField(required=False, allow_blank=True)
    page_title = serializers.CharField(max_length=200, required=False, allow_blank=True)
    user_agent = serializers.CharField(required=False, allow_blank=True)
    client_info = serializers.JSONField(required=False, default=dict)


class MessageCreateSerializer(serializers.Serializer):
    """Сериализатор для создания сообщения"""
    
    content = serializers.CharField(max_length=10000)
    content_type = serializers.ChoiceField(
        choices=['text', 'image', 'voice', 'file'],
        default='text',
    )
    attachment_url = serializers.URLField(required=False, allow_blank=True)
    attachment_meta = serializers.JSONField(required=False, default=dict)


class ConversationRatingSerializer(serializers.Serializer):
    """Сериализатор для оценки диалога"""
    
    rating = serializers.IntegerField(min_value=1, max_value=5)
    feedback = serializers.CharField(max_length=1000, required=False, allow_blank=True)


class ActionDefinitionSerializer(serializers.ModelSerializer):
    """Сериализатор для автоматических действий"""
    
    class Meta:
        model = ActionDefinition
        fields = [
            'name',
            'display_name',
            'description',
            'category',
            'is_read_only',
        ]


class ConversationDetailSerializer(ConversationSerializer):
    """Расширенный сериализатор диалога с сообщениями"""
    
    messages = MessageSerializer(many=True, read_only=True)
    
    class Meta(ConversationSerializer.Meta):
        fields = ConversationSerializer.Meta.fields + ['messages', 'user_context']
