"""
Модели для Telegram Bot Command Center
"""
from django.db import models
from django.conf import settings
from django.utils import timezone


class ScheduledMessage(models.Model):
    """Отложенные сообщения для рассылки"""
    
    MESSAGE_TYPES = (
        ('lesson_reminder', 'Напоминание об уроке'),
        ('hw_reminder', 'Напоминание о ДЗ'),
        ('hw_deadline', 'Напоминание о дедлайне'),
        ('lesson_cancel', 'Отмена урока'),
        ('lesson_reschedule', 'Перенос урока'),
        ('custom', 'Произвольное сообщение'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Ожидает отправки'),
        ('sending', 'Отправляется'),
        ('sent', 'Отправлено'),
        ('partially_sent', 'Частично отправлено'),
        ('cancelled', 'Отменено'),
        ('failed', 'Ошибка'),
    )
    
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='scheduled_messages',
        verbose_name='Преподаватель'
    )
    message_type = models.CharField(
        'Тип сообщения',
        max_length=50,
        choices=MESSAGE_TYPES,
        default='custom'
    )
    content = models.TextField('Текст сообщения')
    
    # Целевая аудитория
    target_groups = models.ManyToManyField(
        'schedule.Group',
        blank=True,
        related_name='scheduled_messages',
        verbose_name='Группы'
    )
    target_students = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='received_scheduled_messages',
        verbose_name='Ученики'
    )
    
    # Связь с уроком/ДЗ (опционально)
    lesson = models.ForeignKey(
        'schedule.Lesson',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='scheduled_messages',
        verbose_name='Урок'
    )
    homework = models.ForeignKey(
        'homework.Homework',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='scheduled_messages',
        verbose_name='Домашнее задание'
    )
    
    # Расписание
    scheduled_at = models.DateTimeField('Запланировано на')
    sent_at = models.DateTimeField('Отправлено', null=True, blank=True)
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    # Статистика отправки
    recipients_count = models.PositiveIntegerField('Всего получателей', default=0)
    sent_count = models.PositiveIntegerField('Успешно отправлено', default=0)
    failed_count = models.PositiveIntegerField('Ошибок', default=0)
    error_message = models.TextField('Сообщение об ошибке', blank=True, default='')
    
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)
    
    class Meta:
        verbose_name = 'Запланированное сообщение'
        verbose_name_plural = 'Запланированные сообщения'
        ordering = ['-scheduled_at']
        indexes = [
            models.Index(fields=['status', 'scheduled_at']),
            models.Index(fields=['teacher', 'status']),
        ]
    
    def __str__(self):
        return f"{self.get_message_type_display()} от {self.teacher} на {self.scheduled_at}"
    
    def mark_sending(self):
        self.status = 'sending'
        self.save(update_fields=['status', 'updated_at'])
    
    def mark_sent(self, sent_count: int, failed_count: int):
        self.sent_at = timezone.now()
        self.sent_count = sent_count
        self.failed_count = failed_count
        if failed_count == 0:
            self.status = 'sent'
        elif sent_count > 0:
            self.status = 'partially_sent'
        else:
            self.status = 'failed'
        self.save(update_fields=['status', 'sent_at', 'sent_count', 'failed_count', 'updated_at'])
    
    def cancel(self):
        if self.status == 'pending':
            self.status = 'cancelled'
            self.save(update_fields=['status', 'updated_at'])
            return True
        return False


class BroadcastLog(models.Model):
    """Лог всех рассылок (для аудита и аналитики)"""
    
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='broadcast_logs',
        verbose_name='Преподаватель'
    )
    message_type = models.CharField('Тип сообщения', max_length=50)
    content_preview = models.CharField('Превью сообщения', max_length=200)
    
    # Статистика
    target_count = models.PositiveIntegerField('Целевых получателей', default=0)
    sent_count = models.PositiveIntegerField('Успешно отправлено', default=0)
    failed_count = models.PositiveIntegerField('Ошибок', default=0)
    
    # Время
    started_at = models.DateTimeField('Начало', auto_now_add=True)
    completed_at = models.DateTimeField('Завершено', null=True, blank=True)
    duration_seconds = models.FloatField('Длительность (сек)', null=True, blank=True)
    
    # Связи (для отчётности)
    scheduled_message = models.ForeignKey(
        ScheduledMessage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logs',
        verbose_name='Запланированное сообщение'
    )
    
    class Meta:
        verbose_name = 'Лог рассылки'
        verbose_name_plural = 'Логи рассылок'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['teacher', 'started_at']),
            models.Index(fields=['message_type', 'started_at']),
        ]
    
    def __str__(self):
        return f"{self.message_type}: {self.content_preview[:50]}..."
    
    def complete(self, sent_count: int, failed_count: int):
        self.completed_at = timezone.now()
        self.sent_count = sent_count
        self.failed_count = failed_count
        if self.started_at:
            self.duration_seconds = (self.completed_at - self.started_at).total_seconds()
        self.save(update_fields=['completed_at', 'sent_count', 'failed_count', 'duration_seconds'])


class MessageTemplate(models.Model):
    """Шаблоны сообщений для быстрой отправки"""
    
    TEMPLATE_TYPES = (
        ('lesson_reminder', 'Напоминание об уроке'),
        ('hw_reminder', 'Напоминание о ДЗ'),
        ('hw_deadline', 'Напоминание о дедлайне'),
        ('lesson_cancel', 'Отмена урока'),
        ('custom', 'Произвольный'),
    )
    
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='message_templates',
        verbose_name='Преподаватель',
        help_text='Если пусто - системный шаблон'
    )
    title = models.CharField('Название шаблона', max_length=100)
    content = models.TextField(
        'Текст шаблона',
        help_text='Плейсхолдеры: {student_name}, {group}, {lesson_title}, {lesson_time}, {hw_title}, {deadline}, {zoom_link}'
    )
    message_type = models.CharField(
        'Тип шаблона',
        max_length=50,
        choices=TEMPLATE_TYPES,
        default='custom'
    )
    is_system = models.BooleanField(
        'Системный шаблон',
        default=False,
        help_text='Системные шаблоны доступны всем'
    )
    is_active = models.BooleanField('Активен', default=True)
    
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)
    
    class Meta:
        verbose_name = 'Шаблон сообщения'
        verbose_name_plural = 'Шаблоны сообщений'
        ordering = ['-is_system', 'title']
    
    def __str__(self):
        prefix = '[Системный] ' if self.is_system else ''
        return f"{prefix}{self.title}"
    
    def render(self, **kwargs) -> str:
        """Рендерит шаблон с переданными параметрами"""
        content = self.content
        for key, value in kwargs.items():
            placeholder = '{' + key + '}'
            content = content.replace(placeholder, str(value or ''))
        return content


class BroadcastRateLimit(models.Model):
    """Отслеживание лимитов рассылок для защиты от спама"""
    
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='broadcast_rate_limits',
        verbose_name='Преподаватель'
    )
    hour_key = models.CharField(
        'Ключ часа',
        max_length=20,
        help_text='Формат: YYYY-MM-DD-HH'
    )
    day_key = models.CharField(
        'Ключ дня',
        max_length=12,
        help_text='Формат: YYYY-MM-DD'
    )
    hourly_count = models.PositiveIntegerField('Рассылок за час', default=0)
    daily_count = models.PositiveIntegerField('Рассылок за день', default=0)
    last_broadcast_at = models.DateTimeField('Последняя рассылка', null=True, blank=True)
    
    class Meta:
        verbose_name = 'Лимит рассылок'
        verbose_name_plural = 'Лимиты рассылок'
        unique_together = ['teacher', 'hour_key']
        indexes = [
            models.Index(fields=['teacher', 'day_key']),
        ]
    
    def __str__(self):
        return f"{self.teacher} - {self.hour_key}: {self.hourly_count}/час, {self.daily_count}/день"
