from rest_framework import serializers
from .models import Tenant, TenantMembership, TenantResourceLimits, TenantUsageStats, TenantInvite


class TenantSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Tenant
        fields = [
            'id', 'name', 'slug', 'status',
            'email', 'phone', 'website', 'logo_url',
            'timezone', 'locale', 'metadata',
            'member_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'status', 'created_at', 'updated_at']

    def get_member_count(self, obj):
        return obj.memberships.filter(is_active=True).count()


class TenantCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ['name', 'slug', 'email', 'phone', 'website', 'logo_url', 'timezone', 'locale']


class TenantMembershipSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_first_name = serializers.CharField(source='user.first_name', read_only=True)
    user_last_name = serializers.CharField(source='user.last_name', read_only=True)

    class Meta:
        model = TenantMembership
        fields = [
            'id', 'tenant', 'user', 'role', 'is_active',
            'user_email', 'user_first_name', 'user_last_name',
            'joined_at', 'updated_at',
        ]
        read_only_fields = ['id', 'tenant', 'user', 'joined_at', 'updated_at']


class TenantResourceLimitsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantResourceLimits
        fields = [
            'max_teachers', 'max_students',
            'max_groups', 'max_courses',
            'max_lessons_per_month', 'max_homeworks',
            'max_storage_mb', 'max_recording_hours',
            'max_zoom_accounts', 'max_concurrent_meetings',
            'api_rate_limit_per_minute',
            'updated_at',
        ]
        read_only_fields = ['updated_at']


class TenantUsageStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantUsageStats
        fields = [
            'current_teachers', 'current_students',
            'current_groups', 'current_courses',
            'current_storage_mb', 'lessons_this_month', 'homeworks_total',
            'last_recalculated_at', 'updated_at',
        ]
        read_only_fields = '__all__'


class TenantInviteSerializer(serializers.ModelSerializer):
    invited_by_email = serializers.EmailField(source='invited_by.email', read_only=True)

    class Meta:
        model = TenantInvite
        fields = [
            'id', 'tenant', 'email', 'role', 'token', 'status',
            'invited_by', 'invited_by_email',
            'created_at', 'expires_at', 'accepted_at',
        ]
        read_only_fields = ['id', 'tenant', 'token', 'status', 'invited_by', 'created_at', 'accepted_at']


class TenantInviteCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(
        choices=TenantMembership.TenantRole.choices,
        default=TenantMembership.TenantRole.STUDENT,
    )


class TenantSwitchSerializer(serializers.Serializer):
    """Для переключения активного tenant'а."""
    tenant_id = serializers.IntegerField(required=False)
    tenant_slug = serializers.SlugField(required=False)

    def validate(self, attrs):
        if not attrs.get('tenant_id') and not attrs.get('tenant_slug'):
            raise serializers.ValidationError('Укажите tenant_id или tenant_slug')
        return attrs


class TenantPublicBrandingSerializer(serializers.ModelSerializer):
    """Публичный брендинг — без чувствительных полей (id, uuid, owner и т.д.)."""
    class Meta:
        model = Tenant
        fields = [
            'name', 'slug', 'logo_url',
            'email', 'phone', 'website',
            'metadata',
        ]
