from rest_framework import serializers

from .models import ProtectedContent, ContentAccessSession, ContentSecurityEvent


class ProtectedContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProtectedContent
        fields = [
            'id',
            'title',
            'description',
            'yandex_embed_url',
            'yandex_public_url',
            'group',
            'created_by',
            'is_active',
            'watermark_enabled',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']


class SessionStartSerializer(serializers.Serializer):
    content_id = serializers.IntegerField(min_value=1)


class SessionHeartbeatSerializer(serializers.Serializer):
    session_token = serializers.UUIDField()
    is_visible = serializers.BooleanField(required=False, default=True)
    is_focused = serializers.BooleanField(required=False, default=True)
    is_fullscreen = serializers.BooleanField(required=False, default=True)
    devtools_open = serializers.BooleanField(required=False, default=False)
    recorder_suspected = serializers.BooleanField(required=False, default=False)
    display_capture_detected = serializers.BooleanField(required=False, default=False)
    multiple_screens_detected = serializers.BooleanField(required=False, default=False)
    metadata = serializers.DictField(required=False, default=dict)


class SessionEventSerializer(serializers.Serializer):
    session_token = serializers.UUIDField()
    event_type = serializers.ChoiceField(choices=ContentSecurityEvent.EVENT_CHOICES)
    severity = serializers.ChoiceField(choices=ContentSecurityEvent.SEVERITY_CHOICES, required=False)
    metadata = serializers.DictField(required=False, default=dict)


class SessionStatusSerializer(serializers.ModelSerializer):
    content_id = serializers.IntegerField(source='content.id', read_only=True)

    class Meta:
        model = ContentAccessSession
        fields = [
            'session_token',
            'content_id',
            'status',
            'risk_score',
            'block_reason',
            'started_at',
            'last_heartbeat_at',
            'blocked_at',
            'ended_at',
            'expires_at',
        ]


class SessionPlaybackUrlSerializer(serializers.Serializer):
    session_token = serializers.UUIDField()
    device_id = serializers.CharField(max_length=255)
