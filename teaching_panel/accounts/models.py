from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.utils.crypto import get_random_string
import random
import string
import uuid
from decimal import Decimal


class CustomUserManager(BaseUserManager):
    """Кастомный менеджер для CustomUser, где email - это уникальный идентификатор"""
    
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('Email обязателен'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        # Админ по умолчанию должен быть 'admin', а не 'teacher'
        extra_fields.setdefault('role', 'admin')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser должен иметь is_staff=True'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser должен иметь is_superuser=True'))
        
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    """
    Кастомная модель пользователя для учебной платформы.
    Вход по email (username отключен).
    """
    
    ROLE_CHOICES = (
        ('student', 'Ученик'),
        ('teacher', 'Учитель'),
        ('admin', 'Администратор'),
    )
    
    # Отключаем username, используем email для входа
    username = None
    email = models.EmailField(_('email адрес'), unique=True)
    email_verified = models.BooleanField(_('email верифицирован'), default=False)
    
    # Дополнительные поля
    phone_number = models.CharField(
        _('номер телефона'), 
        max_length=20, 
        unique=True, 
        blank=True, 
        null=True,
        help_text=_('Для входа через телефон (опционально)')
    )
    
    role = models.CharField(
        _('роль'), 
        max_length=20, 
        choices=ROLE_CHOICES,
        help_text=_('Ученик, Учитель или Администратор')
    )

    middle_name = models.CharField(
        _('отчество'),
        max_length=150,
        blank=True,
        default='',
        help_text=_('Опционально, отображается в профиле')
    )
    
    agreed_to_marketing = models.BooleanField(
        _('согласие на маркетинг'), 
        default=False,
        help_text=_('Согласен на получение маркетинговых рассылок')
    )
    
    avatar = models.TextField(
        _('аватар'),
        blank=True,
        default='',
        help_text=_('Base64 или URL изображения для аватара пользователя')
    )
    
    date_of_birth = models.DateField(
        _('дата рождения'), 
        blank=True, 
        null=True
    )
    
    # Telegram для восстановления пароля и уведомлений
    telegram_id = models.CharField(
        _('Telegram ID'),
        max_length=50,
        blank=True,
        null=True,
        unique=True,
        help_text=_('ID пользователя в Telegram для восстановления пароля и уведомлений')
    )
    
    telegram_username = models.CharField(
        _('Telegram Username'),
        max_length=50,
        blank=True,
        default='',
        help_text=_('Username в Telegram (опционально)')
    )
    
    telegram_chat_id = models.CharField(
        _('Telegram Chat ID'),
        max_length=50,
        blank=True,
        null=True,
        help_text=_('Chat ID для отправки сообщений через бота')
    )

    telegram_verified = models.BooleanField(
        _('Telegram подтверждён'),
        default=False,
        help_text=_('Флаг показывает, что пользователь подтвердил привязку Telegram через бота')
    )

    # Реферальная система
    referral_code = models.CharField(
        _('реферальный код'),
        max_length=12,
        unique=True,
        blank=True,
        default='',
        help_text=_('Уникальный код для реферальной ссылки (например: ?ref=CODE)')
    )
    referred_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='referred_users',
        help_text=_('Пригласивший пользователь (если пришёл по реферальной ссылке)')
    )
    
    # Zoom credentials для учителей
    zoom_account_id = models.CharField(
        _('Zoom Account ID'),
        max_length=255,
        blank=True,
        default='',
        help_text=_('Account ID для Zoom API (только для учителей)')
    )
    
    zoom_client_id = models.CharField(
        _('Zoom Client ID'),
        max_length=255,
        blank=True,
        default='',
        help_text=_('Client ID для Zoom API (только для учителей)')
    )
    
    zoom_client_secret = models.CharField(
        _('Zoom Client Secret'),
        max_length=255,
        blank=True,
        default='',
        help_text=_('Client Secret для Zoom API (только для учителей)')
    )
    
    zoom_user_id = models.CharField(
        _('Zoom User ID'),
        max_length=255,
        blank=True,
        default='',
        help_text=_('User ID в Zoom (обычно email или ID пользователя)')
    )
    
    zoom_pmi_link = models.URLField(
        _('Zoom PMI ссылка'),
        max_length=500,
        blank=True,
        default='',
        help_text=_('Постоянная ссылка Zoom (Personal Meeting ID) для регулярных уроков')
    )
    
    # ==========================================================================
    # Google Meet Integration (OAuth2 tokens stored per-user)
    # Each teacher creates their own Google Cloud project and enters credentials
    # ==========================================================================
    google_meet_connected = models.BooleanField(
        _('Google Meet подключён'),
        default=False,
        help_text=_('Флаг показывает, что учитель успешно авторизовал Google Meet')
    )
    
    # Personal Google OAuth credentials (each teacher has their own)
    google_meet_client_id = models.CharField(
        _('Google Meet Client ID'),
        max_length=255,
        blank=True,
        default='',
        help_text=_('OAuth2 Client ID из Google Cloud Console учителя')
    )
    
    google_meet_client_secret = models.CharField(
        _('Google Meet Client Secret'),
        max_length=255,
        blank=True,
        default='',
        help_text=_('OAuth2 Client Secret из Google Cloud Console учителя')
    )
    
    google_meet_access_token = models.TextField(
        _('Google Meet Access Token'),
        blank=True,
        default='',
        help_text=_('OAuth2 access token для Google Calendar API (зашифрован)')
    )
    
    google_meet_refresh_token = models.TextField(
        _('Google Meet Refresh Token'),
        blank=True,
        default='',
        help_text=_('OAuth2 refresh token для обновления access token')
    )
    
    google_meet_token_expires_at = models.DateTimeField(
        _('Google Meet Token Expires'),
        blank=True,
        null=True,
        help_text=_('Время истечения access token')
    )
    
    google_meet_email = models.EmailField(
        _('Google Meet Email'),
        blank=True,
        default='',
        help_text=_('Email аккаунта Google, к которому привязан Meet')
    )
    
    # Google Drive для хранения файлов
    gdrive_folder_id = models.CharField(
        _('Google Drive Folder ID'),
        max_length=255,
        blank=True,
        default='',
        help_text=_('ID главной папки учителя в Google Drive (только для учителей)')
    )
    
    # Username для чатов (как в Telegram)
    username_handle = models.CharField(
        _('короткое имя'),
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        help_text=_('Короткое имя для упоминаний в чатах (например: @ivanov)')
    )
    
    created_at = models.DateTimeField(_('дата регистрации'), auto_now_add=True)
    updated_at = models.DateTimeField(_('дата обновления'), auto_now=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['role']  # Поля, запрашиваемые при createsuperuser (кроме email и password)
    
    objects = CustomUserManager()
    
    class Meta:
        verbose_name = _('пользователь')
        verbose_name_plural = _('пользователи')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"
    
    def is_teacher(self):
        """Проверка, является ли пользователь преподавателем"""
        return self.role == 'teacher'
    
    def is_student(self):
        """Проверка, является ли пользователь учеником"""
        return self.role == 'student'
    
    def get_full_name(self):
        """Возвращает полное имя пользователя"""
        parts = [self.last_name or '', self.first_name or '', self.middle_name or '']
        full = ' '.join(filter(None, parts)).strip()
        return full or self.email

    # =========================================================================
    # Platform connection status helpers
    # =========================================================================
    def is_zoom_connected(self):
        """
        Проверяет, подключён ли Zoom для этого учителя.
        Zoom считается подключённым если есть все три OAuth credentials.
        """
        return bool(
            self.zoom_account_id and
            self.zoom_client_id and
            self.zoom_client_secret
        )

    def is_google_meet_connected(self):
        """
        Проверяет, подключён ли Google Meet для этого учителя.
        Meet считается подключённым если есть refresh token и флаг connected.
        """
        return bool(self.google_meet_connected and self.google_meet_refresh_token)

    def get_available_platforms(self):
        """
        Возвращает список доступных платформ для проведения уроков.
        Используется в UI для показа выбора платформы.
        """
        platforms = []
        # Zoom через пул платформы всегда доступен (если пул настроен глобально)
        platforms.append({
            'id': 'zoom_pool',
            'name': 'Zoom (пул платформы)',
            'connected': True,  # Пул всегда доступен
            'icon': 'video'
        })
        # Персональный Zoom учителя
        if self.is_zoom_connected():
            platforms.append({
                'id': 'zoom_personal',
                'name': 'Zoom (личный)',
                'connected': True,
                'email': self.zoom_user_id or 'настроен',
                'icon': 'video'
            })
        # Google Meet
        if self.is_google_meet_connected():
            platforms.append({
                'id': 'google_meet',
                'name': 'Google Meet',
                'connected': True,
                'email': self.google_meet_email or 'подключён',
                'icon': 'users'
            })
        return platforms

    def save(self, *args, **kwargs):
        # Генерируем реферальный код, если пуст
        if not self.referral_code:
            # Код из 8 символов: [A-Z0-9]
            base = get_random_string(8, allowed_chars=string.ascii_uppercase + string.digits)
            # Убеждаемся в уникальности
            candidate = base
            counter = 0
            while CustomUser.objects.filter(referral_code=candidate).exclude(pk=self.pk).exists():
                counter += 1
                candidate = f"{base}{counter}"
                if len(candidate) > 12:
                    candidate = get_random_string(10, allowed_chars=string.ascii_uppercase + string.digits)
            self.referral_code = candidate
        super().save(*args, **kwargs)


class StatusBarMessage(models.Model):
    """Сообщения для статус-бара"""
    
    TARGET_CHOICES = (
        ('teachers', 'Учителя'),
        ('students', 'Ученики'),
        ('all', 'Все'),
    )
    
    message = models.TextField('Сообщение')
    target = models.CharField('Для кого', max_length=20, choices=TARGET_CHOICES)
    is_active = models.BooleanField('Активно', default=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='status_messages')
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)
    
    class Meta:
        verbose_name = 'Сообщение статус-бара'
        verbose_name_plural = 'Сообщения статус-бара'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_target_display()}: {self.message[:50]}"


class Chat(models.Model):
    """Чат - может быть личным или групповым"""
    
    CHAT_TYPE_CHOICES = (
        ('private', 'Личный'),
        ('group', 'Групповой'),
    )
    
    name = models.CharField('Название', max_length=255, blank=True, default='')
    chat_type = models.CharField('Тип чата', max_length=20, choices=CHAT_TYPE_CHOICES, default='private')
    participants = models.ManyToManyField(CustomUser, related_name='chats', verbose_name='Участники')
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='created_chats', verbose_name='Создатель')
    group = models.ForeignKey('schedule.Group', on_delete=models.CASCADE, null=True, blank=True, related_name='chats', verbose_name='Группа')
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлён', auto_now=True)
    
    class Meta:
        verbose_name = 'Чат'
        verbose_name_plural = 'Чаты'
        ordering = ['-updated_at']
    
    def __str__(self):
        if self.chat_type == 'group':
            return self.name or f"Групповой чат #{self.id}"
        participants_str = ', '.join([p.get_full_name() for p in self.participants.all()[:2]])
        return f"Чат: {participants_str}"
    
    def get_last_message(self):
        """Возвращает последнее сообщение в чате"""
        return self.messages.order_by('-created_at').first()


class Message(models.Model):
    """Сообщение в чате"""
    
    MESSAGE_TYPE_CHOICES = (
        ('text', 'Текст'),
        ('question', 'Вопрос'),
        ('answer', 'Ответ на вопрос'),
        ('file', 'Файл'),
        ('system', 'Системное'),
    )
    
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='messages', verbose_name='Чат')
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_messages', verbose_name='Отправитель')
    text = models.TextField('Текст сообщения')
    is_read = models.BooleanField('Прочитано', default=False)
    created_at = models.DateTimeField('Отправлено', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)
    
    # === НОВЫЕ ПОЛЯ ДЛЯ АНАЛИТИКИ ===
    message_type = models.CharField(
        'Тип сообщения',
        max_length=20,
        choices=MESSAGE_TYPE_CHOICES,
        default='text'
    )
    reply_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replies',
        verbose_name='Ответ на'
    )
    mentioned_users = models.ManyToManyField(
        CustomUser,
        blank=True,
        related_name='mentioned_in_messages',
        verbose_name='Упомянутые пользователи'
    )
    # AI-анализ сентимента
    sentiment_score = models.FloatField(
        null=True,
        blank=True,
        help_text='Оценка тональности -1 (негатив) до +1 (позитив)'
    )
    is_helpful = models.BooleanField(
        null=True,
        blank=True,
        help_text='Является ли сообщение помощью другому ученику'
    )
    
    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['chat', 'sender', 'created_at'], name='msg_analytics_idx'),
        ]
    
    def __str__(self):
        return f"{self.sender.get_full_name()}: {self.text[:50]}"
    
    def extract_mentions(self):
        """Извлекает @упоминания из текста и связывает с пользователями"""
        import re
        mentions = re.findall(r'@(\w+)', self.text)
        if mentions:
            users = CustomUser.objects.filter(username_handle__in=mentions)
            self.mentioned_users.set(users)
        return mentions


class MessageReadStatus(models.Model):
    """Статус прочтения сообщения для каждого участника"""
    
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='read_statuses', verbose_name='Сообщение')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='message_read_statuses', verbose_name='Пользователь')
    is_read = models.BooleanField('Прочитано', default=False)
    read_at = models.DateTimeField('Прочитано', null=True, blank=True)
    
    class Meta:
        verbose_name = 'Статус прочтения'
        verbose_name_plural = 'Статусы прочтения'
        unique_together = ['message', 'user']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.message.text[:30]} ({'✓' if self.is_read else '✗'})"


class AttendanceAlertRead(models.Model):
    """Отметка о прочтении оповещений о посещаемости"""

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='attendance_alert_reads',
        verbose_name='Пользователь'
    )
    student = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='attendance_alert_as_student_reads',
        verbose_name='Ученик'
    )
    group = models.ForeignKey(
        'schedule.Group',
        on_delete=models.CASCADE,
        related_name='attendance_alert_reads',
        verbose_name='Группа'
    )
    last_seen_absences = models.PositiveIntegerField(
        'Максимум пропусков на момент прочтения',
        default=0
    )
    read_at = models.DateTimeField('Прочитано', null=True, blank=True)

    class Meta:
        verbose_name = 'Прочитанное оповещение о посещаемости'
        verbose_name_plural = 'Прочитанные оповещения о посещаемости'
        unique_together = ['user', 'student', 'group']
        indexes = [
            models.Index(fields=['user', 'group'], name='att_alert_read_user_group'),
            models.Index(fields=['user', 'student'], name='att_alert_read_user_student'),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.student.get_full_name()} ({self.group.name})"


class EmailVerification(models.Model):
    """Модель для верификации email адреса"""
    
    email = models.EmailField('Email адрес')
    token = models.UUIDField('Токен верификации', default=uuid.uuid4, unique=True)
    code = models.CharField('Код верификации', max_length=6)
    is_verified = models.BooleanField('Верифицирован', default=False)
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    expires_at = models.DateTimeField('Истекает')
    attempts = models.IntegerField('Попыток проверки', default=0)
    
    class Meta:
        verbose_name = 'Верификация email'
        verbose_name_plural = 'Верификации email'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.email} - {'✓' if self.is_verified else f'Код: {self.code}'}"
    
    def is_expired(self):
        """Проверка истечения токена/кода"""
        return timezone.now() > self.expires_at
    
    def can_retry(self):
        """Можно ли еще попробовать ввести код (максимум 3 попытки)"""
        return self.attempts < 3
    
    @staticmethod
    def generate_code():
        """Генерация 6-значного кода"""
        return ''.join(random.choices(string.digits, k=6))
    
    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.generate_code()
        if not self.expires_at:
            # Токен действителен 24 часа, код - 10 минут
            self.expires_at = timezone.now() + timezone.timedelta(hours=24)
        super().save(*args, **kwargs)


class PhoneVerification(models.Model):
    """Модель для верификации номера телефона через SMS"""
    
    phone_number = models.CharField('Номер телефона', max_length=20)
    code = models.CharField('Код верификации', max_length=6)
    is_verified = models.BooleanField('Верифицирован', default=False)
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    expires_at = models.DateTimeField('Истекает')
    attempts = models.IntegerField('Попыток проверки', default=0)
    
    class Meta:
        verbose_name = 'Верификация телефона'
        verbose_name_plural = 'Верификации телефонов'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.phone_number} - {'✓' if self.is_verified else f'Код: {self.code}'}"
    
    def is_expired(self):
        """Проверка истечения кода"""
        return timezone.now() > self.expires_at
    
    def can_retry(self):
        """Можно ли еще попробовать ввести код (максимум 3 попытки)"""
        return self.attempts < 3
    
    @staticmethod
    def generate_code():
        """Генерация 6-значного кода"""
        return ''.join(random.choices(string.digits, k=6))
    
    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.generate_code()
        if not self.expires_at:
            # Код действителен 10 минут
            self.expires_at = timezone.now() + timezone.timedelta(minutes=10)
        super().save(*args, **kwargs)


class SystemSettings(models.Model):
    """Глобальные настройки системы (singleton)"""
    
    # Email настройки
    email_from = models.EmailField(
        'Email отправителя',
        default='noreply@teachingpanel.com',
        help_text='Email, от имени которого отправляются письма'
    )
    email_notifications_enabled = models.BooleanField(
        'Email уведомления включены',
        default=True
    )
    welcome_email_enabled = models.BooleanField(
        'Приветственное письмо',
        default=True,
        help_text='Отправлять письмо при регистрации'
    )
    
    # Уведомления
    lesson_reminder_hours = models.IntegerField(
        'Напоминание о занятии (часов)',
        default=2,
        help_text='За сколько часов напоминать о занятии'
    )
    homework_deadline_reminder_hours = models.IntegerField(
        'Напоминание о дедлайне ДЗ (часов)',
        default=24,
        help_text='За сколько часов напоминать о дедлайне'
    )
    push_notifications_enabled = models.BooleanField(
        'Push уведомления',
        default=False
    )
    
    # Zoom настройки по умолчанию
    default_lesson_duration = models.IntegerField(
        'Длительность занятия (минут)',
        default=60,
        help_text='Длительность занятия по умолчанию'
    )
    auto_recording = models.BooleanField(
        'Автозапись занятий',
        default=False,
        help_text='Автоматически записывать занятия'
    )
    waiting_room_enabled = models.BooleanField(
        'Комната ожидания',
        default=True,
        help_text='Включить комнату ожидания в Zoom'
    )
    
    # Расписание
    min_booking_hours = models.IntegerField(
        'Минимум часов до занятия',
        default=2,
        help_text='За сколько часов минимум можно забронировать занятие'
    )
    max_booking_days = models.IntegerField(
        'Максимум дней вперед',
        default=30,
        help_text='На сколько дней вперед можно бронировать'
    )
    cancellation_hours = models.IntegerField(
        'Отмена занятия (часов)',
        default=24,
        help_text='За сколько часов можно отменить занятие'
    )
    
    # Брендинг
    platform_name = models.CharField(
        'Название платформы',
        max_length=100,
        default='Teaching Panel',
        help_text='Название, отображаемое в интерфейсе'
    )
    support_email = models.EmailField(
        'Email поддержки',
        default='support@teachingpanel.com'
    )
    logo_url = models.URLField(
        'URL логотипа',
        blank=True,
        default='',
        help_text='Ссылка на логотип платформы'
    )
    primary_color = models.CharField(
        'Основной цвет',
        max_length=7,
        default='#4F46E5',
        help_text='HEX код основного цвета интерфейса'
    )
    
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)
    
    class Meta:
        verbose_name = 'Настройки системы'
        verbose_name_plural = 'Настройки системы'
    
    def __str__(self):
        return f"Настройки системы (обновлено: {self.updated_at.strftime('%d.%m.%Y %H:%M')})"
    
    def save(self, *args, **kwargs):
        # Singleton: удаляем все предыдущие записи
        if not self.pk:
            SystemSettings.objects.all().delete()
        super().save(*args, **kwargs)
    
    @classmethod
    def get_settings(cls):
        """Получить единственный экземпляр настроек (или создать с дефолтами)"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings


class PasswordResetToken(models.Model):
    """
    Токены для восстановления пароля через Telegram
    """
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='password_reset_tokens',
        verbose_name=_('пользователь')
    )
    token = models.CharField(
        _('токен'),
        max_length=64,
        unique=True,
        help_text=_('Уникальный токен для восстановления пароля')
    )
    created_at = models.DateTimeField(_('создан'), auto_now_add=True)
    expires_at = models.DateTimeField(_('истекает'))
    used = models.BooleanField(_('использован'), default=False)
    used_at = models.DateTimeField(_('использован в'), blank=True, null=True)
    
    class Meta:
        verbose_name = _('токен восстановления пароля')
        verbose_name_plural = _('токены восстановления пароля')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Token for {self.user.email} (expires: {self.expires_at})"
    
    def is_valid(self):
        """Проверка валидности токена"""
        return not self.used and timezone.now() < self.expires_at
    
    @classmethod
    def generate_token(cls, user, expires_in_minutes=30):
        """Генерация нового токена для пользователя"""
        # Удаляем старые неиспользованные токены этого пользователя
        cls.objects.filter(user=user, used=False).delete()
        
        # Генерируем уникальный токен
        token = get_random_string(64)
        expires_at = timezone.now() + timezone.timedelta(minutes=expires_in_minutes)
        
        return cls.objects.create(
            user=user,
            token=token,
            expires_at=expires_at
        )


class TelegramLinkCode(models.Model):
    """Одноразовые коды для безопасной привязки Telegram через бота."""

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='telegram_link_codes'
    )
    code = models.CharField(max_length=16, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('код привязки Telegram')
        verbose_name_plural = _('коды привязки Telegram')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} → {self.code} ({'used' if self.used else 'active'})"

    @classmethod
    def generate_for_user(cls, user, ttl_minutes: int = 10):
        """Генерирует новый код и удаляет старые для пользователя."""
        cls.objects.filter(user=user, used=False).delete()
        code = get_random_string(8).upper()
        expires_at = timezone.now() + timezone.timedelta(minutes=ttl_minutes)
        return cls.objects.create(user=user, code=code, expires_at=expires_at)

    def mark_used(self):
        self.used = True
        self.used_at = timezone.now()
        self.save(update_fields=['used', 'used_at'])


# =========================
# Subscriptions & Payments
# =========================

class Subscription(models.Model):
    PLAN_TRIAL = 'trial'
    PLAN_MONTHLY = 'monthly'
    PLAN_YEARLY = 'yearly'

    PLAN_CHOICES = (
        (PLAN_TRIAL, 'Пробный (7 дней)'),
        (PLAN_MONTHLY, 'Месячный'),
        (PLAN_YEARLY, 'Годовой'),
    )

    STATUS_ACTIVE = 'active'
    STATUS_CANCELLED = 'cancelled'
    STATUS_EXPIRED = 'expired'
    STATUS_PENDING = 'pending'

    STATUS_CHOICES = (
        (STATUS_ACTIVE, 'Активна'),
        (STATUS_CANCELLED, 'Отменена'),
        (STATUS_EXPIRED, 'Истекла'),
        (STATUS_PENDING, 'Ожидает оплаты'),
    )

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='subscription')
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default=PLAN_TRIAL)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)

    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    cancelled_at = models.DateTimeField(null=True, blank=True)

    payment_method = models.CharField(max_length=50, blank=True)
    auto_renew = models.BooleanField(default=True)
    next_billing_date = models.DateField(null=True, blank=True)

    total_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    last_payment_date = models.DateTimeField(null=True, blank=True)

    # Хранилище (GB). Базовый объем 10 ГБ, дополнительные покупки.
    base_storage_gb = models.IntegerField(default=10)
    extra_storage_gb = models.IntegerField(default=0)
    used_storage_gb = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    # Zoom Add-on (платная подписка на выделенный Zoom / личный Zoom)
    # Хранит только факт оплаты и срок действия. Настройка Zoom выполняется отдельным API.
    zoom_addon_expires_at = models.DateTimeField(null=True, blank=True)

    # Zoom Add-on: настройки регулярного платежа.
    # Важно: хранение метода/идентификатора — база для автосписаний,
    # но само автосписание требует отдельной логики (cron/celery).
    zoom_addon_auto_renew = models.BooleanField(default=False)
    zoom_addon_payment_method_id = models.CharField(max_length=255, blank=True, default='')
    zoom_addon_tbank_rebill_id = models.CharField(max_length=100, blank=True, default='')
    
    # ID папки на Google Drive (создаётся при активации подписки)
    gdrive_folder_id = models.CharField(max_length=255, blank=True, default='')
    
    # T-Bank RebillId для рекуррентных платежей (автопродление)
    tbank_rebill_id = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text='RebillId для автоматического продления подписки через T-Bank'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'

    def __str__(self):
        return f"Подписка {self.user.email}: {self.plan} ({self.status})"

    def is_active(self):
        return self.status == self.STATUS_ACTIVE and self.expires_at > timezone.now()

    def days_until_expiry(self):
        if self.expires_at:
            delta = self.expires_at - timezone.now()
            return max(0, delta.days)
        return 0

    @property
    def total_storage_gb(self):
        return self.base_storage_gb + self.extra_storage_gb

    def add_storage(self, gb: int):
        if gb <= 0:
            return
        self.extra_storage_gb += gb
        self.save(update_fields=['extra_storage_gb', 'updated_at'])

    def is_zoom_addon_active(self) -> bool:
        if not self.zoom_addon_expires_at:
            return False
        return self.zoom_addon_expires_at > timezone.now()


class Payment(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_SUCCEEDED = 'succeeded'
    STATUS_FAILED = 'failed'
    STATUS_REFUNDED = 'refunded'

    STATUS_CHOICES = (
        (STATUS_PENDING, 'Ожидает'),
        (STATUS_SUCCEEDED, 'Успешно'),
        (STATUS_FAILED, 'Ошибка'),
        (STATUS_REFUNDED, 'Возврат'),
    )

    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='RUB')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)

    payment_system = models.CharField(max_length=50, default='yookassa')
    payment_id = models.CharField(max_length=255, unique=True)
    payment_url = models.URLField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = 'Платеж'
        verbose_name_plural = 'Платежи'

    def __str__(self):
        return f"Payment {self.payment_id} ({self.status})"


class ReferralAttribution(models.Model):
    """
    Атрибуция реферала/источника трафика для нового пользователя.
    Хранит UTM-метки и исходный URL/канал для аналитики.
    """
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='referral_attribution')
    referrer = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='referral_attributions')
    referral_code = models.CharField(max_length=32, blank=True, default='')
    utm_source = models.CharField(max_length=64, blank=True, default='')
    utm_medium = models.CharField(max_length=64, blank=True, default='')
    utm_campaign = models.CharField(max_length=64, blank=True, default='')
    channel = models.CharField(max_length=64, blank=True, default='', help_text=_('Канал (например, Telegram/GroupName)'))
    ref_url = models.URLField(max_length=500, blank=True, default='')
    cookie_id = models.CharField(max_length=64, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('атрибуция реферала')
        verbose_name_plural = _('атрибуции рефералов')

    def __str__(self):
        return f"ref={self.referral_code} utm={self.utm_source}/{self.utm_medium}/{self.utm_campaign} for {self.user.email}"


class ReferralCommission(models.Model):
    """
    Комиссия рефереру за оплату приглашённого пользователя.
    Создаётся при успешном платеже (subscription/storage).
    """
    STATUS_PENDING = 'pending'
    STATUS_PAID = 'paid'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = (
        (STATUS_PENDING, 'Ожидает выплаты'),
        (STATUS_PAID, 'Выплачено'),
        (STATUS_CANCELLED, 'Отменено'),
    )

    referrer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='referral_commissions')
    referred_user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='earned_commissions')
    payment = models.OneToOneField('Payment', on_delete=models.CASCADE, related_name='referral_commission', null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('750.00'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = _('реферальная комиссия')
        verbose_name_plural = _('реферальные комиссии')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['referrer', 'status']),
            models.Index(fields=['referred_user']),
        ]

    def __str__(self):
        return f"{self.referrer.email} ← {self.referred_user.email}: {self.amount} ({self.status})"

    def mark_paid(self):
        self.status = self.STATUS_PAID
        self.paid_at = timezone.now()
        self.save(update_fields=['status', 'paid_at'])


class NotificationSettings(models.Model):
    """Персональные настройки уведомлений пользователя."""

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='notification_settings')
    telegram_enabled = models.BooleanField(default=True)

    # Учителям — базовые
    notify_homework_submitted = models.BooleanField(default=True)
    notify_subscription_expiring = models.BooleanField(default=True)
    notify_payment_success = models.BooleanField(default=True)

    # Учителям — аналитика: пропуски
    notify_absence_alert = models.BooleanField(
        default=True,
        help_text='Уведомления о сериях пропусков учеников'
    )
    absence_alert_threshold = models.PositiveSmallIntegerField(
        default=3,
        help_text='Минимальное количество пропусков подряд для уведомления (0 = отключено)'
    )

    # Учителям — аналитика: успеваемость
    notify_performance_drop = models.BooleanField(
        default=True,
        help_text='Уведомления о падении успеваемости ученика'
    )
    performance_drop_percent = models.PositiveSmallIntegerField(
        default=20,
        help_text='Процент падения среднего балла для уведомления'
    )

    # Учителям — аналитика: группа
    notify_group_health = models.BooleanField(
        default=True,
        help_text='Уведомления об аномалиях по группе (посещаемость/успеваемость)'
    )

    # Учителям — backlog проверки ДЗ
    notify_grading_backlog = models.BooleanField(
        default=True,
        help_text='Уведомления о накопившихся непроверенных ДЗ'
    )
    grading_backlog_threshold = models.PositiveSmallIntegerField(
        default=5,
        help_text='Минимальное количество непроверенных работ для уведомления'
    )
    grading_backlog_hours = models.PositiveSmallIntegerField(
        default=48,
        help_text='Сколько часов работа может висеть без проверки'
    )

    # Учителям — неактивные ученики
    notify_inactive_student = models.BooleanField(
        default=True,
        help_text='Уведомления о неактивных учениках'
    )
    inactive_student_days = models.PositiveSmallIntegerField(
        default=7,
        help_text='Количество дней без активности для уведомления'
    )

    # ===== НОВЫЕ: Учителям — события с учениками и уроками =====
    
    # Вступление/уход ученика
    notify_student_joined = models.BooleanField(
        default=True,
        help_text='Уведомление когда ученик вступает в группу или становится индивидуальным'
    )
    notify_student_left = models.BooleanField(
        default=True,
        help_text='Уведомление когда ученик покидает группу'
    )
    
    # Запись урока
    notify_recording_ready = models.BooleanField(
        default=True,
        help_text='Уведомление когда запись урока обработана и доступна'
    )
    
    # ===== Глобальные настройки уведомлений по умолчанию (для уроков) =====
    
    # Анонсы/напоминания перед уроком
    default_lesson_reminder_enabled = models.BooleanField(
        default=True,
        help_text='По умолчанию отправлять напоминания о начале урока'
    )
    default_lesson_reminder_minutes = models.PositiveSmallIntegerField(
        default=15,
        help_text='За сколько минут до урока отправлять напоминание (5, 10, 15, 30, 60)'
    )
    
    # Куда отправлять уведомления ученикам
    default_notify_to_group_chat = models.BooleanField(
        default=True,
        help_text='Отправлять уведомления в Telegram-группу (если привязана)'
    )
    default_notify_to_students_dm = models.BooleanField(
        default=True,
        help_text='Отправлять уведомления ученикам в личные сообщения'
    )
    
    # Отправка ссылки при старте урока
    notify_lesson_link_on_start = models.BooleanField(
        default=True,
        help_text='Отправлять ссылку на урок (Zoom/Meet) когда учитель начинает урок'
    )
    
    # Новые материалы
    notify_materials_added = models.BooleanField(
        default=True,
        help_text='Уведомлять учеников о добавлении новых материалов к уроку'
    )

    # Ученикам — базовые
    notify_homework_graded = models.BooleanField(default=True)
    notify_homework_deadline = models.BooleanField(default=True)
    notify_lesson_reminders = models.BooleanField(default=True)
    notify_new_homework = models.BooleanField(default=True)

    # Ученикам — аналитика: пропуски
    notify_student_absence_warning = models.BooleanField(
        default=True,
        help_text='Предупреждения ученику о его пропусках'
    )

    # Ученикам — контрольные точки/дедлайны
    notify_control_point_deadline = models.BooleanField(
        default=True,
        help_text='Напоминания о контрольных точках'
    )

    # Ученикам — достижения
    notify_achievement = models.BooleanField(
        default=False,
        help_text='Уведомления о достижениях и прогрессе'
    )

    # Ученикам — напоминание об активности
    notify_inactivity_nudge = models.BooleanField(
        default=True,
        help_text='Мягкие напоминания при длительном отсутствии активности'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('настройки уведомлений')
        verbose_name_plural = _('настройки уведомлений')

    def __str__(self):
        return f"Настройки уведомлений {self.user.email}"


class NotificationLog(models.Model):
    """Хранит историю отправленных уведомлений для отладки и аналитики."""

    CHANNEL_CHOICES = (
        ('telegram', 'Telegram'),
        ('email', 'Email'),
    )

    TYPE_CHOICES = (
        ('homework_submitted', 'ДЗ сдано учеником'),
        ('homework_graded', 'ДЗ проверено учителем'),
        ('homework_deadline', 'Напоминание о дедлайне ДЗ'),
        ('subscription_expiring', 'Истекает подписка'),
        ('payment_success', 'Оплата прошла успешно'),
        ('lesson_reminder', 'Напоминание об уроке'),
        ('new_homework', 'Новое домашнее задание'),
        # Аналитика — для учителя
        ('absence_alert', 'Серия пропусков ученика'),
        ('performance_drop_alert', 'Падение успеваемости ученика'),
        ('group_health_alert', 'Аномалии по группе'),
        ('grading_backlog', 'Непроверенные ДЗ накопились'),
        ('inactive_student_alert', 'Неактивный ученик'),
        # Новые события — для учителя
        ('student_joined', 'Ученик вступил в группу'),
        ('student_left', 'Ученик покинул группу'),
        ('recording_ready', 'Запись урока готова'),
        # Новые события — для ученика
        ('lesson_link_sent', 'Ссылка на урок отправлена'),
        ('materials_added', 'Добавлены материалы к уроку'),
        ('welcome_to_group', 'Добро пожаловать в группу'),
        # Аналитика — для ученика
        ('student_absence_warning', 'Предупреждение о пропусках'),
        ('control_point_deadline', 'Напоминание о контрольной точке'),
        ('achievement', 'Достижение/прогресс'),
        ('student_inactivity_nudge', 'Напоминание об активности'),
        # Хранилище (сохраняем для совместимости)
        ('storage_warning', 'Хранилище почти заполнено'),
        ('storage_limit_exceeded', 'Хранилище заполнено'),
        ('recording_available', 'Запись урока доступна'),
    )

    STATUS_CHOICES = (
        ('sent', 'Отправлено'),
        ('skipped', 'Пропущено'),
        ('failed', 'Ошибка'),
    )

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notification_logs')
    notification_type = models.CharField(max_length=64, choices=TYPE_CHOICES)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default='telegram')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='sent')
    message = models.TextField()
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('лог уведомлений')
        verbose_name_plural = _('логи уведомлений')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.notification_type} → {self.user.email} ({self.status})"


class NotificationMute(models.Model):
    """
    Модель для отключения уведомлений по конкретным группам или ученикам.
    Позволяет учителю заглушить уведомления от определённых сущностей,
    не отключая глобально весь тип уведомлений.
    """
    
    MUTE_TYPE_CHOICES = (
        ('group', 'Группа'),
        ('student', 'Ученик'),
    )
    
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='notification_mutes',
        verbose_name=_('пользователь'),
        help_text=_('Учитель, который заглушает уведомления')
    )
    mute_type = models.CharField(
        _('тип'),
        max_length=20,
        choices=MUTE_TYPE_CHOICES,
        help_text=_('Заглушить группу или конкретного ученика')
    )
    # Ссылка на группу (если mute_type == 'group')
    group = models.ForeignKey(
        'schedule.Group',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notification_mutes',
        verbose_name=_('группа')
    )
    # Ссылка на ученика (если mute_type == 'student')
    student = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='muted_by_teachers',
        verbose_name=_('ученик')
    )
    # Опционально: какие именно типы уведомлений заглушить (если пусто — все)
    muted_notification_types = models.JSONField(
        _('типы уведомлений'),
        default=list,
        blank=True,
        help_text=_('Список типов уведомлений для заглушки (пусто = все)')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('заглушка уведомлений')
        verbose_name_plural = _('заглушки уведомлений')
        ordering = ['-created_at']
        # Уникальность: один пользователь не может заглушить одну группу/ученика дважды
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'mute_type', 'group'],
                condition=models.Q(mute_type='group'),
                name='unique_group_mute'
            ),
            models.UniqueConstraint(
                fields=['user', 'mute_type', 'student'],
                condition=models.Q(mute_type='student'),
                name='unique_student_mute'
            ),
        ]
    
    def __str__(self):
        if self.mute_type == 'group' and self.group:
            return f"{self.user.email} заглушил группу {self.group.name}"
        elif self.mute_type == 'student' and self.student:
            return f"{self.user.email} заглушил ученика {self.student.get_full_name()}"
        return f"NotificationMute #{self.pk}"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.mute_type == 'group' and not self.group:
            raise ValidationError({'group': _('Укажите группу для заглушки')})
        if self.mute_type == 'student' and not self.student:
            raise ValidationError({'student': _('Укажите ученика для заглушки')})


# ============================================================================
# НОВЫЕ МОДЕЛИ: СИСТЕМА ПОСЕЩЕНИЙ И РЕЙТИНГА
# ============================================================================

class AttendanceRecord(models.Model):
    """
    Запись посещения ученика на занятие.
    Может быть автоматически заполнена при подключении к Zoom или вручную учителем.
    """
    
    STATUS_ATTENDED = 'attended'
    STATUS_ABSENT = 'absent'
    STATUS_WATCHED_RECORDING = 'watched_recording'
    
    STATUS_CHOICES = [
        (STATUS_ATTENDED, '✅ Был'),
        (STATUS_ABSENT, '❌ Не был'),
        (STATUS_WATCHED_RECORDING, '👁️ Посмотрел запись'),
    ]
    
    lesson = models.ForeignKey(
        'schedule.Lesson',
        on_delete=models.CASCADE,
        related_name='attendance_records',
        verbose_name=_('занятие')
    )
    student = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='attendance_records',
        limit_choices_to={'role': 'student'},
        verbose_name=_('ученик')
    )
    
    status = models.CharField(
        _('статус посещения'),
        max_length=20,
        choices=STATUS_CHOICES,
        null=True,
        blank=True
    )
    auto_recorded = models.BooleanField(
        _('автоматически заполнено'),
        default=False,
        help_text=_('True если заполнено при подключении к Zoom')
    )
    recorded_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='manual_attendance_records',
        limit_choices_to={'role': 'teacher'},
        verbose_name=_('заполнил (учитель)')
    )
    
    recorded_at = models.DateTimeField(_('дата создания'), auto_now_add=True)
    updated_at = models.DateTimeField(_('дата обновления'), auto_now=True)
    
    class Meta:
        verbose_name = _('запись посещения')
        verbose_name_plural = _('записи посещения')
        unique_together = ('lesson', 'student')
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['lesson', 'student']),
            models.Index(fields=['student', '-recorded_at']),
            models.Index(fields=['status', 'recorded_at']),
        ]
    
    def __str__(self):
        status_label = dict(self.STATUS_CHOICES).get(self.status, '?')
        return f"{self.student.get_full_name()} - {self.lesson.title}: {status_label}"


class UserRating(models.Model):
    """
    Рейтинг ученика (очки).
    Может быть как для группы, так и индивидуальный (group=NULL).
    Очки суммируют посещения, ДЗ, контрольные точки.
    """
    
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='ratings',
        limit_choices_to={'role': 'student'},
        verbose_name=_('ученик')
    )
    group = models.ForeignKey(
        'schedule.Group',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='student_ratings',
        verbose_name=_('группа')
    )
    
    total_points = models.IntegerField(
        _('общие очки'),
        default=0,
        help_text=_('Сумма всех очков (посещение + ДЗ + контроль)')
    )
    attendance_points = models.IntegerField(
        _('очки за посещение'),
        default=0,
        help_text=_('Очки за посещения занятий')
    )
    homework_points = models.IntegerField(
        _('очки за ДЗ'),
        default=0,
        help_text=_('Очки за выполненные домашние задания')
    )
    control_points_value = models.IntegerField(
        _('очки за контрольные точки'),
        default=0,
        db_column='control_points',
        help_text=_('Очки за пройденные контрольные точки')
    )
    
    rank = models.IntegerField(
        _('место в рейтинге'),
        default=0,
        help_text=_('Место в рейтинге группы (0 если нет группы)')
    )
    
    updated_at = models.DateTimeField(_('дата обновления'), auto_now=True)
    
    class Meta:
        verbose_name = _('рейтинг ученика')
        verbose_name_plural = _('рейтинги учеников')
        unique_together = ('user', 'group')
        ordering = ['-total_points']
        indexes = [
            models.Index(fields=['group', '-total_points']),
            models.Index(fields=['user', 'group']),
        ]
    
    def __str__(self):
        group_name = f" ({self.group.name})" if self.group else " (индивидуальный)"
        return f"{self.user.get_full_name()}{group_name}: {self.total_points} очков"
    
    def recalculate_total(self):
        """Пересчитать общее количество очков"""
        self.total_points = (
            self.attendance_points + 
            self.homework_points + 
            self.control_points_value
        )


class IndividualStudent(models.Model):
    """
    Индивидуальный ученик (отдельная категория).
    Может быть БЕЗ группы (полностью индивидуальные занятия)
    или С группой (индивидуальные + групповые занятия).
    """
    
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='individual_student_profile',
        limit_choices_to={'role': 'student'},
        verbose_name=_('ученик')
    )
    teacher = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='individual_students',
        limit_choices_to={'role': 'teacher'},
        verbose_name=_('основной учитель')
    )
    teacher_notes = models.TextField(
        _('замечания учителя'),
        blank=True,
        default='',
        help_text=_('Заметки преподавателя об ученике')
    )
    created_at = models.DateTimeField(_('дата создания'), auto_now_add=True)
    updated_at = models.DateTimeField(_('дата обновления'), auto_now=True)
    
    class Meta:
        verbose_name = _('индивидуальный ученик')
        verbose_name_plural = _('индивидуальные ученики')
    
    def __str__(self):
        return f"{self.user.get_full_name()} (индивидуальный)"


# ============================================================================
# РЕФЕРАЛЬНЫЕ ССЫЛКИ И ПАРТНЁРЫ (для админки)
# ============================================================================

class ReferralLink(models.Model):
    """
    Реферальная ссылка для рекламы в ТГ-каналах и других источниках.
    Каждая ссылка имеет уникальный код и привязана к партнёру/каналу.
    """
    code = models.CharField(
        _('код ссылки'),
        max_length=32,
        unique=True,
        help_text=_('Уникальный код для URL (?ref=CODE)')
    )
    name = models.CharField(
        _('название'),
        max_length=128,
        help_text=_('Название для идентификации (например, "ТГ канал @example")')
    )
    partner_name = models.CharField(
        _('имя партнёра'),
        max_length=128,
        blank=True,
        default='',
        help_text=_('Имя/контакт человека, который рекламирует')
    )
    partner_contact = models.CharField(
        _('контакт партнёра'),
        max_length=255,
        blank=True,
        default='',
        help_text=_('Telegram/email/телефон партнёра для выплат')
    )
    commission_amount = models.DecimalField(
        _('комиссия за оплату'),
        max_digits=10,
        decimal_places=2,
        default=Decimal('750.00'),
        help_text=_('Сумма выплаты партнёру за каждую оплату')
    )
    utm_source = models.CharField(max_length=64, blank=True, default='telegram')
    utm_medium = models.CharField(max_length=64, blank=True, default='referral')
    utm_campaign = models.CharField(max_length=64, blank=True, default='')
    
    # Статистика (обновляется триггерами или вручную)
    clicks_count = models.IntegerField(_('кликов'), default=0)
    registrations_count = models.IntegerField(_('регистраций'), default=0)
    payments_count = models.IntegerField(_('оплат'), default=0)
    total_earned = models.DecimalField(
        _('всего заработано партнёром'),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total_paid_out = models.DecimalField(
        _('выплачено партнёру'),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    is_active = models.BooleanField(_('активна'), default=True)
    created_at = models.DateTimeField(_('создана'), auto_now_add=True)
    updated_at = models.DateTimeField(_('обновлена'), auto_now=True)
    notes = models.TextField(_('заметки'), blank=True, default='')
    
    class Meta:
        verbose_name = _('реферальная ссылка')
        verbose_name_plural = _('реферальные ссылки')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['is_active', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    def get_full_url(self, base_url='https://lectio.space'):
        """Генерирует полную реферальную ссылку"""
        params = f"ref={self.code}"
        if self.utm_source:
            params += f"&utm_source={self.utm_source}"
        if self.utm_medium:
            params += f"&utm_medium={self.utm_medium}"
        if self.utm_campaign:
            params += f"&utm_campaign={self.utm_campaign}"
        return f"{base_url}/?{params}"
    
    def increment_clicks(self):
        """Увеличить счётчик кликов"""
        self.clicks_count += 1
        self.save(update_fields=['clicks_count', 'updated_at'])
    
    def increment_registrations(self):
        """Увеличить счётчик регистраций"""
        self.registrations_count += 1
        self.save(update_fields=['registrations_count', 'updated_at'])
    
    def record_payment(self, amount=None):
        """Записать оплату и комиссию"""
        self.payments_count += 1
        commission = amount if amount else self.commission_amount
        self.total_earned += commission
        self.save(update_fields=['payments_count', 'total_earned', 'updated_at'])
    
    def record_payout(self, amount):
        """Записать выплату партнёру"""
        self.total_paid_out += amount
        self.save(update_fields=['total_paid_out', 'updated_at'])
    
    @classmethod
    def generate_code(cls, length=8):
        """Генерирует уникальный код"""
        while True:
            code = get_random_string(length, allowed_chars=string.ascii_uppercase + string.digits)
            if not cls.objects.filter(code=code).exists():
                return code


class ReferralClick(models.Model):
    """
    Лог кликов по реферальным ссылкам для детальной аналитики.
    """
    link = models.ForeignKey(
        ReferralLink,
        on_delete=models.CASCADE,
        related_name='clicks',
        verbose_name=_('ссылка')
    )
    ip_address = models.GenericIPAddressField(_('IP адрес'), null=True, blank=True)
    user_agent = models.TextField(_('User Agent'), blank=True, default='')
    referer = models.URLField(_('Referer'), blank=True, default='')
    cookie_id = models.CharField(max_length=64, blank=True, default='')
    created_at = models.DateTimeField(_('время клика'), auto_now_add=True)
    
    # Результат клика
    resulted_in_registration = models.BooleanField(_('привёл к регистрации'), default=False)
    registered_user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='referral_clicks',
        verbose_name=_('зарегистрированный пользователь')
    )
    
    class Meta:
        verbose_name = _('клик по реферальной ссылке')
        verbose_name_plural = _('клики по реферальным ссылкам')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['link', '-created_at']),
            models.Index(fields=['cookie_id']),
        ]
    
    def __str__(self):
        return f"Click on {self.link.code} at {self.created_at}"


# =============================================================================
# МОДЕЛИ ДЛЯ РАСШИРЕННОЙ АНАЛИТИКИ УЧЕНИКОВ
# =============================================================================

class StudentActivityLog(models.Model):
    """
    Лог активности ученика для построения хитмапа активности.
    Записывает действия с привязкой ко времени.
    """
    ACTION_TYPES = (
        ('homework_start', 'Начал ДЗ'),
        ('homework_submit', 'Сдал ДЗ'),
        ('answer_save', 'Сохранил ответ'),
        ('lesson_join', 'Зашёл на урок'),
        ('recording_watch', 'Смотрел запись'),
        ('chat_message', 'Написал в чат'),
        ('question_ask', 'Задал вопрос'),
        ('login', 'Вход в систему'),
    )
    
    student = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='activity_logs',
        limit_choices_to={'role': 'student'},
        verbose_name=_('ученик')
    )
    action_type = models.CharField(
        _('тип действия'),
        max_length=30,
        choices=ACTION_TYPES
    )
    group = models.ForeignKey(
        'schedule.Group',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_activity_logs',
        verbose_name=_('группа')
    )
    
    # Детали действия
    details = models.JSONField(
        default=dict,
        blank=True,
        help_text='Дополнительные данные: {"homework_id": 123, "score": 85}'
    )
    
    # Временные метки для хитмапа
    created_at = models.DateTimeField(auto_now_add=True)
    day_of_week = models.PositiveSmallIntegerField(
        _('день недели'),
        help_text='0=Понедельник, 6=Воскресенье'
    )
    hour_of_day = models.PositiveSmallIntegerField(
        _('час дня'),
        help_text='0-23'
    )
    
    class Meta:
        verbose_name = _('лог активности ученика')
        verbose_name_plural = _('логи активности учеников')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['student', '-created_at'], name='activity_student_idx'),
            models.Index(fields=['day_of_week', 'hour_of_day'], name='activity_heatmap_idx'),
            models.Index(fields=['action_type', 'created_at'], name='activity_type_idx'),
        ]
    
    def __str__(self):
        return f"{self.student.email} - {self.get_action_type_display()} @ {self.created_at}"
    
    def save(self, *args, **kwargs):
        if not self.pk:
            from django.utils import timezone
            now = timezone.now()
            self.day_of_week = now.weekday()
            self.hour_of_day = now.hour
        super().save(*args, **kwargs)


class ChatAnalyticsSummary(models.Model):
    """
    Агрегированная статистика активности ученика в чатах группы.
    Пересчитывается периодически.
    """
    student = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='chat_analytics',
        limit_choices_to={'role': 'student'},
        verbose_name=_('ученик')
    )
    group = models.ForeignKey(
        'schedule.Group',
        on_delete=models.CASCADE,
        related_name='student_chat_analytics',
        verbose_name=_('группа')
    )
    period_start = models.DateField(_('начало периода'))
    period_end = models.DateField(_('конец периода'))
    
    # Метрики активности
    total_messages = models.IntegerField(default=0, help_text='Всего сообщений')
    questions_asked = models.IntegerField(default=0, help_text='Вопросов задано')
    answers_given = models.IntegerField(default=0, help_text='Ответов на вопросы других')
    helpful_messages = models.IntegerField(default=0, help_text='Полезных сообщений (помощь)')
    
    # Упоминания
    times_mentioned = models.IntegerField(default=0, help_text='Сколько раз упомянули этого ученика')
    times_mentioning_others = models.IntegerField(default=0, help_text='Сколько раз упоминал других')
    
    # Сентимент
    avg_sentiment = models.FloatField(null=True, blank=True, help_text='Средний сентимент -1..+1')
    positive_messages = models.IntegerField(default=0)
    negative_messages = models.IntegerField(default=0)
    neutral_messages = models.IntegerField(default=0)
    
    # Индекс влиятельности (0-100)
    influence_score = models.IntegerField(
        default=0,
        help_text='Индекс влиятельности: частота упоминаний + ответы на вопросы'
    )
    
    # Роль в группе (вычисляемая)
    ROLE_CHOICES = (
        ('leader', '👑 Лидер'),
        ('helper', '🤝 Помощник'),
        ('active', '💬 Активный'),
        ('observer', '👀 Наблюдатель'),
        ('silent', '🔇 Молчун'),
    )
    detected_role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='observer',
        help_text='Автоматически определённая роль в группе'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('статистика чата ученика')
        verbose_name_plural = _('статистика чатов учеников')
        unique_together = ('student', 'group', 'period_start', 'period_end')
        indexes = [
            models.Index(fields=['group', 'period_end'], name='chat_group_period_idx'),
            models.Index(fields=['influence_score'], name='chat_influence_idx'),
        ]
    
    def __str__(self):
        return f"{self.student.email} in {self.group.name}: {self.total_messages} msgs"
    
    def compute_influence_score(self):
        """Вычисляет индекс влиятельности"""
        # Формула: упоминания*3 + ответы_помощь*2 + всего_сообщений*0.1
        score = (
            self.times_mentioned * 3 +
            self.answers_given * 2 +
            self.helpful_messages * 2 +
            int(self.total_messages * 0.1)
        )
        self.influence_score = min(100, score)
        return self.influence_score
    
    def detect_role(self):
        """Определяет роль ученика в группе на основе метрик"""
        if self.influence_score >= 50 and self.total_messages >= 20:
            self.detected_role = 'leader'
        elif self.helpful_messages >= 5 or self.answers_given >= 10:
            self.detected_role = 'helper'
        elif self.total_messages >= 10:
            self.detected_role = 'active'
        elif self.total_messages >= 3:
            self.detected_role = 'observer'
        else:
            self.detected_role = 'silent'
        return self.detected_role


class SystemErrorEvent(models.Model):
    """Ошибки и сбои системы/процессов для админ-модерации."""

    SEVERITY_CHOICES = (
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='error', db_index=True)
    source = models.CharField(max_length=80, default='backend', db_index=True)
    code = models.CharField(max_length=80, default='', db_index=True)

    message = models.TextField(default='')
    details = models.JSONField(default=dict, blank=True)

    teacher = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='system_errors',
        limit_choices_to={'role': 'teacher'},
        db_index=True,
    )

    request_path = models.CharField(max_length=300, blank=True, default='')
    request_method = models.CharField(max_length=10, blank=True, default='')
    process = models.CharField(max_length=80, blank=True, default='')

    fingerprint = models.CharField(max_length=64, db_index=True)
    occurrences = models.PositiveIntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(default=timezone.now, db_index=True)

    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_system_errors',
        limit_choices_to={'role': 'admin'},
    )

    class Meta:
        ordering = ['-last_seen_at']
        indexes = [
            models.Index(fields=['severity', 'last_seen_at'], name='sys_err_sev_ts_idx'),
            models.Index(fields=['teacher', 'last_seen_at'], name='sys_err_teacher_ts_idx'),
            models.Index(fields=['fingerprint', 'resolved_at'], name='sys_err_fp_res_idx'),
        ]

    def __str__(self):
        t = getattr(self.teacher, 'email', None) or 'no-teacher'
        return f"{self.severity}:{self.source}:{self.code} ({t})"
