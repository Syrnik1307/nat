"""
Bot models — запланированные сообщения (Telegram).
"""
from django.db import models
from django.conf import settings


class ScheduledMessage(models.Model):
    """Запланированное сообщение (Telegram)."""

    class MessageType(models.TextChoices):
        LESSON_REMINDER = 'lesson_reminder', 'Напоминание об уроке'
        HW_REMINDER = 'hw_reminder', 'Напоминание о ДЗ'
        HW_DEADLINE = 'hw_deadline', 'Напоминание о дедлайне'
        LESSON_CANCEL = 'lesson_cancel', 'Отмена урока'
        LESSON_RESCHEDULE = 'lesson_reschedule', 'Перенос урока'
        CUSTOM = 'custom', 'Произвольное сообщение'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Ожидает отправки'
        SENDING = 'sending', 'Отправляется'
        SENT = 'sent', 'Отправлено'
        PARTIALLY_SENT = 'partially_sent', 'Частично отправлено'
        CANCELLED = 'cancelled', 'Отменено'
        FAILED = 'failed', 'Ошибка'

    message_type = models.CharField(
        max_length=50, choices=MessageType.choices, default=MessageType.CUSTOM,
        verbose_name='Тип сообщения',
    )
    content = models.TextField(verbose_name='Текст сообщения')
    scheduled_at = models.DateTimeField(verbose_name='Запланировано на')
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name='Отправлено')
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING,
        verbose_name='Статус',
    )
    recipients_count = models.PositiveIntegerField(default=0, verbose_name='Всего получателей')
    sent_count = models.PositiveIntegerField(default=0, verbose_name='Успешно отправлено')
    failed_count = models.PositiveIntegerField(default=0, verbose_name='Ошибок')
    error_message = models.TextField(blank=True, default='', verbose_name='Сообщение об ошибке')

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='scheduled_messages', verbose_name='Преподаватель',
    )
    lesson = models.ForeignKey(
        'schedule.Lesson', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='scheduled_messages',
        verbose_name='Урок',
    )
    homework = models.ForeignKey(
        'homework.Homework', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='scheduled_messages',
        verbose_name='Домашнее задание',
    )
    target_groups = models.ManyToManyField(
        'schedule.Group', blank=True,
        related_name='scheduled_messages', verbose_name='Группы',
    )
    target_students = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True,
        related_name='received_scheduled_messages', verbose_name='Ученики',
    )
    school = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='scheduled_messages',
        null=True, blank=True,
        help_text='Школа',
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')

    class Meta:
        verbose_name = 'Запланированное сообщение'
        verbose_name_plural = 'Запланированные сообщения'
        ordering = ['-scheduled_at']

    def __str__(self):
        return f'{self.message_type}: {self.content[:50]}'
