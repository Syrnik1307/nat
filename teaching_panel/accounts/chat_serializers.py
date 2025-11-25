from rest_framework import serializers
from .models import CustomUser, Chat, Message, MessageReadStatus


class UserUsernameSerializer(serializers.ModelSerializer):
    """Сериализатор для отображения короткого имени пользователя"""
    
    class Meta:
        model = CustomUser
        fields = ['id', 'username_handle', 'first_name', 'last_name', 'email']


class MessageSerializer(serializers.ModelSerializer):
    """Сериализатор для сообщений"""
    
    sender = UserUsernameSerializer(read_only=True)
    sender_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = ['id', 'chat', 'sender', 'sender_name', 'text', 'is_read', 'created_at', 'updated_at']
        read_only_fields = ['sender', 'created_at', 'updated_at']
    
    def get_sender_name(self, obj):
        return obj.sender.get_full_name()


class ChatSerializer(serializers.ModelSerializer):
    """Сериализатор для чатов"""
    
    participants = UserUsernameSerializer(many=True, read_only=True)
    participant_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Chat
        fields = [
            'id', 'name', 'chat_type', 'participants', 'participant_ids',
            'created_by', 'group', 'last_message', 'unread_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']
    
    def get_last_message(self, obj):
        last_msg = obj.get_last_message()
        if last_msg:
            return {
                'id': last_msg.id,
                'text': last_msg.text,
                'sender': last_msg.sender.get_full_name(),
                'created_at': last_msg.created_at
            }
        return None
    
    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.messages.filter(
                sender__ne=request.user,
                read_statuses__user=request.user,
                read_statuses__is_read=False
            ).count()
        return 0
    
    def create(self, validated_data):
        participant_ids = validated_data.pop('participant_ids', [])
        validated_data['created_by'] = self.context['request'].user
        chat = Chat.objects.create(**validated_data)
        
        # Добавляем участников
        if participant_ids:
            chat.participants.set(participant_ids)
        
        # Добавляем создателя как участника
        chat.participants.add(validated_data['created_by'])
        
        return chat


class MessageReadStatusSerializer(serializers.ModelSerializer):
    """Сериализатор для статусов прочтения"""
    
    user = UserUsernameSerializer(read_only=True)
    
    class Meta:
        model = MessageReadStatus
        fields = ['id', 'message', 'user', 'is_read', 'read_at']
        read_only_fields = ['user', 'read_at']
