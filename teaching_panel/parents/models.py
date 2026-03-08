import uuid
from django.db import models
from django.conf import settings
from schedule.models import Group


class ParentAccess(models.Model):
    """
    Единая точка доступа родителя к данным ученика.
    Один ученик = один токен навсегда.
    Учителя добавляют свои гранты к этому объекту.
    """
    token = models.UUIDField(
        unique=True, default=uuid.uuid4, db_index=True,
        help_text='Magic-link токен для доступа без авторизации'
    )
    student = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='parent_access',
        limit_choices_to={'role': 'student'}
    )

    parent_name = models.CharField(
        max_length=200, blank=True, default='',
        help_text='Имя родителя (опционально)'
    )
    parent_contact = models.CharField(
        max_length=200, blank=True, default='',
        help_text='Контакт родителя: телефон, telegram и т.д.'
    )

    # Telegram-алертинг (один на всех учителей)
    telegram_chat_id = models.CharField(
        max_length=50, blank=True, null=True,
        help_text='Chat ID для Telegram-уведомлений родителю'
    )
    telegram_connected = models.BooleanField(default=False)
    alert_missed_hw = models.BooleanField(
        default=True,
        help_text='Алерт: ДЗ не сдано более 3 дней после дедлайна'
    )
    alert_missed_lesson = models.BooleanField(
        default=True,
        help_text='Алерт: ученик пропустил урок'
    )
    alert_low_balance = models.BooleanField(
        default=True,
        help_text='Алерт: баланс уроков <= 2 (будущее)'
    )
    alert_new_grade = models.BooleanField(
        default=False,
        help_text='Алерт: новая оценка за контрольную'
    )

    is_active = models.BooleanField(default=True)
    last_viewed_at = models.DateTimeField(null=True, blank=True)
    view_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'доступ для родителя'
        verbose_name_plural = 'доступы для родителей'

    def __str__(self):
        return f"ParentAccess: {self.student.get_full_name()} ({self.token})"


class ParentAccessGrant(models.Model):
    """
    Грант конкретного учителя — какие данные он открывает родителю.
    subject_label = кастомное название предмета (задаёт учитель).
    
    Каждый учитель видит и управляет ТОЛЬКО своим грантом.
    На parent dashboard отображается как отдельный таб-предмет.
    """
    parent_access = models.ForeignKey(
        ParentAccess, on_delete=models.CASCADE,
        related_name='grants'
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='parent_grants',
        limit_choices_to={'role': 'teacher'}
    )
    group = models.ForeignKey(
        Group, on_delete=models.CASCADE,
        help_text='Группа, по которой учитель открывает данные'
    )

    subject_label = models.CharField(
        max_length=200,
        help_text='Название предмета для родительского дашборда (задаёт учитель)'
    )

    # Флаги видимости секций
    show_attendance = models.BooleanField(default=True)
    show_homework = models.BooleanField(default=True)
    show_grades = models.BooleanField(default=True)
    # Заглушки на будущее — поля уже есть, UI покажет "Скоро"
    show_knowledge_map = models.BooleanField(default=True)
    show_finance = models.BooleanField(default=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['parent_access', 'teacher', 'group']
        verbose_name = 'грант доступа учителя'
        verbose_name_plural = 'гранты доступа учителей'

    def __str__(self):
        return f"{self.subject_label} ({self.teacher.get_full_name()}) → {self.parent_access.student.get_full_name()}"


class ParentComment(models.Model):
    """
    Комментарий учителя для родителя.
    Лента комментариев — учитель может писать в любой момент.
    Отображается на parent dashboard внутри таба предмета.
    """
    grant = models.ForeignKey(
        ParentAccessGrant, on_delete=models.CASCADE,
        related_name='comments'
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='parent_comments'
    )
    text = models.TextField(help_text='Текст комментария для родителя')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'комментарий для родителя'
        verbose_name_plural = 'комментарии для родителей'

    def __str__(self):
        return f"Comment by {self.teacher.get_full_name()} on {self.created_at:%Y-%m-%d}"
