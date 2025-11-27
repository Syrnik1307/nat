from django.contrib import admin
from .models import SupportTicket, SupportMessage, QuickSupportResponse


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'subject', 'user_or_email', 'status', 'priority', 'created_at', 'assigned_to')
    list_filter = ('status', 'priority', 'created_at')
    search_fields = ('subject', 'description', 'user__email', 'email')
    readonly_fields = ('created_at', 'updated_at', 'resolved_at')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'email', 'name', 'subject', 'description')
        }),
        ('Статус и приоритет', {
            'fields': ('status', 'priority', 'category', 'assigned_to')
        }),
        ('Технические данные', {
            'fields': ('user_agent', 'page_url', 'screenshot'),
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
