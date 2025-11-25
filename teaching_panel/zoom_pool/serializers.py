from rest_framework import serializers
from .models import ZoomAccount


class ZoomAccountSerializer(serializers.ModelSerializer):
    is_available = serializers.SerializerMethodField()
    
    class Meta:
        model = ZoomAccount
        fields = [
            'id', 'email', 'api_key', 'api_secret', 'zoom_user_id',
            'max_concurrent_meetings', 'current_meetings',
            'is_active', 'last_used_at', 'is_available',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['current_meetings', 'last_used_at', 'created_at', 'updated_at']
    
    def get_is_available(self, obj):
        return obj.is_available()
