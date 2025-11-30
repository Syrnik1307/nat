from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import SystemSettings, Subscription, Payment


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Добавляет роль пользователя в JWT токен"""
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Добавляем кастомные claims
        # ВАЖНО: Роль берем ТОЛЬКО из БД, не переопределяем!
        # Это предотвращает случайное изменение ролей через токены
        token['role'] = user.role
        token['is_superuser'] = getattr(user, 'is_superuser', False)
        token['email'] = user.email
        
        return token


class UserProfileSerializer(serializers.ModelSerializer):
    """Сериализатор для профиля текущего пользователя"""

    class Meta:
        model = get_user_model()
        fields = [
            'id',
            'email',
            'phone_number',
            'first_name',
            'middle_name',
            'last_name',
            'role',
            'avatar',
            'agreed_to_marketing',
            'date_of_birth',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['email', 'phone_number', 'role', 'created_at', 'updated_at']
        extra_kwargs = {
            'first_name': {'allow_blank': True, 'required': False},
            'middle_name': {'allow_blank': True, 'required': False},
            'last_name': {'allow_blank': True, 'required': False},
            'avatar': {'allow_blank': True, 'required': False},
        }


class SystemSettingsSerializer(serializers.ModelSerializer):
    """Сериализатор для системных настроек"""
    
    class Meta:
        model = SystemSettings
        fields = [
            'id',
            # Email
            'email_from',
            'email_notifications_enabled',
            'welcome_email_enabled',
            # Уведомления
            'lesson_reminder_hours',
            'homework_deadline_reminder_hours',
            'push_notifications_enabled',
            # Zoom
            'default_lesson_duration',
            'auto_recording',
            'waiting_room_enabled',
            # Расписание
            'min_booking_hours',
            'max_booking_days',
            'cancellation_hours',
            # Брендинг
            'platform_name',
            'support_email',
            'logo_url',
            'primary_color',
            # Метаданные
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_primary_color(self, value):
        """Проверка HEX цвета"""
        if not value.startswith('#') or len(value) != 7:
            raise serializers.ValidationError('Используйте формат HEX: #RRGGBB')
        try:
            int(value[1:], 16)
        except ValueError:
            raise serializers.ValidationError('Некорректный HEX код цвета')
        return value
    
    def validate_lesson_reminder_hours(self, value):
        if value < 0 or value > 168:
            raise serializers.ValidationError('Напоминание должно быть от 0 до 168 часов (неделя)')
        return value
    
    def validate_default_lesson_duration(self, value):
        if value < 15 or value > 480:
            raise serializers.ValidationError('Длительность от 15 минут до 8 часов')
        return value


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            'id', 'amount', 'currency', 'status',
            'payment_system', 'payment_id', 'payment_url',
            'created_at', 'paid_at', 'metadata'
        ]
        read_only_fields = ['id', 'status', 'payment_system', 'payment_id', 'payment_url', 'created_at', 'paid_at']


class SubscriptionSerializer(serializers.ModelSerializer):
    payments = PaymentSerializer(many=True, read_only=True)
    total_storage_gb = serializers.IntegerField(read_only=True)

    class Meta:
        model = Subscription
        fields = [
            'id', 'plan', 'status', 'started_at', 'expires_at',
            'cancelled_at', 'payment_method', 'auto_renew',
            'next_billing_date', 'total_paid', 'last_payment_date',
            'base_storage_gb', 'extra_storage_gb', 'used_storage_gb', 'total_storage_gb',
            'created_at', 'updated_at', 'payments'
        ]
        read_only_fields = [
            'id', 'status', 'started_at', 'cancelled_at', 'total_paid',
            'last_payment_date', 'created_at', 'updated_at', 'total_storage_gb'
        ]
