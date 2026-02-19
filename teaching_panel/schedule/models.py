from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class ZoomAccount(models.Model):
    """Пул Zoom аккаунтов для распределения лицензий"""
    
    name = models.CharField(_('название аккаунта'), max_length=200, help_text=_('Например: Zoom License 1'))
    api_key = models.CharField(_('API ключ'), max_length=255)
    api_secret = models.CharField(_('API секрет'), max_length=255)
    zoom_user_id = models.CharField(_('Zoom User ID'), max_length=255)
    
    is_busy = models.BooleanField(_('занят'), default=False, db_index=True)
    current_lesson = models.OneToOneField(
        'Lesson',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='active_zoom_account',
        verbose_name=_('текущее занятие')
    )
    
    created_at = models.DateTimeField(_('дата создания'), auto_now_add=True)
    updated_at = models.DateTimeField(_('дата обновления'), auto_now=True)
    
    class Meta:
        verbose_name = _('Zoom аккаунт')
        verbose_name_plural = _('Zoom аккаунты')
        ordering = ['name']
    
    def __str__(self):
        status = 'Занят' if self.is_busy else 'Свободен'
        return f"{self.name} ({status})"


class Group(models.Model):
    """Учебная группа"""
    
    name = models.CharField(_('название группы'), max_length=200)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='teaching_groups',
        limit_choices_to={'role': 'teacher'},
        verbose_name=_('преподаватель')
    )
    students = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='enrolled_groups',
        limit_choices_to={'role': 'student'},
        blank=True,
        verbose_name=_('студенты')
    )
    description = models.TextField(_('описание'), blank=True)
    invite_code = models.CharField(
        _('код приглашения'),
        max_length=8,
        unique=True,
        blank=True,
        null=True,
        help_text=_('Уникальный код для присоединения учеников к группе')
    )
    created_at = models.DateTimeField(_('дата создания'), auto_now_add=True)
    updated_at = models.DateTimeField(_('дата обновления'), auto_now=True)
    
    class Meta:
        verbose_name = _('группа')
        verbose_name_plural = _('группы')
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.teacher.get_full_name()})"
    
    def student_count(self):
        """Количество студентов в группе"""
        return self.students.count()
    
    def generate_invite_code(self):
        """Генерирует уникальный код приглашения"""
        import random
        import string
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not Group.objects.filter(invite_code=code).exists():
                self.invite_code = code
                self.save(update_fields=['invite_code'])
                return code
    
    def save(self, *args, **kwargs):
        # Генерация invite_code если он отсутствует (как для новых, так и для старых записей)
        if not self.invite_code:
            import random
            import string
            while True:
                code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                if not Group.objects.filter(invite_code=code).exists():
                    self.invite_code = code
                    break
        super().save(*args, **kwargs)


class Lesson(models.Model):
    """Занятие (урок)"""
    
    title = models.CharField(_('название'), max_length=200)
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='lessons',
        verbose_name=_('группа')
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='teaching_lessons',
        limit_choices_to={'role': 'teacher'},
        verbose_name=_('преподаватель')
    )
    start_time = models.DateTimeField(_('время начала'))
    end_time = models.DateTimeField(_('время окончания'))
    
    topics = models.TextField(
        _('темы урока'), 
        blank=True,
        help_text=_('Темы, которые будут рассмотрены на уроке')
    )
    
    location = models.CharField(
        _('место проведения'), 
        max_length=300,
        blank=True,
        help_text=_('Адрес или название аудитории')
    )
    
    # Интеграция с пулом Zoom аккаунтов
    zoom_meeting_id = models.CharField(_('ID встречи Zoom'), max_length=100, blank=True, null=True)
    zoom_start_url = models.URLField(_('ссылка для запуска (преподаватель)'), blank=True, null=True)
    zoom_join_url = models.URLField(_('ссылка для входа (студенты)'), blank=True, null=True)
    zoom_password = models.CharField(_('пароль Zoom'), max_length=50, blank=True, null=True)
    
    # Связь с новым пулом Zoom аккаунтов (zoom_pool app)
    zoom_account = models.ForeignKey(
        'zoom_pool.ZoomAccount',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_lessons',
        verbose_name=_('назначенный Zoom аккаунт')
    )
    
    # Старое поле для совместимости (deprecated)
    zoom_account_used = models.ForeignKey(
        'ZoomAccount',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lessons_history',
        verbose_name=_('использованный Zoom аккаунт (старое)')
    )
    
    notes = models.TextField(_('заметки'), blank=True)
    created_at = models.DateTimeField(_('дата создания'), auto_now_add=True)
    updated_at = models.DateTimeField(_('дата обновления'), auto_now=True)
    
    class Meta:
        verbose_name = _('занятие')
        verbose_name_plural = _('занятия')
        ordering = ['start_time']
        indexes = [
            models.Index(fields=['start_time']),
            models.Index(fields=['teacher', 'start_time']),
            models.Index(fields=['group', 'start_time'])
        ]
    
    def __str__(self):
        return f"{self.title} - {self.group.name} ({self.start_time.strftime('%d.%m.%Y %H:%M')})"
    
    def duration(self):
        """Длительность урока в минутах"""
        return int((self.end_time - self.start_time).total_seconds() / 60)

    def clean(self):
        """Приводим времена к aware и базовая валидация."""
        if self.start_time and timezone.is_naive(self.start_time):
            self.start_time = timezone.make_aware(self.start_time, timezone.get_current_timezone())
        if self.end_time and timezone.is_naive(self.end_time):
            self.end_time = timezone.make_aware(self.end_time, timezone.get_current_timezone())
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            from django.core.exceptions import ValidationError
            raise ValidationError({'end_time': _('время окончания должно быть позже начала')})

    def save(self, *args, **kwargs):
        # Ensure clean runs for programmatic creates (e.g. tests)
        self.clean()
        super().save(*args, **kwargs)


class LessonRecording(models.Model):
    """Запись урока (ссылка на облачную запись Zoom + архив)"""
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name='recordings',
        verbose_name=_('урок')
    )
    
    zoom_recording_id = models.CharField(_('ID записи Zoom'), max_length=100, blank=True, default='')
    download_url = models.URLField(_('ссылка для скачивания'), blank=True)
    play_url = models.URLField(_('ссылка для просмотра'), blank=True)
    
    # Архивирование в S3/Azure Blob
    archive_url = models.URLField(
        _('архивная ссылка'),
        blank=True,
        help_text='Постоянная ссылка на запись в облачном хранилище (S3/Azure Blob)'
    )
    archive_key = models.CharField(
        _('ключ в хранилище'),
        max_length=500,
        blank=True,
        help_text='Путь к файлу в S3/Azure: recordings/{lesson_id}/{recording_id}.mp4'
    )
    archived_at = models.DateTimeField(
        _('дата архивирования'),
        null=True,
        blank=True
    )
    archive_size_bytes = models.BigIntegerField(
        _('размер архива'),
        null=True,
        blank=True
    )
    
    file_size = models.BigIntegerField(_('размер файла (байты)'), null=True, blank=True)
    duration = models.IntegerField(_('длительность (секунды)'), null=True, blank=True)
    recording_start = models.DateTimeField(_('начало записи'), null=True, blank=True)
    recording_end = models.DateTimeField(_('окончание записи'), null=True, blank=True)
    
    status = models.CharField(
        _('статус'),
        max_length=20,
        choices=[
            ('processing', _('Обрабатывается')),
            ('completed', _('Готова')),
            ('archived', _('Архивирована')),
            ('failed', _('Ошибка')),
        ],
        default='processing'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('запись урока')
        verbose_name_plural = _('записи уроков')
        ordering = ['-created_at']

    def __str__(self):
        return f"Recording for {self.lesson.title} ({self.created_at.strftime('%d.%m.%Y %H:%M')})"


class Attendance(models.Model):
    """Посещаемость студента на занятии"""
    
    STATUS_CHOICES = (
        ('present', 'Присутствовал'),
        ('absent', 'Отсутствовал'),
        ('excused', 'Уважительная причина'),
    )
    
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name='attendances',
        verbose_name=_('занятие')
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='attendances',
        limit_choices_to={'role': 'student'},
        verbose_name=_('студент')
    )
    status = models.CharField(
        _('статус'), 
        max_length=10, 
        choices=STATUS_CHOICES,
        default='absent'
    )
    notes = models.TextField(_('заметки'), blank=True)
    marked_at = models.DateTimeField(_('время отметки'), auto_now=True)
    
    class Meta:
        verbose_name = _('посещаемость')
        verbose_name_plural = _('посещаемость')
        unique_together = ['lesson', 'student']
        ordering = ['lesson__start_time']
        indexes = [
            models.Index(fields=['lesson', 'student']),
            models.Index(fields=['student', 'status'])
        ]
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.lesson.title} ({self.get_status_display()})"


class RecurringLesson(models.Model):
    """Регулярное (повторяющееся) занятие"""
    
    WEEK_TYPE_CHOICES = (
        ('ALL', 'Каждая неделя'),
        ('UPPER', 'Верхняя неделя'),
        ('LOWER', 'Нижняя неделя'),
    )
    
    DAY_OF_WEEK_CHOICES = (
        (0, 'Понедельник'),
        (1, 'Вторник'),
        (2, 'Среда'),
        (3, 'Четверг'),
        (4, 'Пятница'),
        (5, 'Суббота'),
        (6, 'Воскресенье'),
    )
    
    title = models.CharField(_('название'), max_length=200)
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='recurring_lessons',
        verbose_name=_('группа')
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recurring_teaching_lessons',
        limit_choices_to={'role': 'teacher'},
        verbose_name=_('преподаватель')
    )
    
    day_of_week = models.IntegerField(
        _('день недели'),
        choices=DAY_OF_WEEK_CHOICES,
        help_text=_('0 = Понедельник, 6 = Воскресенье')
    )
    week_type = models.CharField(
        _('тип недели'),
        max_length=10,
        choices=WEEK_TYPE_CHOICES,
        default='ALL',
        help_text=_('Для семестров с чередованием недель')
    )
    
    start_time = models.TimeField(_('время начала'))
    end_time = models.TimeField(_('время окончания'))
    
    start_date = models.DateField(_('дата начала действия'))
    end_date = models.DateField(_('дата окончания действия'))
    
    topics = models.TextField(
        _('темы урока'),
        blank=True,
        help_text=_('Стандартные темы для этого регулярного урока')
    )
    
    location = models.CharField(
        _('место проведения'),
        max_length=300,
        blank=True,
        help_text=_('Адрес или название аудитории')
    )
    
    created_at = models.DateTimeField(_('дата создания'), auto_now_add=True)
    updated_at = models.DateTimeField(_('дата обновления'), auto_now=True)
    
    class Meta:
        verbose_name = _('регулярное занятие')
        verbose_name_plural = _('регулярные занятия')
        ordering = ['day_of_week', 'start_time']
        indexes = [
            models.Index(fields=['teacher', 'day_of_week']),
            models.Index(fields=['group', 'day_of_week'])
        ]
    
    def __str__(self):
        day_name = dict(self.DAY_OF_WEEK_CHOICES)[self.day_of_week]
        week_type = dict(self.WEEK_TYPE_CHOICES)[self.week_type]
        return f"{self.title} - {day_name} {self.start_time.strftime('%H:%M')} ({week_type})"


class IndividualInviteCode(models.Model):
    """Индивидуальный инвайт-код для приглашения одного ученика"""

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='individual_invite_codes',
        limit_choices_to={'role': 'teacher'},
        verbose_name=_('преподаватель'),
    )
    subject = models.CharField(
        _('предмет'), max_length=200,
        help_text='Название предмета/дисциплины',
    )
    invite_code = models.CharField(
        _('код приглашения'), max_length=8, unique=True, db_index=True,
        help_text='Уникальный 8-символьный код для приглашения одного ученика',
    )
    is_used = models.BooleanField(
        _('использован'), default=False, db_index=True,
        help_text='Был ли код использован для приглашения ученика',
    )
    used_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='joined_individual_subjects',
        limit_choices_to={'role': 'student'},
        verbose_name=_('использован учеником'),
    )
    used_at = models.DateTimeField(_('дата использования'), null=True, blank=True)
    created_at = models.DateTimeField(_('дата создания'), auto_now_add=True)

    class Meta:
        verbose_name = _('индивидуальный инвайт-код')
        verbose_name_plural = _('индивидуальные инвайт-коды')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['teacher', 'is_used'], name='schedule_in_teacher_7762a6_idx'),
            models.Index(fields=['used_by'], name='schedule_in_used_by_6295cc_idx'),
            models.Index(fields=['invite_code'], name='schedule_in_invite__befbc6_idx'),
        ]

    def __str__(self):
        status = 'использован' if self.is_used else 'активен'
        return f"{self.invite_code} ({self.subject}) — {status}"


class AuditLog(models.Model):
    """Журнал аудита действий пользователей"""
    
    ACTION_CHOICES = [
        ('lesson_start', 'Запуск урока'),
        ('lesson_create', 'Создание урока'),
        ('lesson_update', 'Обновление урока'),
        ('lesson_delete', 'Удаление урока'),
        ('zoom_account_acquire', 'Захват Zoom аккаунта'),
        ('zoom_account_release', 'Освобождение Zoom аккаунта'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs',
        verbose_name=_('пользователь')
    )
    action = models.CharField(_('действие'), max_length=50, choices=ACTION_CHOICES)
    resource_type = models.CharField(_('тип ресурса'), max_length=50)
    resource_id = models.IntegerField(_('ID ресурса'), null=True, blank=True)
    ip_address = models.GenericIPAddressField(_('IP адрес'), null=True, blank=True)
    user_agent = models.TextField(_('User Agent'), blank=True)
    details = models.JSONField(_('детали'), default=dict, blank=True)
    timestamp = models.DateTimeField(_('время'), auto_now_add=True, db_index=True)
    
    class Meta:
        verbose_name = _('запись аудита')
        verbose_name_plural = _('записи аудита')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
            models.Index(fields=['resource_type', 'resource_id']),
        ]
    
    def __str__(self):
        user_email = self.user.email if self.user else 'Неизвестный'
        action_display = dict(self.ACTION_CHOICES).get(self.action, self.action)
        return f"{user_email} - {action_display} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

