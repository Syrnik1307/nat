from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

"""Core domain models.

Duplicate educational entities (Lesson, Assignment, Submission) were moved to dedicated
apps: schedule (for lessons with Zoom pooling) and homework (for assignments & submissions).
This module now keeps only Course for high-level grouping. Migration will drop old tables.
"""


class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='courses_taught')
    students = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='courses_enrolled', blank=True)
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
        
        return cls.objects.create(**log_data)
