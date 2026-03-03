from django.db import models
from django.conf import settings
from schedule.models import Group


class ExamType(models.Model):
    """Тип экзамена: ЕГЭ, ОГЭ, или кастомный от учителя."""
    slug = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default='')
    is_preset = models.BooleanField(default=False, help_text='True для встроенных шаблонов (ЕГЭ/ОГЭ)')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_exam_types'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'тип экзамена'
        verbose_name_plural = 'типы экзаменов'

    def __str__(self):
        return self.name


class Subject(models.Model):
    """Предмет: Математика (профиль), Русский язык и т.д."""
    exam_type = models.ForeignKey(ExamType, on_delete=models.CASCADE, related_name='subjects')
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=100)
    icon = models.CharField(max_length=50, blank=True, default='book-open',
                            help_text='Имя иконки из lucide-react')
    order = models.IntegerField(default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_subjects'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'name']
        unique_together = ['exam_type', 'slug']
        verbose_name = 'предмет'
        verbose_name_plural = 'предметы'

    def __str__(self):
        return f"{self.exam_type.name} - {self.name}"


class Topic(models.Model):
    """Тема/задание экзамена. Например: ЕГЭ Математика — Задание 1 (Планиметрия)."""
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='topics')
    number = models.IntegerField(help_text='Номер задания в экзамене')
    title = models.CharField(max_length=255, help_text='Название темы')
    max_points = models.IntegerField(default=1, help_text='Максимальный балл за задание')
    description = models.TextField(blank=True, default='')
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['number']
        unique_together = ['subject', 'number']
        verbose_name = 'тема экзамена'
        verbose_name_plural = 'темы экзамена'

    def __str__(self):
        return f"#{self.number}. {self.title} (макс. {self.max_points}б)"


class ExamAssignment(models.Model):
    """Назначение предмета экзамена группе/ученику учителем."""
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='exam_assignments', limit_choices_to={'role': 'teacher'}
    )
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='assignments')
    group = models.ForeignKey(
        Group, on_delete=models.CASCADE, null=True, blank=True,
        related_name='exam_assignments'
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        null=True, blank=True, related_name='assigned_exams',
        limit_choices_to={'role': 'student'}
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'назначение экзамена'
        verbose_name_plural = 'назначения экзаменов'

    def __str__(self):
        target = self.group or self.student
        return f"{self.subject} -> {target}"


class StudentTopicScore(models.Model):
    """Кэшированный агрегированный балл ученика по теме экзамена."""
    TREND_CHOICES = (
        ('up', 'Растёт'),
        ('stable', 'Стабильно'),
        ('down', 'Снижается'),
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='topic_scores', limit_choices_to={'role': 'student'},
        db_index=True
    )
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='student_scores')
    score_percent = models.FloatField(default=0, help_text='Процент освоения 0-100')
    attempts_count = models.IntegerField(default=0)
    total_points_earned = models.FloatField(default=0)
    total_points_possible = models.FloatField(default=0)
    trend = models.CharField(max_length=10, choices=TREND_CHOICES, default='stable')
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['student', 'topic']
        verbose_name = 'балл ученика по теме'
        verbose_name_plural = 'баллы учеников по темам'

    def __str__(self):
        return f"{self.student.email}: {self.topic} - {self.score_percent:.0f}%"
