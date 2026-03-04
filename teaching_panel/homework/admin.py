from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Homework, Question, Choice, StudentSubmission, Answer, HomeworkFile,
    GeminiAPIKey, AIGradingJob, AIGradingUsage,
)

@admin.register(Homework)
class HomeworkAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'teacher', 'lesson', 'created_at')
    search_fields = ('title', 'description')

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'homework', 'question_type', 'points', 'order')
    list_filter = ('question_type',)

@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'text', 'is_correct')
    list_filter = ('is_correct',)

@admin.register(StudentSubmission)
class StudentSubmissionAdmin(admin.ModelAdmin):
    list_display = ('id', 'homework', 'student', 'status', 'total_score', 'created_at')
    list_filter = ('status',)

@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('id', 'submission', 'question', 'auto_score', 'needs_manual_review')
    list_filter = ('needs_manual_review',)


@admin.register(HomeworkFile)
class HomeworkFileAdmin(admin.ModelAdmin):
    """Админка для просмотра загруженных файлов ДЗ (картинки, аудио от учеников)."""
    list_display = ('id', 'original_name', 'teacher_link', 'storage', 'size_kb', 'gdrive_link', 'created_at', 'migrated_at')
    list_filter = ('storage', 'created_at')
    search_fields = ('id', 'original_name', 'teacher__email', 'teacher__first_name', 'teacher__last_name')
    readonly_fields = ('id', 'teacher', 'original_name', 'mime_type', 'size', 'storage', 
                       'local_path', 'gdrive_file_id', 'gdrive_url', 'created_at', 'migrated_at')
    ordering = ('-created_at',)
    
    def teacher_link(self, obj):
        if obj.teacher:
            return format_html(
                '<a href="/admin/accounts/customuser/{}/change/">{}</a>',
                obj.teacher.id, obj.teacher.email
            )
        return '-'
    teacher_link.short_description = 'Учитель'
    
    def size_kb(self, obj):
        return f"{obj.size // 1024} KB"
    size_kb.short_description = 'Размер'
    
    def gdrive_link(self, obj):
        if obj.gdrive_file_id:
            return format_html(
                '<a href="https://drive.google.com/file/d/{}/view" target="_blank">GDrive</a>',
                obj.gdrive_file_id
            )
        return '-'
    gdrive_link.short_description = 'GDrive'


# =============================================================================
# AI GRADING ADMIN
# =============================================================================

@admin.register(GeminiAPIKey)
class GeminiAPIKeyAdmin(admin.ModelAdmin):
    list_display = (
        'label', 'is_active', 'priority', 'usage_display',
        'daily_limits_display', 'errors_display', 'disabled_until',
    )
    list_filter = ('is_active',)
    list_editable = ('is_active', 'priority')
    search_fields = ('label',)
    readonly_fields = (
        'requests_used_today', 'tokens_used_today', 'last_reset_date',
        'consecutive_errors', 'last_error', 'created_at', 'updated_at',
    )
    fieldsets = (
        (None, {'fields': ('label', 'api_key', 'is_active', 'priority')}),
        ('Лимиты', {'fields': ('daily_request_limit', 'daily_token_limit')}),
        ('Использование сегодня', {
            'fields': ('requests_used_today', 'tokens_used_today', 'last_reset_date'),
        }),
        ('Ошибки', {
            'fields': ('consecutive_errors', 'last_error', 'disabled_until'),
        }),
        ('Даты', {'fields': ('created_at', 'updated_at')}),
    )
    actions = ['reset_errors', 'reset_daily_usage']

    def usage_display(self, obj):
        return f"{obj.requests_used_today} req / {obj.tokens_used_today:,} tok"
    usage_display.short_description = 'Сегодня'

    def daily_limits_display(self, obj):
        return f"{obj.daily_request_limit} req / {obj.daily_token_limit:,} tok"
    daily_limits_display.short_description = 'Лимит/день'

    def errors_display(self, obj):
        if obj.consecutive_errors > 0:
            return format_html(
                '<span style="color: red;">{} ошибок</span>',
                obj.consecutive_errors
            )
        return '-'
    errors_display.short_description = 'Ошибки'

    @admin.action(description='Сбросить ошибки и разблокировать')
    def reset_errors(self, request, queryset):
        queryset.update(consecutive_errors=0, last_error='', disabled_until=None)

    @admin.action(description='Сбросить дневное использование')
    def reset_daily_usage(self, request, queryset):
        queryset.update(requests_used_today=0, tokens_used_today=0)


@admin.register(AIGradingJob)
class AIGradingJobAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'status', 'mode', 'homework_link', 'teacher_link',
        'student_link', 'tokens_display', 'retry_count', 'created_at',
    )
    list_filter = ('status', 'mode', 'created_at')
    search_fields = (
        'homework__title', 'teacher__email',
        'submission__student__email',
    )
    readonly_fields = (
        'submission', 'homework', 'teacher', 'api_key_used',
        'tokens_input', 'tokens_output', 'result', 'error_message',
        'retry_count', 'created_at', 'started_at', 'completed_at',
    )
    list_per_page = 50
    ordering = ('-created_at',)

    def homework_link(self, obj):
        return format_html(
            '<a href="/admin/homework/homework/{}/change/">{}</a>',
            obj.homework_id, obj.homework.title[:40]
        )
    homework_link.short_description = 'ДЗ'

    def teacher_link(self, obj):
        return obj.teacher.email
    teacher_link.short_description = 'Учитель'

    def student_link(self, obj):
        student = obj.submission.student
        return student.get_full_name() or student.email
    student_link.short_description = 'Ученик'

    def tokens_display(self, obj):
        total = obj.tokens_input + obj.tokens_output
        if total > 0:
            return f"{total:,}"
        return '-'
    tokens_display.short_description = 'Токены'


@admin.register(AIGradingUsage)
class AIGradingUsageAdmin(admin.ModelAdmin):
    list_display = (
        'teacher_email', 'month', 'tokens_display', 'requests_count',
        'submissions_graded', 'limit_display',
    )
    list_filter = ('month',)
    search_fields = ('teacher__email',)
    readonly_fields = (
        'teacher', 'month', 'tokens_used', 'requests_count', 'submissions_graded',
    )
    ordering = ('-month', '-tokens_used')

    def teacher_email(self, obj):
        return obj.teacher.email
    teacher_email.short_description = 'Учитель'

    def tokens_display(self, obj):
        pct = (obj.tokens_used / obj.monthly_limit * 100) if obj.monthly_limit else 0
        color = 'red' if pct > 90 else 'orange' if pct > 70 else 'green'
        return format_html(
            '<span style="color: {};">{:,} / {:,} ({:.0f}%)</span>',
            color, obj.tokens_used, obj.monthly_limit, pct
        )
    tokens_display.short_description = 'Токены'

    def limit_display(self, obj):
        return f"{obj.tokens_remaining:,} осталось"
    limit_display.short_description = 'Остаток'
