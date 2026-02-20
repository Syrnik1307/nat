from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
import uuid

"""Core domain models.

Duplicate educational entities (Lesson, Assignment, Submission) were moved to dedicated
apps: schedule (for lessons with Zoom pooling) and homework (for assignments & submissions).
This module now keeps only Course for high-level grouping. Migration will drop old tables.
"""


class Course(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('published', 'Опубликован'),
        ('archived', 'В архиве'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    short_description = models.CharField(max_length=500, blank=True, verbose_name='Краткое описание')
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='courses_taught')
    students = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='courses_enrolled', blank=True)
    cover_url = models.URLField(blank=True, verbose_name='URL обложки')
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Цена (₽)')
    duration = models.CharField(max_length=50, blank=True, verbose_name='Длительность (напр. "6 часов")')
    is_published = models.BooleanField(default=False, verbose_name='Опубликован')
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='draft',
        db_index=True, verbose_name='Статус',
    )
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        null=True, blank=True, related_name='courses',
        verbose_name='Тенант',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'курс'
        verbose_name_plural = 'курсы'

    def __str__(self):
        return self.title


class AuditLog(models.Model):
    """
    Журнал аудита действий пользователей в системе
    """
    ACTION_CHOICES = [
        ('create', 'Создание'),
        ('update', 'Обновление'),
        ('delete', 'Удаление'),
        ('grade', 'Выставление оценки'),
        ('submit', 'Отправка работы'),
        ('view', 'Просмотр'),
        ('login', 'Вход в систему'),
        ('logout', 'Выход из системы'),
        ('other', 'Другое'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='core_audit_logs',  # Изменено чтобы избежать конфликта
        help_text='Пользователь, совершивший действие'
    )
    
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        db_index=True,
        help_text='Тип действия'
    )
    
    # Generic FK для связи с любой моделью
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    description = models.TextField(
        blank=True,
        help_text='Описание действия'
    )
    
    # Дополнительные данные в JSON
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text='Дополнительные данные (JSON)'
    )
    
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text='IP адрес пользователя'
    )
    
    user_agent = models.TextField(
        blank=True,
        help_text='User agent браузера'
    )
    
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text='Время действия'
    )
    
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        null=True, blank=True, related_name='core_audit_logs_tenant',
        verbose_name='Тенант',
    )
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Аудит-лог'
        verbose_name_plural = 'Аудит-логи'
        indexes = [
            models.Index(fields=['user', 'action', '-timestamp'], name='audit_user_action_idx'),
            models.Index(fields=['content_type', 'object_id'], name='audit_content_idx'),
            models.Index(fields=['-timestamp'], name='audit_timestamp_idx'),
        ]
    
    def __str__(self):
        user_str = self.user.email if self.user else 'Anonymous'
        return f"{user_str} - {self.get_action_display()} at {self.timestamp}"
    
    @classmethod
    def log(cls, user, action, content_object=None, description='', metadata=None, request=None):
        """
        Удобный метод для создания лога
        
        Пример использования:
        AuditLog.log(
            user=request.user,
            action='grade',
            content_object=submission,
            description=f'Выставлена оценка {score}',
            metadata={'score': score, 'feedback': feedback},
            request=request
        )
        """
        log_data = {
            'user': user,
            'action': action,
            'description': description,
            'metadata': metadata or {},
        }
        
        if content_object:
            log_data['content_object'] = content_object
        
        if request:
            # Извлекаем IP и User-Agent из запроса
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0].strip()
            else:
                ip = request.META.get('REMOTE_ADDR')
            
            log_data['ip_address'] = ip
            log_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')[:500]
            
            # Tenant из middleware
            tenant = getattr(request, 'tenant', None)
            if tenant:
                log_data['tenant'] = tenant
        
        return cls.objects.create(**log_data)


# ══════════════════════════════════════════════════════════════════════════════
# Course modules, lessons, materials, access, progress
# ══════════════════════════════════════════════════════════════════════════════

class CourseModule(models.Model):
    """Модуль курса — группировка уроков."""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=300, verbose_name='Название модуля')
    description = models.TextField(blank=True, verbose_name='Описание модуля')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'модуль курса'
        verbose_name_plural = 'модули курса'
        ordering = ['order', 'id']

    def __str__(self):
        return f'{self.course.title} / {self.title}'


class CourseLesson(models.Model):
    """Урок курса."""
    VIDEO_PROVIDER_CHOICES = [
        ('local', 'Локальное хранилище'),
        ('kinescope', 'Kinescope'),
        ('external', 'Внешняя ссылка'),
    ]
    VIDEO_STATUS_CHOICES = [
        ('none', 'Нет видео'),
        ('uploading', 'Загружается'),
        ('processing', 'Обрабатывается'),
        ('ready', 'Готово'),
        ('error', 'Ошибка'),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons')
    module = models.ForeignKey(
        CourseModule, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='lessons', verbose_name='Модуль',
    )
    homework = models.ForeignKey(
        'homework.Homework', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='course_lessons', verbose_name='Домашнее задание',
    )
    title = models.CharField(max_length=300, verbose_name='Название урока')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')
    video_url = models.URLField(blank=True, verbose_name='Ссылка на видео')
    content = models.TextField(blank=True, verbose_name='Текстовый контент (HTML)')
    duration = models.CharField(max_length=50, blank=True, verbose_name='Длительность')
    is_free_preview = models.BooleanField(default=False, verbose_name='Бесплатный превью')
    # Kinescope integration (migration 0009)
    video_provider = models.CharField(
        max_length=20, choices=VIDEO_PROVIDER_CHOICES, default='local',
        verbose_name='Провайдер видео',
    )
    video_status = models.CharField(
        max_length=20, choices=VIDEO_STATUS_CHOICES, default='none',
        verbose_name='Статус видео',
    )
    kinescope_video_id = models.CharField(
        max_length=255, blank=True,
        verbose_name='Kinescope Video ID',
        help_text='ID видео в Kinescope (заполняется автоматически)',
    )
    kinescope_embed_url = models.URLField(
        max_length=1024, blank=True,
        verbose_name='Kinescope Embed URL',
        help_text='Embed-ссылка для плеера Kinescope',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'урок курса'
        verbose_name_plural = 'уроки курса'
        ordering = ['order', 'id']

    def __str__(self):
        return f'{self.course.title} / {self.title}'


class CourseLessonMaterial(models.Model):
    """Материал (файл) к уроку."""
    lesson = models.ForeignKey(CourseLesson, on_delete=models.CASCADE, related_name='materials')
    name = models.CharField(max_length=200, verbose_name='Название файла')
    url = models.URLField(verbose_name='Ссылка на файл')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'материал урока'
        verbose_name_plural = 'материалы урока'

    def __str__(self):
        return self.name


class CourseAccess(models.Model):
    """Доступ пользователя к курсу."""
    ACCESS_TYPE_CHOICES = [
        ('purchased', 'Покупка'),
        ('granted', 'Предоставлено'),
        ('trial', 'Пробный'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='course_accesses')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='accesses')
    access_type = models.CharField(max_length=20, choices=ACCESS_TYPE_CHOICES, default='purchased')
    granted_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name='Истекает')
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'доступ к курсу'
        verbose_name_plural = 'доступы к курсам'
        unique_together = [('user', 'course')]

    def __str__(self):
        return f'{self.user} → {self.course} ({self.access_type})'


class CourseLessonProgress(models.Model):
    """Прогресс ученика по конкретному уроку."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='lesson_progress')
    lesson = models.ForeignKey(CourseLesson, on_delete=models.CASCADE, related_name='progress_records')
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_position = models.PositiveIntegerField(default=0, verbose_name='Позиция видео (сек)')

    class Meta:
        verbose_name = 'прогресс по уроку'
        verbose_name_plural = 'прогресс по урокам'
        unique_together = [('user', 'lesson')]

    def __str__(self):
        return f'{self.user} / {self.lesson} ({"✓" if self.completed else "..."})'


# ══════════════════════════════════════════════════════════════════════════════
# Protected Content & Access Sessions (migrations 0004, 0005, 0008)
# ══════════════════════════════════════════════════════════════════════════════

class ProtectedContent(models.Model):
    """Защищённый контент (видео/материалы) с водяным знаком и сессионным доступом."""
    title = models.CharField(max_length=255, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    yandex_embed_url = models.URLField(max_length=1024, verbose_name='URL для iframe (Яндекс Диск)')
    yandex_public_url = models.URLField(max_length=1024, blank=True, verbose_name='Публичная ссылка (опционально)')
    group = models.ForeignKey(
        'schedule.Group', on_delete=models.CASCADE,
        null=True, blank=True, related_name='protected_contents',
        verbose_name='Группа',
    )
    lesson = models.OneToOneField(
        CourseLesson, on_delete=models.CASCADE,
        null=True, blank=True, related_name='protected_content',
        verbose_name='Урок курса',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_protected_contents',
        verbose_name='Создатель',
    )
    is_active = models.BooleanField(default=True, db_index=True, verbose_name='Активен')
    watermark_enabled = models.BooleanField(default=True, verbose_name='Водяной знак включен')
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        null=True, blank=True, related_name='protected_contents',
        verbose_name='Тенант',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')

    class Meta:
        verbose_name = 'Защищённый контент'
        verbose_name_plural = 'Защищённый контент'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class ContentAccessSession(models.Model):
    """Сессия доступа к защищённому контенту."""
    STATUS_CHOICES = [
        ('active', 'Активна'),
        ('blocked', 'Заблокирована'),
        ('ended', 'Завершена'),
        ('expired', 'Истекла'),
    ]

    content = models.ForeignKey(
        ProtectedContent, on_delete=models.CASCADE,
        related_name='access_sessions', verbose_name='Контент',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='content_access_sessions', verbose_name='Пользователь',
    )
    session_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', db_index=True)
    risk_score = models.PositiveIntegerField(default=0)
    block_reason = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        null=True, blank=True, related_name='content_access_sessions',
        verbose_name='Тенант',
    )
    started_at = models.DateTimeField(auto_now_add=True, db_index=True)
    last_heartbeat_at = models.DateTimeField(null=True, blank=True)
    blocked_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(db_index=True)

    class Meta:
        verbose_name = 'Сессия доступа к контенту'
        verbose_name_plural = 'Сессии доступа к контенту'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['user', 'status', '-started_at'], name='content_session_user_idx'),
            models.Index(fields=['content', 'status'], name='content_session_content_idx'),
        ]

    def __str__(self):
        return f'Session {self.session_token} ({self.status})'


class ContentSecurityEvent(models.Model):
    """Событие безопасности во время сессии доступа к контенту."""
    # Event type constants
    EVENT_TAB_HIDDEN = 'tab_hidden'
    EVENT_WINDOW_BLUR = 'window_blur'
    EVENT_FULLSCREEN_EXITED = 'fullscreen_exited'
    EVENT_PRINT_SCREEN = 'print_screen_pressed'
    EVENT_DEVTOOLS_OPENED = 'devtools_opened'
    EVENT_SCREEN_RECORDING_SUSPECTED = 'screen_recording_suspected'
    EVENT_DISPLAY_CAPTURE_DETECTED = 'display_capture_detected'
    EVENT_MULTIPLE_SCREENS = 'multiple_screens_detected'
    EVENT_WATERMARK_TAMPER = 'watermark_tamper_detected'
    EVENT_NETWORK_PROXY = 'network_proxy_detected'
    EVENT_HEARTBEAT_ANOMALY = 'heartbeat_anomaly'

    EVENT_TYPE_CHOICES = [
        (EVENT_TAB_HIDDEN, 'Tab hidden'),
        (EVENT_WINDOW_BLUR, 'Window blur'),
        (EVENT_FULLSCREEN_EXITED, 'Fullscreen exited'),
        (EVENT_PRINT_SCREEN, 'Print screen pressed'),
        (EVENT_DEVTOOLS_OPENED, 'Devtools opened'),
        (EVENT_SCREEN_RECORDING_SUSPECTED, 'Screen recording suspected'),
        (EVENT_DISPLAY_CAPTURE_DETECTED, 'Display capture detected'),
        (EVENT_MULTIPLE_SCREENS, 'Multiple screens detected'),
        (EVENT_WATERMARK_TAMPER, 'Watermark tamper detected'),
        (EVENT_NETWORK_PROXY, 'Network proxy detected'),
        (EVENT_HEARTBEAT_ANOMALY, 'Heartbeat anomaly'),
    ]
    EVENT_CHOICES = EVENT_TYPE_CHOICES  # Alias for serializers

    # Severity constants
    SEVERITY_INFO = 'info'
    SEVERITY_WARNING = 'warning'
    SEVERITY_CRITICAL = 'critical'

    SEVERITY_CHOICES = [
        (SEVERITY_INFO, 'Info'),
        (SEVERITY_WARNING, 'Warning'),
        (SEVERITY_CRITICAL, 'Critical'),
    ]

    session = models.ForeignKey(
        ContentAccessSession, on_delete=models.CASCADE,
        related_name='security_events', verbose_name='Сессия',
    )
    event_type = models.CharField(max_length=64, choices=EVENT_TYPE_CHOICES, db_index=True)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='info')
    score_delta = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Событие безопасности контента'
        verbose_name_plural = 'События безопасности контента'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['session', '-created_at'], name='content_event_session_idx'),
            models.Index(fields=['event_type', '-created_at'], name='content_event_type_idx'),
        ]

    def __str__(self):
        return f'{self.event_type} ({self.severity}) @ {self.created_at}'
