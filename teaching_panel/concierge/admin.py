"""
Django Admin для Lectio Concierge
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Conversation, Message, 
    KnowledgeDocument, KnowledgeChunk,
    ActionDefinition, ActionExecution,
    ConversationMetrics,
)


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ['sender_type', 'sender_user', 'content', 'created_at']
    fields = ['sender_type', 'sender_user', 'content', 'created_at']
    ordering = ['created_at']
    
    def has_add_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user_email', 'status_badge', 'language', 
        'page_title', 'ai_messages_count', 'created_at', 'updated_at'
    ]
    list_filter = ['status', 'language', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'page_title']
    readonly_fields = [
        'uuid', 'user', 'status', 'created_at', 'updated_at', 
        'ai_escalated_at', 'ai_escalation_reason', 'ai_messages_count',
        'telegram_thread_id', 'user_context', 'client_info',
    ]
    inlines = [MessageInline]
    
    fieldsets = (
        ('Основное', {
            'fields': ('uuid', 'user', 'status', 'language')
        }),
        ('Контекст', {
            'fields': ('page_url', 'page_title', 'user_context', 'client_info')
        }),
        ('AI', {
            'fields': ('ai_messages_count', 'ai_retry_count', 'ai_escalated_at', 'ai_escalation_reason')
        }),
        ('Telegram', {
            'fields': ('telegram_thread_id', 'assigned_admin')
        }),
        ('Оценка', {
            'fields': ('user_rating', 'user_feedback')
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at', 'resolved_at')
        }),
    )
    
    def user_email(self, obj):
        return obj.user.email if obj.user else '-'
    user_email.short_description = 'Email'
    
    def status_badge(self, obj):
        colors = {
            'ai_mode': '#3b82f6',      # blue
            'human_mode': '#f59e0b',   # orange
            'resolved': '#10b981',      # green
            'closed': '#6b7280',        # gray
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background:{}; color:white; padding:2px 8px; border-radius:4px">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Статус'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation', 'sender_type', 'content_preview', 'created_at']
    list_filter = ['sender_type', 'content_type', 'created_at']
    search_fields = ['content', 'conversation__user__email']
    readonly_fields = ['conversation', 'sender_type', 'sender_user', 'content', 'created_at']
    
    def content_preview(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    content_preview.short_description = 'Содержимое'


@admin.register(KnowledgeDocument)
class KnowledgeDocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'language', 'is_active', 'last_indexed_at']
    list_filter = ['category', 'language', 'is_active']
    search_fields = ['title', 'source_path']
    readonly_fields = ['source_path', 'content_hash', 'last_indexed_at', 'created_at', 'updated_at']


@admin.register(KnowledgeChunk)
class KnowledgeChunkAdmin(admin.ModelAdmin):
    list_display = ['id', 'document', 'chunk_index', 'section_title', 'content_preview']
    list_filter = ['document__category']
    search_fields = ['content', 'section_title']
    readonly_fields = ['document', 'chunk_index', 'content', 'embedding_model']
    
    def content_preview(self, obj):
        return obj.content[:150] + '...' if len(obj.content) > 150 else obj.content
    content_preview.short_description = 'Содержимое'


@admin.register(ActionDefinition)
class ActionDefinitionAdmin(admin.ModelAdmin):
    list_display = ['name', 'display_name', 'category', 'is_read_only', 'is_active']
    list_filter = ['category', 'is_active', 'is_read_only']
    search_fields = ['name', 'display_name', 'description']
    
    fieldsets = (
        ('Основное', {
            'fields': ('name', 'display_name', 'display_name_en', 'description', 'category')
        }),
        ('Обработчик', {
            'fields': ('handler_path',)
        }),
        ('AI триггеры', {
            'fields': ('trigger_keywords', 'trigger_categories', 'required_params')
        }),
        ('Безопасность', {
            'fields': ('is_read_only', 'requires_confirmation', 'max_daily_runs_per_user')
        }),
        ('Статус', {
            'fields': ('is_active',)
        }),
    )


@admin.register(ActionExecution)
class ActionExecutionAdmin(admin.ModelAdmin):
    list_display = ['id', 'action', 'conversation', 'status', 'duration_ms', 'started_at']
    list_filter = ['status', 'action', 'started_at']
    search_fields = ['conversation__user__email', 'action__name']
    readonly_fields = [
        'action', 'conversation', 'triggered_by_message', 
        'status', 'input_params', 'result', 'result_message', 
        'error_message', 'started_at', 'completed_at', 'duration_ms'
    ]


@admin.register(ConversationMetrics)
class ConversationMetricsAdmin(admin.ModelAdmin):
    list_display = [
        'date', 'total_conversations', 'ai_only_resolved', 
        'escalated_to_human', 'avg_rating', 'actions_executed'
    ]
    list_filter = ['date']
    readonly_fields = [
        'date', 'total_conversations', 'ai_only_resolved', 
        'escalated_to_human', 'avg_ai_response_time_ms', 
        'avg_human_response_time_sec', 'avg_rating', 'ratings_count',
        'actions_executed', 'actions_success_rate', 'updated_at'
    ]
