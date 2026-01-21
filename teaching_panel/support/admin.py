from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import SupportTicket, SupportMessage, QuickSupportResponse, SystemStatus


@admin.register(SystemStatus)
class SystemStatusAdmin(admin.ModelAdmin):
    list_display = ('status', 'incident_title', 'updated_at', 'updated_by')
    readonly_fields = ('updated_at',)
    
    def has_add_permission(self, request):
        # Разрешаем только один объект (singleton)
        return not SystemStatus.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'subject', 'user_or_email', 'status', 'priority', 'priority_badge', 'category', 'sla_status', 'created_at', 'assigned_to')
    list_filter = ('status', 'priority', 'category', 'created_at')
    search_fields = ('subject', 'description', 'user__email', 'email', 'error_message')
    readonly_fields = ('created_at', 'updated_at', 'resolved_at', 'first_response_at', 'sla_info')
    list_editable = ('priority', 'status')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'email', 'name', 'subject', 'description')
        }),
        ('Статус и приоритет', {
            'fields': ('status', 'priority', 'category', 'assigned_to')
        }),
        ('SLA', {
            'fields': ('sla_info', 'first_response_at'),
            'classes': ('collapse',)
        }),
        ('Контекст пользователя', {
            'fields': ('user_role', 'subscription_status', 'page_url', 'browser_info', 'build_version'),
            'classes': ('collapse',)
        }),
        ('Описание проблемы', {
            'fields': ('error_message', 'steps_to_reproduce', 'expected_behavior', 'actual_behavior'),
            'classes': ('collapse',)
        }),
        ('Технические данные', {
            'fields': ('user_agent', 'screen_resolution', 'screenshot'),
            'classes': ('collapse',)
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at', 'resolved_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_or_email(self, obj):
        if obj.user:
            return obj.user.email
        return obj.email or 'Аноним'
    user_or_email.short_description = 'Пользователь'
    
    def priority_badge(self, obj):
        colors = {
            'p0': '#dc3545',  # Красный
            'p1': '#fd7e14',  # Оранжевый
            'p2': '#ffc107',  # Жёлтый
            'p3': '#28a745',  # Зелёный
        }
        color = colors.get(obj.priority, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px;">{}</span>',
            color, obj.get_priority_display()
        )
    priority_badge.short_description = 'Приоритет'
    
    def sla_status(self, obj):
        if obj.first_response_at:
            mins = obj.time_to_first_response
            if obj.sla_breached:
                return format_html('<span style="color: red;">Нарушен ({} мин)</span>', mins)
            return format_html('<span style="color: green;">OK ({} мин)</span>', mins)
        else:
            remaining = (obj.sla_deadline - timezone.now()).total_seconds() / 60
            if remaining < 0:
                return format_html('<span style="color: red;">ПРОСРОЧЕН!</span>')
            elif remaining < 30:
                return format_html('<span style="color: orange;">Осталось {} мин</span>', int(remaining))
            return format_html('<span style="color: gray;">{} мин</span>', int(remaining))
    sla_status.short_description = 'SLA'
    
    def sla_info(self, obj):
        return f"SLA: {obj.sla_minutes} мин | Дедлайн: {obj.sla_deadline.strftime('%d.%m.%Y %H:%M')}"
    sla_info.short_description = 'Информация о SLA'


@admin.register(SupportMessage)
class SupportMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'author_name', 'is_staff_reply', 'created_at', 'message_preview')
    list_filter = ('is_staff_reply', 'created_at')
    search_fields = ('message', 'ticket__subject', 'author__email')
    readonly_fields = ('created_at',)
    
    def author_name(self, obj):
        if obj.author:
            return obj.author.email
        return 'Аноним'
    author_name.short_description = 'Автор'
    
    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Сообщение'


@admin.register(QuickSupportResponse)
class QuickSupportResponseAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'usage_count', 'is_active', 'created_at')
    list_filter = ('is_active', 'category', 'created_at')
    search_fields = ('title', 'message', 'category')
    readonly_fields = ('usage_count', 'created_at', 'updated_at')
