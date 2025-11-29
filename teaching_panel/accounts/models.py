from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.utils.crypto import get_random_string
import random
import string
import uuid


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
    
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='messages', verbose_name='Чат')
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_messages', verbose_name='Отправитель')
    text = models.TextField('Текст сообщения')
    is_read = models.BooleanField('Прочитано', default=False)
    created_at = models.DateTimeField('Отправлено', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)
    
    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.sender.get_full_name()}: {self.text[:50]}"


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
