from django.contrib import admin
from .models import ZoomAccount, Group, Lesson, Attendance, RecurringLesson, AuditLog


@admin.register(ZoomAccount)
class ZoomAccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'zoom_user_id', 'is_busy', 'current_lesson', 'updated_at')
    list_filter = ('is_busy', 'created_at')
    search_fields = ('name', 'zoom_user_id')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'zoom_user_id')
        }),
        ('API ключи', {
            'fields': ('api_key', 'api_secret'),
            'classes': ('collapse',)
        }),
        ('Статус', {
            'fields': ('is_busy', 'current_lesson')
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'teacher', 'student_count', 'created_at')
    list_filter = ('teacher', 'created_at')
    search_fields = ('name', 'teacher__email', 'description')
    filter_horizontal = ('students',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'teacher', 'description')
        }),
        ('Студенты', {
            'fields': ('students',)
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'group', 'teacher', 'start_time', 'end_time', 'location')
    list_filter = ('group', 'teacher', 'start_time')
    search_fields = ('title', 'group__name', 'teacher__email', 'topics', 'location')
    date_hierarchy = 'start_time'
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('title', 'group', 'teacher')
        }),
        ('Расписание', {
            'fields': ('start_time', 'end_time', 'location')
        }),
        ('Содержание', {
            'fields': ('topics', 'notes')
        }),
        ('Zoom интеграция', {
            'fields': ('zoom_meeting_id', 'zoom_join_url', 'zoom_password'),
            'classes': ('collapse',)
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'lesson', 'status', 'marked_at')
    list_filter = ('status', 'lesson__group', 'marked_at')
    search_fields = ('student__email', 'student__first_name', 'student__last_name', 'lesson__title')
    readonly_fields = ('marked_at',)
    
    fieldsets = (
        (None, {
            'fields': ('lesson', 'student', 'status', 'notes')
        }),
        ('Системная информация', {
            'fields': ('marked_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(RecurringLesson)
class RecurringLessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'group', 'teacher', 'day_of_week', 'week_type', 'start_time', 'end_time', 'start_date', 'end_date')
    list_filter = ('day_of_week', 'week_type', 'group', 'teacher')
    search_fields = ('title', 'group__name', 'teacher__email', 'topics')
    date_hierarchy = 'start_date'
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('title', 'group', 'teacher')
        }),
        ('Расписание', {
            'fields': ('day_of_week', 'week_type', 'start_time', 'end_time')
        }),
        ('Период действия', {
            'fields': ('start_date', 'end_date')
        }),
        ('Содержание', {
            'fields': ('topics', 'location')
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'resource_type', 'resource_id', 'ip_address', 'timestamp')
    list_filter = ('action', 'resource_type', 'timestamp')
    search_fields = ('user__email', 'ip_address', 'user_agent')
    readonly_fields = ('user', 'action', 'resource_type', 'resource_id', 'ip_address', 'user_agent', 'details', 'timestamp')
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Пользователь и действие', {
            'fields': ('user', 'action', 'resource_type', 'resource_id')
        }),
        ('Контекст запроса', {
            'fields': ('ip_address', 'user_agent')
        }),
        ('Детали', {
            'fields': ('details',)
        }),
        ('Время', {
            'fields': ('timestamp',)
        }),
    )
    
    def has_add_permission(self, request):
        """Запретить ручное создание записей аудита через админку"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Запретить изменение записей аудита"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Разрешить удаление только суперпользователям"""
        return request.user.is_superuser
