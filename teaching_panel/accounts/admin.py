from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    CustomUser,
    Chat,
    Message,
    MessageReadStatus,
    StatusBarMessage,
    PhoneVerification,
    EmailVerification,
    Subscription,
    Payment,
    TelegramLinkCode,
    NotificationSettings,
    NotificationLog,
)


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Админ-панель для кастомной модели пользователя"""
    
    model = CustomUser
    list_display = ('email', 'username_handle', 'role', 'first_name', 'last_name', 'telegram_verified', 'is_staff', 'is_active', 'created_at')
    list_filter = ('role', 'is_staff', 'is_active', 'agreed_to_marketing', 'telegram_verified')
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Личная информация', {'fields': ('first_name', 'last_name', 'middle_name', 'username_handle', 'phone_number', 'date_of_birth', 'avatar')}),
        ('Роль и права', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Zoom', {'fields': ('zoom_account_id', 'zoom_client_id', 'zoom_client_secret', 'zoom_user_id', 'zoom_pmi_link')}),
        ('Telegram', {'fields': ('telegram_id', 'telegram_username', 'telegram_chat_id', 'telegram_verified')}),
        ('Маркетинг', {'fields': ('agreed_to_marketing',)}),
        ('Важные даты', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username_handle', 'role', 'password1', 'password2', 'is_staff', 'is_active')
        }),
    )
    
    search_fields = ('email', 'username_handle', 'first_name', 'last_name', 'phone_number')
    ordering = ('-created_at',)


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'chat_type', 'created_by', 'created_at')
    list_filter = ('chat_type', 'created_at')
    search_fields = ('name',)
    filter_horizontal = ('participants',)
    raw_id_fields = ('created_by', 'group')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'chat', 'sender', 'text_preview', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('text', 'sender__email')
    raw_id_fields = ('chat', 'sender')
    
    def text_preview(self, obj):
        return obj.text[:50]
    text_preview.short_description = 'Текст'


@admin.register(MessageReadStatus)
class MessageReadStatusAdmin(admin.ModelAdmin):
    list_display = ('id', 'message', 'user', 'is_read', 'read_at')
    list_filter = ('is_read', 'read_at')
    raw_id_fields = ('message', 'user')


@admin.register(StatusBarMessage)
class StatusBarMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'message_preview', 'target', 'is_active', 'created_by', 'created_at')
    list_filter = ('target', 'is_active', 'created_at')
    search_fields = ('message',)
    raw_id_fields = ('created_by',)
    
    def message_preview(self, obj):
        return obj.message[:50]
    message_preview.short_description = 'Сообщение'


@admin.register(PhoneVerification)
class PhoneVerificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'phone_number', 'code', 'is_verified', 'attempts', 'created_at', 'expires_at')
    list_filter = ('is_verified', 'created_at')
    search_fields = ('phone_number',)
    readonly_fields = ('code', 'created_at', 'expires_at')
    
    def has_add_permission(self, request):
        # Отключаем ручное создание через админку
        return False


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'code', 'token_preview', 'is_verified', 'attempts', 'created_at', 'expires_at')
    list_filter = ('is_verified', 'created_at')
    search_fields = ('email',)
    readonly_fields = ('token', 'code', 'created_at', 'expires_at')
    
    def token_preview(self, obj):
        return str(obj.token)[:8] + '...'
    token_preview.short_description = 'Токен'
    
    def has_add_permission(self, request):
        # Отключаем ручное создание через админку
        return False


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    raw_id_fields = ('subscription',)
    readonly_fields = ()


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'plan', 'status', 'started_at', 'expires_at',
        'auto_renew', 'next_billing_date', 'total_paid', 'last_payment_date',
    )
    list_filter = ('plan', 'status', 'auto_renew', 'expires_at', 'started_at')
    search_fields = ('user__email',)
    raw_id_fields = ('user',)
    inlines = [PaymentInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'payment_id', 'subscription', 'amount', 'currency', 'status',
        'payment_system', 'created_at', 'paid_at',
    )
    list_filter = ('status', 'payment_system', 'currency', 'created_at')
    search_fields = ('payment_id', 'subscription__user__email')
    raw_id_fields = ('subscription',)


@admin.register(TelegramLinkCode)
class TelegramLinkCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'user', 'used', 'created_at', 'expires_at', 'used_at')
    list_filter = ('used', 'created_at')
    search_fields = ('code', 'user__email')
    raw_id_fields = ('user',)
    readonly_fields = ('code', 'created_at', 'expires_at', 'used_at')


@admin.register(NotificationSettings)
class NotificationSettingsAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'telegram_enabled', 'notify_homework_submitted',
        'notify_homework_graded', 'notify_homework_deadline', 'notify_lesson_reminders',
        'notify_new_homework', 'notify_subscription_expiring', 'notify_payment_success', 'updated_at'
    )
    list_filter = (
        'telegram_enabled', 'notify_homework_submitted', 'notify_homework_graded',
        'notify_homework_deadline', 'notify_lesson_reminders', 'notify_new_homework',
        'notify_subscription_expiring', 'notify_payment_success'
    )
    search_fields = ('user__email',)
    raw_id_fields = ('user',)


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ('notification_type', 'user', 'channel', 'status', 'created_at')
    list_filter = ('notification_type', 'channel', 'status', 'created_at')
    search_fields = ('user__email', 'message')
    raw_id_fields = ('user',)
