from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import SystemSettings, Subscription, Payment, NotificationSettings


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
    
    # Вычисляемые поля для статуса платформ
    zoom_connected = serializers.SerializerMethodField()
    zoom_email = serializers.SerializerMethodField()
    google_meet_connected = serializers.SerializerMethodField()
    available_platforms = serializers.SerializerMethodField()

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
            'telegram_username',
            'telegram_verified',
            'zoom_pmi_link',
            # Статус платформ (read-only)
            'zoom_connected',
            'zoom_email',
            'google_meet_connected',
            'google_meet_email',
            'available_platforms',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'email', 'phone_number', 'role', 'created_at', 'updated_at',
            'zoom_connected', 'zoom_email', 'google_meet_connected', 'google_meet_email', 'available_platforms'
        ]
        extra_kwargs = {
            'first_name': {'allow_blank': True, 'required': False},
            'middle_name': {'allow_blank': True, 'required': False},
            'last_name': {'allow_blank': True, 'required': False},
            'avatar': {'allow_blank': True, 'required': False},
        }

    def get_zoom_connected(self, obj):
        """Возвращает True если Zoom подключён (личные credentials)"""
        return obj.is_zoom_connected()

    def get_zoom_email(self, obj):
        """Возвращает email/user_id привязанного Zoom аккаунта"""
        if obj.is_zoom_connected():
            return obj.zoom_user_id or ''
        return ''

    def get_google_meet_connected(self, obj):
        """Возвращает True если Google Meet подключён"""
        return obj.is_google_meet_connected()

    def get_available_platforms(self, obj):
        """Возвращает список доступных платформ для проведения уроков"""
        # Только для учителей
        if obj.role != 'teacher':
            return []
        return obj.get_available_platforms()


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
    gdrive_folder_link = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = [
            'id', 'plan', 'status', 'started_at', 'expires_at',
            'cancelled_at', 'payment_method', 'auto_renew',
            'next_billing_date', 'total_paid', 'last_payment_date',
            'base_storage_gb', 'extra_storage_gb', 'used_storage_gb', 'total_storage_gb',
            'gdrive_folder_id', 'gdrive_folder_link',
            'created_at', 'updated_at', 'payments'
        ]
        read_only_fields = [
            'id', 'status', 'started_at', 'cancelled_at', 'total_paid',
            'last_payment_date', 'created_at', 'updated_at', 'total_storage_gb',
            'gdrive_folder_id', 'gdrive_folder_link'
        ]
    
    def get_gdrive_folder_link(self, obj):
        if obj.gdrive_folder_id:
            return f"https://drive.google.com/drive/folders/{obj.gdrive_folder_id}"
        return None


class NotificationSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationSettings
        fields = [
            'telegram_enabled',
            # Базовые — учитель
            'notify_homework_submitted',
            'notify_subscription_expiring',
            'notify_payment_success',
            # Аналитика — учитель
            'notify_absence_alert',
            'absence_alert_threshold',
            'notify_performance_drop',
            'performance_drop_percent',
            'notify_group_health',
            'notify_grading_backlog',
            'grading_backlog_threshold',
            'grading_backlog_hours',
            'notify_inactive_student',
            'inactive_student_days',
            # Новые — учитель: события с учениками и уроками
            'notify_student_joined',
            'notify_student_left',
            'notify_recording_ready',
            # Глобальные настройки уроков — учитель
            'default_lesson_reminder_enabled',
            'default_lesson_reminder_minutes',
            'default_notify_to_group_chat',
            'default_notify_to_students_dm',
            'notify_lesson_link_on_start',
            'notify_materials_added',
            # Базовые — ученик
            'notify_homework_graded',
            'notify_homework_deadline',
            'notify_lesson_reminders',
            'notify_new_homework',
            # Аналитика — ученик
            'notify_student_absence_warning',
            'notify_control_point_deadline',
            'notify_achievement',
            'notify_inactivity_nudge',
            'updated_at',
        ]
        read_only_fields = ['updated_at']
