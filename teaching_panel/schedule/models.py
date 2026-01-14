from django.db import models
from django.db import IntegrityError, transaction
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.auth import get_user_model


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
        """Генерирует уникальный код приглашения.

        Гарантия уникальности внутри таблицы обеспечивается `unique=True`.
        Для кросс-табличной уникальности (Group vs IndividualInviteCode)
        используем префикс `G` и дополнительно проверяем старые/наследованные коды.
        """
        import secrets
        import string

        old_code = (self.invite_code or '').strip().upper() if self.invite_code else ''
        alphabet = string.ascii_uppercase + string.digits

        # Дизайн-уникальность: группы начинаются с G
        prefix = 'G'
        max_attempts = 64

        update_fields = ['invite_code']
        for _ in range(max_attempts):
            candidate = prefix + ''.join(secrets.choice(alphabet) for _ in range(7))
            if candidate == old_code:
                continue

            # Защита от редкого конфликта с legacy-кодами из другой таблицы
            if IndividualInviteCode.objects.filter(invite_code=candidate).exists():
                continue

            self.invite_code = candidate
            try:
                with transaction.atomic():
                    self.save(update_fields=update_fields)
                return candidate
            except IntegrityError:
                # Коллизия в таблице Group (гонка/редкий случай) — пробуем снова
                continue

        raise IntegrityError('Не удалось сгенерировать уникальный invite_code для группы')
    
    def save(self, *args, **kwargs):
        # Генерация invite_code если он отсутствует (как для новых, так и для старых записей)
        if self.invite_code:
            return super().save(*args, **kwargs)

        import secrets
        import string

        alphabet = string.ascii_uppercase + string.digits
        prefix = 'G'
        max_attempts = 64

        update_fields = kwargs.get('update_fields')
        if update_fields is not None:
            update_fields = set(update_fields)
            update_fields.add('invite_code')
            kwargs['update_fields'] = list(update_fields)

        for _ in range(max_attempts):
            candidate = prefix + ''.join(secrets.choice(alphabet) for _ in range(7))

            # Защита от редкого конфликта с legacy-кодами из другой таблицы
            if IndividualInviteCode.objects.filter(invite_code=candidate).exists():
                continue

            self.invite_code = candidate
            try:
                with transaction.atomic():
                    return super().save(*args, **kwargs)
            except IntegrityError:
                # Коллизия по unique внутри Group — повторяем
                self.invite_code = None
                continue

        raise IntegrityError('Не удалось сгенерировать уникальный invite_code для группы')


class Lesson(models.Model):
    """Занятие (урок)"""
    
    title = models.CharField(_('название'), max_length=200, blank=True, default='')
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
    zoom_start_url = models.URLField(_('ссылка для запуска (преподаватель)'), max_length=1000, blank=True, null=True)
    zoom_join_url = models.URLField(_('ссылка для входа (студенты)'), max_length=500, blank=True, null=True)
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
    
    # Флаг быстрого урока (не показывается в расписании)
    is_quick_lesson = models.BooleanField(
        _('быстрый урок'),
        default=False,
        help_text=_('Урок создан через "Быстрый урок" и не должен отображаться в расписании')
    )
    
    # Настройка записи урока
    record_lesson = models.BooleanField(
        _('записывать урок'),
        default=False,
        help_text=_('Автоматически записывать урок в Zoom и сохранять в Google Drive')
    )
    recording_available_for_days = models.IntegerField(
        _('доступность записи (дней)'),
        default=90,
        help_text=_('Сколько дней запись будет доступна ученикам (0 = бессрочно)')
    )
    
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
        display = self.display_name
        return f"{display} ({self.start_time.strftime('%d.%m.%Y %H:%M')})"
    
    @property
    def display_name(self):
        """Название для отображения: тема урока или имя группы"""
        if self.title and self.title.strip():
            return self.title.strip()
        return self.group.name if self.group else 'Урок'
    
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

    class Visibility(models.TextChoices):
        LESSON_GROUP = 'lesson_group', _('Только группа урока')
        ALL_TEACHER_GROUPS = 'all_teacher_groups', _('Все группы преподавателя')
        CUSTOM_GROUPS = 'custom_groups', _('Выбранные группы')
        CUSTOM_STUDENTS = 'custom_students', _('Выбранные ученики')

    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name='recordings',
        verbose_name=_('урок'),
        null=True,
        blank=True,
        help_text=_('Урок, к которому привязана запись (может быть пустым для standalone записей)')
    )

    # Владелец записи (для standalone записей, у которых lesson=None)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_recordings',
        verbose_name=_('преподаватель'),
        null=True,
        blank=True,
        limit_choices_to={'role': 'teacher'},
        help_text=_('Преподаватель-владелец записи (для standalone записей)')
    )

    # Standalone-записи не имеют урока, поэтому сохраняем их название отдельно
    title = models.CharField(
        _('название'),
        max_length=255,
        blank=True,
        default='',
        help_text=_('Название standalone видео (если запись не привязана к уроку)')
    )
    
    zoom_recording_id = models.CharField(_('ID записи Zoom'), max_length=100, blank=True, default='')
    download_url = models.URLField(_('ссылка для скачивания'), blank=True)
    play_url = models.URLField(_('ссылка для просмотра'), blank=True)
    recording_type = models.CharField(
        _('тип записи'),
        max_length=50,
        default='shared_screen_with_speaker_view',
        help_text='Тип Zoom записи: shared_screen_with_speaker_view, audio_only и т.д.'
    )
    
    # Архивирование в Google Drive / S3 / Azure Blob
    storage_provider = models.CharField(
        _('провайдер хранилища'),
        max_length=20,
        choices=[
            ('gdrive', 'Google Drive'),
            ('s3', 'AWS S3'),
            ('azure', 'Azure Blob'),
            ('local', 'Локальное хранилище')
        ],
        default='gdrive'
    )
    archive_url = models.URLField(
        _('архивная ссылка'),
        blank=True,
        help_text='Постоянная ссылка на запись в облачном хранилище'
    )
    archive_key = models.CharField(
        _('ключ в хранилище'),
        max_length=500,
        blank=True,
        help_text='ID файла в Google Drive или путь в S3/Azure'
    )
    gdrive_file_id = models.CharField(
        _('Google Drive File ID'),
        max_length=100,
        blank=True,
        help_text='Уникальный ID файла в Google Drive для прямого доступа'
    )
    gdrive_folder_id = models.CharField(
        _('Google Drive Folder ID'),
        max_length=100,
        blank=True,
        help_text='ID папки в Google Drive где хранится запись'
    )
    thumbnail_url = models.URLField(
        _('превью записи'),
        blank=True,
        help_text='Ссылка на миниатюру/обложку видео'
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
            ('ready', _('Готова')),
            ('archived', _('Архивирована')),
            ('failed', _('Ошибка')),
            ('deleted', _('Удалена')),
        ],
        default='processing'
    )

    visibility = models.CharField(
        _('видимость'),
        max_length=32,
        choices=Visibility.choices,
        default=Visibility.LESSON_GROUP,
        help_text=_('Определяет, кому доступна запись')
    )
    allowed_groups = models.ManyToManyField(
        Group,
        related_name='recording_access',
        blank=True,
        verbose_name=_('доступные группы')
    )
    allowed_students = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='recording_access',
        blank=True,
        limit_choices_to={'role': 'student'},
        verbose_name=_('доступные студенты')
    )
    
    # Доступность
    available_until = models.DateTimeField(
        _('доступна до'),
        null=True,
        blank=True,
        help_text=_('Дата автоматического удаления записи')
    )
    views_count = models.IntegerField(
        _('количество просмотров'),
        default=0,
        help_text=_('Сколько раз запись была просмотрена')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('запись урока')
        verbose_name_plural = _('записи уроков')
        ordering = ['-created_at']

    def __str__(self):
        if self.lesson_id and self.lesson:
            name = self.lesson.title or 'Урок'
        else:
            name = self.title or 'Standalone видео'
        return f"Recording: {name} ({self.created_at.strftime('%d.%m.%Y %H:%M')})"

    def ensure_base_group_access(self):
        """Убеждаемся, что базовая группа урока всегда имеет доступ."""
        if self.lesson_id and self.lesson and self.lesson.group_id:
            if not self.allowed_groups.filter(id=self.lesson.group_id).exists():
                self.allowed_groups.add(self.lesson.group)

    def apply_privacy(self, privacy_type=None, group_ids=None, student_ids=None, teacher=None):
        """Применяет настройки приватности к записи."""
        visibility_map = {
            None: self.Visibility.LESSON_GROUP,
            'lesson_group': self.Visibility.LESSON_GROUP,
            self.Visibility.LESSON_GROUP: self.Visibility.LESSON_GROUP,
            'all': self.Visibility.ALL_TEACHER_GROUPS,
            self.Visibility.ALL_TEACHER_GROUPS: self.Visibility.ALL_TEACHER_GROUPS,
            'groups': self.Visibility.CUSTOM_GROUPS,
            self.Visibility.CUSTOM_GROUPS: self.Visibility.CUSTOM_GROUPS,
            'students': self.Visibility.CUSTOM_STUDENTS,
            self.Visibility.CUSTOM_STUDENTS: self.Visibility.CUSTOM_STUDENTS,
        }
        resolved_visibility = visibility_map.get(privacy_type, self.Visibility.LESSON_GROUP)

        teacher = teacher or (self.lesson.teacher if self.lesson_id and self.lesson else None)

        def _clean_ids(values):
            cleaned = []
            if not values:
                return cleaned
            for value in values:
                try:
                    cleaned.append(int(value))
                except (TypeError, ValueError):
                    continue
            return cleaned

        group_ids = set(_clean_ids(group_ids))
        student_ids = set(_clean_ids(student_ids))

        if self.lesson_id and self.lesson and self.lesson.group_id:
            group_ids.add(self.lesson.group_id)

        self.visibility = resolved_visibility
        self.save(update_fields=['visibility'])

        if resolved_visibility == self.Visibility.ALL_TEACHER_GROUPS:
            # Достаточно хранить базовую группу как fallback
            if group_ids:
                base_groups = Group.objects.filter(id__in=group_ids)
                self.allowed_groups.set(base_groups)
            else:
                self.allowed_groups.clear()
            self.allowed_students.clear()
            return

        if resolved_visibility == self.Visibility.CUSTOM_GROUPS:
            group_qs = Group.objects.filter(id__in=group_ids)
            if teacher:
                group_qs = group_qs.filter(teacher=teacher)
            self.allowed_groups.set(group_qs)
            self.allowed_students.clear()
            return

        if resolved_visibility == self.Visibility.CUSTOM_STUDENTS:
            UserModel = get_user_model()
            students_qs = UserModel.objects.filter(id__in=student_ids, role='student')
            if group_ids:
                base_groups = Group.objects.filter(id__in=group_ids)
                self.allowed_groups.set(base_groups)
            else:
                self.allowed_groups.clear()
            self.allowed_students.set(students_qs)
            return

        # По умолчанию запись доступна только базовой группе
        if group_ids:
            base_groups = Group.objects.filter(id__in=group_ids)
            self.allowed_groups.set(base_groups)
        else:
            self.allowed_groups.clear()
        self.allowed_students.clear()


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
    
    title = models.CharField(_('название'), max_length=200, blank=True, default='')
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
    
    # ===== Telegram-уведомления =====
    telegram_notify_enabled = models.BooleanField(
        _('Telegram-уведомления'),
        default=False,
        help_text=_('Отправлять уведомления о начале урока')
    )
    
    telegram_notify_minutes = models.PositiveIntegerField(
        _('За сколько минут'),
        default=10,
        help_text=_('За сколько минут до начала отправлять уведомление (5, 10, 15, 30)')
    )
    
    telegram_notify_to_group = models.BooleanField(
        _('В группу'),
        default=True,
        help_text=_('Отправлять уведомление в Telegram-группу')
    )
    
    telegram_notify_to_students = models.BooleanField(
        _('В личку'),
        default=False,
        help_text=_('Отправлять личные сообщения ученикам')
    )
    
    telegram_group_chat_id = models.CharField(
        _('Chat ID Telegram-группы'),
        max_length=50,
        blank=True,
        default='',
        help_text=_('ID группы в Telegram (бот должен быть добавлен в группу)')
    )
    
    # Анонс урока (опционально)
    telegram_announce_enabled = models.BooleanField(
        _('Анонс урока'),
        default=False,
        help_text=_('Отправлять анонс заранее (утром в день урока)')
    )
    
    telegram_announce_time = models.TimeField(
        _('Время анонса'),
        null=True,
        blank=True,
        default=None,
        help_text=_('Во сколько отправить анонс в день урока')
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
        display = self.display_name
        return f"{display} - {day_name} {self.start_time.strftime('%H:%M')} ({week_type})"
    
    @property
    def display_name(self):
        """Название для отображения: тема урока или имя группы"""
        if self.title and self.title.strip():
            return self.title.strip()
        return self.group.name if self.group else 'Урок'


class TeacherStorageQuota(models.Model):
    """Квота хранилища для записей уроков преподавателя"""
    
    teacher = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='storage_quota',
        limit_choices_to={'role': 'teacher'},
        verbose_name=_('преподаватель')
    )
    
    # Квоты в байтах
    total_quota_bytes = models.BigIntegerField(
        _('общая квота (байты)'),
        default=5368709120,  # 5 GB по умолчанию
        help_text=_('Общий лимит хранилища в байтах')
    )
    used_bytes = models.BigIntegerField(
        _('использовано (байты)'),
        default=0,
        help_text=_('Фактически использованный объем')
    )
    
    # Дополнительные метрики
    recordings_count = models.IntegerField(
        _('количество записей'),
        default=0,
        help_text=_('Общее количество записей')
    )
    
    # История покупок
    purchased_gb = models.IntegerField(
        _('докуплено GB'),
        default=0,
        help_text=_('Суммарно докуплено гигабайт сверх базовой квоты')
    )
    
    # Уведомления
    warning_sent = models.BooleanField(
        _('предупреждение отправлено'),
        default=False,
        help_text=_('Флаг отправки предупреждения о превышении 80%')
    )
    last_warning_at = models.DateTimeField(
        _('дата последнего предупреждения'),
        null=True,
        blank=True
    )
    
    quota_exceeded = models.BooleanField(
        _('квота превышена'),
        default=False,
        help_text=_('Флаг превышения квоты')
    )
    
    created_at = models.DateTimeField(_('дата создания'), auto_now_add=True)
    updated_at = models.DateTimeField(_('дата обновления'), auto_now=True)
    
    class Meta:
        verbose_name = _('квота хранилища')
        verbose_name_plural = _('квоты хранилища')
        ordering = ['-used_bytes']
        indexes = [
            models.Index(fields=['teacher']),
            models.Index(fields=['quota_exceeded']),
            models.Index(fields=['-used_bytes']),
        ]
    
    def __str__(self):
        return f"{self.teacher.get_full_name()} - {self.used_gb:.2f}/{self.total_gb:.2f} GB"
    
    @property
    def total_gb(self):
        """Общая квота в GB"""
        return self.total_quota_bytes / (1024 ** 3)
    
    @property
    def used_gb(self):
        """Использовано в GB"""
        return self.used_bytes / (1024 ** 3)
    
    @property
    def available_bytes(self):
        """Доступно байт"""
        return max(0, self.total_quota_bytes - self.used_bytes)
    
    @property
    def available_gb(self):
        """Доступно в GB"""
        return self.available_bytes / (1024 ** 3)
    
    @property
    def usage_percent(self):
        """Процент использования"""
        if self.total_quota_bytes == 0:
            return 0
        return (self.used_bytes / self.total_quota_bytes) * 100
    
    def can_upload(self, file_size_bytes):
        """Проверить возможность загрузки файла"""
        return (self.used_bytes + file_size_bytes) <= self.total_quota_bytes
    
    def add_recording(self, file_size_bytes):
        """Добавить запись и обновить использование"""
        self.used_bytes += file_size_bytes
        self.recordings_count += 1
        
        # Проверить превышение
        if self.used_bytes >= self.total_quota_bytes:
            self.quota_exceeded = True
        
        # Проверить предупреждение (80%)
        if self.usage_percent >= 80 and not self.warning_sent:
            self.warning_sent = True
            self.last_warning_at = timezone.now()
        
        self.save()
    
    def remove_recording(self, file_size_bytes):
        """Удалить запись и освободить место"""
        self.used_bytes = max(0, self.used_bytes - file_size_bytes)
        self.recordings_count = max(0, self.recordings_count - 1)
        
        # Сбросить флаги если место освободилось
        if self.used_bytes < self.total_quota_bytes:
            self.quota_exceeded = False
        
        if self.usage_percent < 80:
            self.warning_sent = False
        
        self.save()
    
    def increase_quota(self, additional_gb):
        """Увеличить квоту"""
        additional_bytes = int(additional_gb * (1024 ** 3))
        self.total_quota_bytes += additional_bytes
        self.purchased_gb += additional_gb
        
        # Сбросить флаги
        if self.used_bytes < self.total_quota_bytes:
            self.quota_exceeded = False
        
        if self.usage_percent < 80:
            self.warning_sent = False
        
        self.save()


class LessonMaterial(models.Model):
    """Учебные материалы к уроку (теория, конспект, Miro, документы)"""
    
    class MaterialType(models.TextChoices):
        THEORY = 'theory', _('Теория (перед уроком)')
        NOTES = 'notes', _('Конспект (после урока)')
        MIRO_BOARD = 'miro', _('Доска Miro')
        DOCUMENT = 'document', _('Документ')
        LINK = 'link', _('Ссылка')
        IMAGE = 'image', _('Изображение')

    class Visibility(models.TextChoices):
        LESSON_GROUP = 'lesson_group', _('Только группа урока')
        ALL_TEACHER_GROUPS = 'all_teacher_groups', _('Все группы преподавателя')
        CUSTOM_GROUPS = 'custom_groups', _('Выбранные группы')
        CUSTOM_STUDENTS = 'custom_students', _('Выбранные ученики')
    
    lesson = models.ForeignKey(
        'Lesson',
        on_delete=models.CASCADE,
        related_name='materials',
        verbose_name=_('урок'),
        null=True,
        blank=True,
        help_text=_('Урок, к которому привязан материал (опционально)')
    )
    
    material_type = models.CharField(
        _('тип материала'),
        max_length=20,
        choices=MaterialType.choices,
        default=MaterialType.NOTES,
        help_text=_('Тип материала: теория, конспект, Miro доска, документ и т.д.')
    )
    
    title = models.CharField(
        _('название'),
        max_length=255,
        help_text=_('Название материала')
    )
    
    description = models.TextField(
        _('описание'),
        blank=True,
        help_text=_('Краткое описание содержания')
    )
    
    # Файлы и ссылки
    file_url = models.URLField(
        _('ссылка на файл'),
        max_length=500,
        blank=True,
        help_text=_('URL файла в Google Drive или другом хранилище')
    )
    
    file_name = models.CharField(
        _('имя файла'),
        max_length=200,
        blank=True
    )
    
    file_size_bytes = models.BigIntegerField(
        _('размер файла (байты)'),
        default=0
    )
    
    gdrive_file_id = models.CharField(
        _('Google Drive File ID'),
        max_length=100,
        blank=True,
        help_text=_('ID файла в Google Drive')
    )
    
    # Поля для Miro досок
    miro_board_id = models.CharField(
        _('ID доски Miro'),
        max_length=100,
        blank=True,
        help_text=_('Уникальный идентификатор доски в Miro')
    )
    miro_board_url = models.URLField(
        _('ссылка на доску Miro'),
        max_length=500,
        blank=True,
        help_text=_('Прямая ссылка на доску Miro')
    )
    miro_embed_url = models.URLField(
        _('embed ссылка Miro'),
        max_length=500,
        blank=True,
        help_text=_('Ссылка для встраивания доски (iframe)')
    )
    miro_thumbnail_url = models.URLField(
        _('превью доски Miro'),
        max_length=500,
        blank=True,
        help_text=_('Ссылка на миниатюру доски')
    )
    
    # Для текстового контента (конспекты)
    content = models.TextField(
        _('содержимое'),
        blank=True,
        help_text=_('Текстовый контент конспекта (Markdown или HTML)')
    )
    
    # Владелец и видимость
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_materials',
        verbose_name=_('загрузил')
    )
    
    visibility = models.CharField(
        _('видимость'),
        max_length=32,
        choices=Visibility.choices,
        default=Visibility.LESSON_GROUP,
        help_text=_('Кому доступен материал')
    )
    
    allowed_groups = models.ManyToManyField(
        Group,
        related_name='material_access',
        blank=True,
        verbose_name=_('доступные группы')
    )
    
    allowed_students = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='material_access',
        blank=True,
        limit_choices_to={'role': 'student'},
        verbose_name=_('доступные студенты')
    )
    
    uploaded_at = models.DateTimeField(_('дата загрузки'), auto_now_add=True)
    updated_at = models.DateTimeField(_('дата обновления'), auto_now=True)
    
    # Статистика и порядок
    views_count = models.IntegerField(
        _('количество просмотров'),
        default=0
    )
    
    order = models.PositiveIntegerField(_('порядок'), default=0)
    
    class Meta:
        verbose_name = _('учебный материал')
        verbose_name_plural = _('учебные материалы')
        ordering = ['order', 'material_type', '-uploaded_at']
        indexes = [
            models.Index(fields=['lesson', 'material_type']),
            models.Index(fields=['uploaded_by', 'uploaded_at']),
            models.Index(fields=['material_type', 'uploaded_at']),
        ]
    
    def __str__(self):
        type_label = self.get_material_type_display()
        lesson_title = self.lesson.title if self.lesson else 'Без урока'
        return f"{lesson_title} - {type_label}: {self.title}"
    
    @property
    def file_size_mb(self):
        """Размер файла в MB"""
        if self.file_size_bytes:
            return round(self.file_size_bytes / (1024 ** 2), 2)
        return None
    
    @property 
    def is_miro(self):
        """Является ли материал доской Miro"""
        return self.material_type == self.MaterialType.MIRO_BOARD


class MaterialView(models.Model):
    """Отслеживание просмотров материалов учениками"""
    
    material = models.ForeignKey(
        'LessonMaterial',
        on_delete=models.CASCADE,
        related_name='views',
        verbose_name=_('материал')
    )
    
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='material_views',
        limit_choices_to={'role': 'student'},
        verbose_name=_('ученик')
    )
    
    viewed_at = models.DateTimeField(
        _('дата просмотра'),
        auto_now_add=True
    )
    
    # Опциональные метрики
    duration_seconds = models.IntegerField(
        _('длительность просмотра (секунды)'),
        default=0,
        help_text=_('Сколько времени ученик провел с материалом')
    )
    
    completed = models.BooleanField(
        _('завершен'),
        default=False,
        help_text=_('Ученик полностью изучил материал')
    )
    
    class Meta:
        verbose_name = _('просмотр материала')
        verbose_name_plural = _('просмотры материалов')
        ordering = ['-viewed_at']
        unique_together = [['material', 'student']]  # Один просмотр на ученика
        indexes = [
            models.Index(fields=['material', 'student']),
            models.Index(fields=['student', 'viewed_at'])
        ]
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.material.title} ({self.viewed_at.strftime('%d.%m.%Y %H:%M')})"
    


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


class IndividualInviteCode(models.Model):
    """Инвайт-код для приглашения одного индивидуального ученика на предмет"""
    
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='individual_invite_codes',
        limit_choices_to={'role': 'teacher'},
        verbose_name=_('преподаватель')
    )
    subject = models.CharField(
        _('предмет'),
        max_length=200,
        help_text=_('Название предмета/дисциплины')
    )
    invite_code = models.CharField(
        _('код приглашения'),
        max_length=8,
        unique=True,
        db_index=True,
        help_text=_('Уникальный 8-символьный код для приглашения одного ученика')
    )
    is_used = models.BooleanField(
        _('использован'),
        default=False,
        db_index=True,
        help_text=_('Был ли код использован для приглашения ученика')
    )
    used_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='joined_individual_subjects',
        limit_choices_to={'role': 'student'},
        verbose_name=_('использован учеником')
    )
    used_at = models.DateTimeField(
        _('дата использования'),
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(_('дата создания'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('индивидуальный инвайт-код')
        verbose_name_plural = _('индивидуальные инвайт-коды')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['teacher', 'is_used']),
            models.Index(fields=['used_by']),
            models.Index(fields=['invite_code']),
        ]
    
    def __str__(self):
        status = '✓ Использован' if self.is_used else '○ Активен'
        return f"{self.subject} ({self.teacher.get_full_name()}) - {status}"
    
    def generate_invite_code(self):
        """Генерирует уникальный 8-символьный код приглашения"""
        import secrets
        import string

        old_code = (self.invite_code or '').strip().upper() if self.invite_code else ''
        alphabet = string.ascii_uppercase + string.digits

        # Дизайн-уникальность: индивидуальные коды начинаются с I
        prefix = 'I'
        max_attempts = 64

        for _ in range(max_attempts):
            candidate = prefix + ''.join(secrets.choice(alphabet) for _ in range(7))
            if candidate == old_code:
                continue

            # Защита от конфликтов с Group (особенно legacy-значения)
            if Group.objects.filter(invite_code=candidate).exists():
                continue

            self.invite_code = candidate
            try:
                with transaction.atomic():
                    self.save(update_fields=['invite_code'])
                return candidate
            except IntegrityError:
                continue

        raise IntegrityError('Не удалось сгенерировать уникальный invite_code для индивидуального приглашения')
    
    def save(self, *args, **kwargs):
        # Генерируем код если его нет
        if self.invite_code:
            return super().save(*args, **kwargs)

        import secrets
        import string

        alphabet = string.ascii_uppercase + string.digits
        prefix = 'I'
        max_attempts = 64

        update_fields = kwargs.get('update_fields')
        if update_fields is not None:
            update_fields = set(update_fields)
            update_fields.add('invite_code')
            kwargs['update_fields'] = list(update_fields)

        for _ in range(max_attempts):
            candidate = prefix + ''.join(secrets.choice(alphabet) for _ in range(7))

            # Защита от конфликтов с Group (особенно legacy-значения)
            if Group.objects.filter(invite_code=candidate).exists():
                continue

            self.invite_code = candidate
            try:
                with transaction.atomic():
                    return super().save(*args, **kwargs)
            except IntegrityError:
                self.invite_code = ''
                continue

        raise IntegrityError('Не удалось сгенерировать уникальный invite_code для индивидуального приглашения')


class LessonNotificationLog(models.Model):
    """Лог отправленных Telegram-уведомлений (для избежания дублей)"""
    
    NOTIFICATION_TYPE_CHOICES = (
        ('reminder', 'Напоминание'),
        ('announce', 'Анонс'),
    )
    
    recurring_lesson = models.ForeignKey(
        RecurringLesson,
        on_delete=models.CASCADE,
        related_name='notification_logs',
        verbose_name=_('регулярный урок')
    )
    notification_type = models.CharField(
        _('тип уведомления'),
        max_length=20,
        choices=NOTIFICATION_TYPE_CHOICES
    )
    lesson_date = models.DateField(_('дата урока'))
    sent_at = models.DateTimeField(_('отправлено'), auto_now_add=True)
    recipients_count = models.PositiveIntegerField(
        _('количество получателей'),
        default=0
    )
    error_message = models.TextField(
        _('ошибка'),
        blank=True,
        default='',
        help_text=_('Сообщение об ошибке, если уведомление не удалось отправить')
    )
    
    class Meta:
        verbose_name = _('лог уведомления')
        verbose_name_plural = _('логи уведомлений')
        unique_together = ['recurring_lesson', 'notification_type', 'lesson_date']
        indexes = [
            models.Index(fields=['lesson_date', 'notification_type']),
        ]
    
    def __str__(self):
        return f"{self.recurring_lesson.title} - {self.lesson_date} ({self.notification_type})"


class RecurringLessonTelegramBindCode(models.Model):
    """Одноразовый код для привязки Telegram-группы к регулярному уроку.

    Используется ботом в группе: /bindgroup <CODE>
    """

    recurring_lesson = models.ForeignKey(
        RecurringLesson,
        on_delete=models.CASCADE,
        related_name='telegram_bind_codes',
        verbose_name=_('регулярный урок')
    )
    code = models.CharField(
        _('код'),
        max_length=12,
        unique=True,
        db_index=True
    )
    expires_at = models.DateTimeField(_('истекает'))
    used_at = models.DateTimeField(_('использован'), null=True, blank=True)
    used_chat_id = models.CharField(
        _('chat_id'),
        max_length=50,
        blank=True,
        default=''
    )
    created_at = models.DateTimeField(_('создан'), auto_now_add=True)

    class Meta:
        verbose_name = _('код привязки Telegram')
        verbose_name_plural = _('коды привязки Telegram')
        indexes = [
            models.Index(fields=['expires_at']),
            models.Index(fields=['used_at']),
        ]

    def __str__(self):
        return f"{self.code} → {self.recurring_lesson_id}"


class MiroUserToken(models.Model):
    """OAuth токены Miro для учителей.
    
    Позволяет учителю авторизоваться в Miro через OAuth
    и получать доступ к своим доскам.
    """
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='miro_token',
        verbose_name=_('пользователь')
    )
    
    access_token = models.CharField(
        _('access token'),
        max_length=500,
        help_text=_('Токен доступа Miro API')
    )
    
    refresh_token = models.CharField(
        _('refresh token'),
        max_length=500,
        blank=True,
        help_text=_('Токен для обновления access token')
    )
    
    token_type = models.CharField(
        _('тип токена'),
        max_length=50,
        default='Bearer'
    )
    
    expires_at = models.DateTimeField(
        _('истекает'),
        null=True,
        blank=True,
        help_text=_('Когда истекает access token')
    )
    
    miro_user_id = models.CharField(
        _('Miro User ID'),
        max_length=100,
        blank=True,
        help_text=_('ID пользователя в Miro')
    )
    
    miro_team_id = models.CharField(
        _('Miro Team ID'),
        max_length=100,
        blank=True,
        help_text=_('ID команды в Miro')
    )
    
    scopes = models.TextField(
        _('scopes'),
        blank=True,
        help_text=_('Разрешения токена через пробел')
    )
    
    created_at = models.DateTimeField(_('создан'), auto_now_add=True)
    updated_at = models.DateTimeField(_('обновлён'), auto_now=True)
    
    class Meta:
        verbose_name = _('Miro токен пользователя')
        verbose_name_plural = _('Miro токены пользователей')
    
    def __str__(self):
        return f"Miro token for {self.user.email}"
    
    @property
    def is_expired(self):
        """Проверить, истёк ли токен"""
        if not self.expires_at:
            return False
        return timezone.now() >= self.expires_at
    
    def needs_refresh(self):
        """Проверить, нужно ли обновить токен (за 5 минут до истечения)"""
        if not self.expires_at:
            return False
        buffer = timezone.timedelta(minutes=5)
        return timezone.now() >= (self.expires_at - buffer)


class LessonTranscriptStats(models.Model):
    """Статистика по транскрипту урока (участие, упоминания)"""
    lesson = models.OneToOneField(
        Lesson,
        on_delete=models.CASCADE,
        related_name='transcript_stats',
        verbose_name=_('урок')
    )
    
    # Сырые данные анализа
    stats_json = models.JSONField(
        _('данные анализа'),
        default=dict, 
        help_text=_("JSON со статистикой: speakers, mentions, timeline")
    )
    
    # Агрегированные метрики для быстрых отчетов
    teacher_talk_time_percent = models.FloatField(_('% времени учителя'), default=0)
    student_talk_time_percent = models.FloatField(_('% времени учеников'), default=0)
    
    created_at = models.DateTimeField(_('дата анализа'), auto_now_add=True)
    updated_at = models.DateTimeField(_('дата обновления'), auto_now=True)
    
    class Meta:
        verbose_name = _('статистика транскрипта')
        verbose_name_plural = _('статистика транскриптов')

    def __str__(self):
        return f"Stats for {self.lesson}"

