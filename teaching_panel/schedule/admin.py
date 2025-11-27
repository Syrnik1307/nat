from django.contrib import admin
from .models import (
    ZoomAccount, Group, Lesson, Attendance, RecurringLesson, AuditLog, 
    TeacherStorageQuota, LessonMaterial, MaterialView
)


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


@admin.register(TeacherStorageQuota)
class TeacherStorageQuotaAdmin(admin.ModelAdmin):
    list_display = (
        'teacher_name',
        'used_gb_display',
        'total_gb_display',
        'usage_percent_display',
        'recordings_count',
        'quota_exceeded',
        'warning_sent'
    )
    list_filter = ('quota_exceeded', 'warning_sent', 'created_at')
    search_fields = ('teacher__email', 'teacher__first_name', 'teacher__last_name')
    readonly_fields = (
        'used_bytes',
        'recordings_count',
        'created_at',
        'updated_at',
        'last_warning_at',
        'usage_percent_display',
        'available_gb_display'
    )
    
    fieldsets = (
        ('Преподаватель', {
            'fields': ('teacher',)
        }),
        ('Квота хранилища', {
            'fields': (
                'total_quota_bytes',
                'used_bytes',
                'usage_percent_display',
                'available_gb_display',
                'recordings_count'
            )
        }),
        ('История покупок', {
            'fields': ('purchased_gb',)
        }),
        ('Статус и уведомления', {
            'fields': (
                'quota_exceeded',
                'warning_sent',
                'last_warning_at'
            )
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def teacher_name(self, obj):
        """Имя преподавателя"""
        return obj.teacher.get_full_name() or obj.teacher.email
    teacher_name.short_description = 'Преподаватель'
    teacher_name.admin_order_field = 'teacher__email'
    
    def used_gb_display(self, obj):
        """Использовано ГБ"""
        return f"{obj.used_gb:.2f} GB"
    used_gb_display.short_description = 'Использовано'
    used_gb_display.admin_order_field = 'used_bytes'
    
    def total_gb_display(self, obj):
        """Общая квота ГБ"""
        return f"{obj.total_gb:.2f} GB"
    total_gb_display.short_description = 'Квота'
    
    def usage_percent_display(self, obj):
        """Процент использования"""
        percent = obj.usage_percent
        if percent >= 90:
            color = 'red'
        elif percent >= 80:
            color = 'orange'
        else:
            color = 'green'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
            color,
            percent
        )
    usage_percent_display.short_description = 'Использование'
    
    def available_gb_display(self, obj):
        """Доступно ГБ"""
        return f"{obj.available_gb:.2f} GB"
    available_gb_display.short_description = 'Доступно'
    
    actions = ['reset_warnings', 'add_5gb_quota', 'add_10gb_quota']
    
    def reset_warnings(self, request, queryset):
        """Сбросить предупреждения"""
        queryset.update(warning_sent=False, last_warning_at=None)
        self.message_user(request, f"Предупреждения сброшены для {queryset.count()} записей")
    reset_warnings.short_description = "Сбросить предупреждения"
    
    def add_5gb_quota(self, request, queryset):
        """Добавить 5 ГБ к квоте"""
        for quota in queryset:
            quota.increase_quota(5)
        self.message_user(request, f"Добавлено 5 ГБ к {queryset.count()} записям")
    add_5gb_quota.short_description = "Добавить 5 ГБ"
    
    def add_10gb_quota(self, request, queryset):
        """Добавить 10 ГБ к квоте"""
        for quota in queryset:
            quota.increase_quota(10)
        self.message_user(request, f"Добавлено 10 ГБ к {queryset.count()} записям")
    add_10gb_quota.short_description = "Добавить 10 ГБ"


@admin.register(LessonMaterial)
class LessonMaterialAdmin(admin.ModelAdmin):
    list_display = ('title', 'lesson', 'material_type', 'uploaded_by', 'views_count', 'file_size_display', 'uploaded_at')
    list_filter = ('material_type', 'uploaded_at')
    search_fields = ('title', 'lesson__title', 'uploaded_by__email')
    readonly_fields = ('uploaded_at', 'views_count', 'file_size_mb')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('lesson', 'material_type', 'title', 'description')
        }),
        ('Файл', {
            'fields': ('file_url', 'file_name', 'file_size_bytes', 'file_size_mb')
        }),
        ('Метаданные', {
            'fields': ('uploaded_by', 'uploaded_at', 'views_count')
        }),
    )
    
    def file_size_display(self, obj):
        """Отображение размера файла в MB"""
        return f"{obj.file_size_mb:.2f} MB"
    file_size_display.short_description = 'Размер'


@admin.register(MaterialView)
class MaterialViewAdmin(admin.ModelAdmin):
    list_display = ('student', 'material', 'viewed_at', 'duration_display', 'completed')
    list_filter = ('completed', 'viewed_at', 'material__material_type')
    search_fields = ('student__email', 'student__first_name', 'student__last_name', 'material__title')
    readonly_fields = ('viewed_at',)
    
    fieldsets = (
        ('Информация о просмотре', {
            'fields': ('material', 'student', 'viewed_at')
        }),
        ('Метрики', {
            'fields': ('duration_seconds', 'completed')
        }),
    )
    
    def duration_display(self, obj):
        """Отображение длительности в минутах"""
        minutes = obj.duration_seconds // 60
        seconds = obj.duration_seconds % 60
        return f"{minutes}м {seconds}с" if minutes > 0 else f"{seconds}с"
    duration_display.short_description = 'Длительность'


from django.utils.html import format_html
