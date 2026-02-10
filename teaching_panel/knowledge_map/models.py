"""
Карта знаний ЕГЭ/ОГЭ — модели данных.

Иерархия:
  ExamType (ЕГЭ / ОГЭ)
    └── Subject (Математика, Русский язык, ...)
          └── Section (Алгебра, Геометрия, ...)
                └── Topic (Линейные уравнения, Треугольники, ...)

Прогресс ученика:
  StudentTopicMastery — многомерная оценка по каждой теме:
    - mastery_level (0-100): текущий уровень освоения
    - stability (0-100): стабильность результатов
    - trend: растёт / стабильно / падает
    - last_scores: последние N оценок (JSON)
    - total_attempts / successful_attempts: статистика
"""

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class ExamType(models.Model):
    """ЕГЭ или ОГЭ."""
    EXAM_CHOICES = [
        ('ege', 'ЕГЭ'),
        ('oge', 'ОГЭ'),
    ]

    code = models.CharField(max_length=10, unique=True, choices=EXAM_CHOICES)
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'Тип экзамена'
        verbose_name_plural = 'Типы экзаменов'
        ordering = ['code']

    def __str__(self):
        return self.name


class Subject(models.Model):
    """Предмет (привязан к типу экзамена)."""
    exam_type = models.ForeignKey(
        ExamType, on_delete=models.CASCADE, related_name='subjects'
    )
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, blank=True, default='')
    color = models.CharField(max_length=7, blank=True, default='#6366f1')
    max_primary_score = models.PositiveIntegerField(default=0)
    total_tasks = models.PositiveIntegerField(default=0)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Предмет'
        verbose_name_plural = 'Предметы'
        ordering = ['order', 'name']
        unique_together = ['exam_type', 'code']

    def __str__(self):
        return f'{self.exam_type.name} — {self.name}'


class Section(models.Model):
    """Раздел кодификатора (крупный блок тем)."""
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name='sections'
    )
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Раздел'
        verbose_name_plural = 'Разделы'
        ordering = ['order', 'code']
        unique_together = ['subject', 'code']

    def __str__(self):
        return f'{self.subject.name} — {self.name}'


class Topic(models.Model):
    """Конкретная тема / задание экзамена."""
    DIFFICULTY_CHOICES = [
        ('base', 'Базовый'),
        ('medium', 'Повышенный'),
        ('high', 'Высокий'),
    ]

    section = models.ForeignKey(
        Section, on_delete=models.CASCADE, related_name='topics'
    )
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=300)
    description = models.TextField(blank=True, default='')

    task_number = models.PositiveIntegerField(
        null=True, blank=True,
        help_text='Номер задания в КИМ (1-27 для ЕГЭ мат.профиль и т.д.)'
    )
    max_score = models.PositiveIntegerField(
        default=1,
        help_text='Максимальный балл за задание'
    )
    difficulty = models.CharField(
        max_length=10, choices=DIFFICULTY_CHOICES, default='base'
    )

    fipi_code = models.CharField(
        max_length=50, blank=True, default='',
        help_text='Код из кодификатора ФИПИ'
    )
    keywords = models.JSONField(
        default=list, blank=True,
        help_text='Ключевые слова для поиска/автоматической привязки'
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Тема'
        verbose_name_plural = 'Темы'
        ordering = ['order', 'code']
        unique_together = ['section', 'code']

    def __str__(self):
        prefix = f'Задание {self.task_number}' if self.task_number else self.code
        return f'{prefix}: {self.name}'


class StudentExamAssignment(models.Model):
    """
    Привязка ученика к типу экзамена и предмету.
    Ученик сдаёт ОГЭ ИЛИ ЕГЭ по конкретным предметам.
    """
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='exam_assignments'
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name='student_assignments'
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='assigned_exams'
    )

    class Meta:
        verbose_name = 'Назначение экзамена ученику'
        verbose_name_plural = 'Назначения экзаменов ученикам'
        unique_together = ['student', 'subject']

    def __str__(self):
        return f'{self.student} → {self.subject}'


class StudentTopicMastery(models.Model):
    """
    Многомерный прогресс ученика по конкретной теме.

    Система оценки:
    - mastery_level: взвешенная оценка (0-100), учитывает давность
    - stability: стабильность результатов (низкий разброс = высокая)
    - trend: направление прогресса
    - attempted_count: сколько раз пытался
    - success_count: сколько раз выше порога (70%)
    - last_scores: JSON массив последних 10 оценок [{score, max_score, date, hw_id}]
    """
    TREND_CHOICES = [
        ('rising', 'Растёт'),
        ('stable', 'Стабильно'),
        ('falling', 'Падает'),
        ('new', 'Мало данных'),
    ]

    MASTERY_STATUS_CHOICES = [
        ('not_started', 'Не начато'),
        ('learning', 'Изучается'),
        ('practiced', 'Отработано'),
        ('mastered', 'Освоено'),
        ('needs_review', 'Требует повторения'),
    ]

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='topic_mastery'
    )
    topic = models.ForeignKey(
        Topic, on_delete=models.CASCADE, related_name='student_mastery'
    )

    mastery_level = models.FloatField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text='Уровень освоения (0-100), взвешенный по давности'
    )
    stability = models.FloatField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text='Стабильность результатов (100 = всегда одинаково хорошо)'
    )
    trend = models.CharField(
        max_length=10, choices=TREND_CHOICES, default='new'
    )
    status = models.CharField(
        max_length=20, choices=MASTERY_STATUS_CHOICES, default='not_started'
    )

    attempted_count = models.PositiveIntegerField(default=0)
    success_count = models.PositiveIntegerField(default=0)
    total_score_earned = models.FloatField(default=0)
    total_score_possible = models.FloatField(default=0)
    avg_time_seconds = models.PositiveIntegerField(
        default=0, help_text='Среднее время на задание (сек)'
    )

    last_scores = models.JSONField(
        default=list, blank=True,
        help_text='Последние 10 результатов: [{score, max_score, date, homework_id}]'
    )

    first_attempt_at = models.DateTimeField(null=True, blank=True)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Прогресс по теме'
        verbose_name_plural = 'Прогресс по темам'
        unique_together = ['student', 'topic']
        indexes = [
            models.Index(fields=['student', 'topic']),
            models.Index(fields=['student', 'mastery_level']),
        ]

    def __str__(self):
        return f'{self.student} — {self.topic}: {self.mastery_level:.0f}%'

    @property
    def success_rate(self):
        if self.attempted_count == 0:
            return 0
        return round(self.success_count / self.attempted_count * 100, 1)

    @property
    def avg_score_percent(self):
        if self.total_score_possible == 0:
            return 0
        return round(self.total_score_earned / self.total_score_possible * 100, 1)

    def record_attempt(self, score, max_score, homework_id=None, time_seconds=0):
        """
        Записать новую попытку и пересчитать все метрики.
        Вызывается из сигнала при оценке ДЗ.
        """
        from django.utils import timezone

        now = timezone.now()

        self.attempted_count += 1
        self.total_score_earned += score
        self.total_score_possible += max_score

        percent = (score / max_score * 100) if max_score > 0 else 0
        if percent >= 70:
            self.success_count += 1

        if not self.first_attempt_at:
            self.first_attempt_at = now
        self.last_attempt_at = now

        if time_seconds > 0:
            if self.avg_time_seconds == 0:
                self.avg_time_seconds = time_seconds
            else:
                self.avg_time_seconds = int(
                    (self.avg_time_seconds * (self.attempted_count - 1) + time_seconds)
                    / self.attempted_count
                )

        entry = {
            'score': score,
            'max_score': max_score,
            'percent': round(percent, 1),
            'date': now.isoformat(),
            'homework_id': homework_id,
        }
        scores = self.last_scores or []
        scores.append(entry)
        self.last_scores = scores[-10:]

        self._recalculate_mastery()
        self._recalculate_stability()
        self._recalculate_trend()
        self._recalculate_status()

        self.save()

    def _recalculate_mastery(self):
        """Mastery = взвешенное среднее (экспоненциальное затухание)."""
        scores = self.last_scores or []
        if not scores:
            self.mastery_level = 0
            return

        decay = 0.85
        weights = []
        values = []
        for i, entry in enumerate(scores):
            weight = decay ** (len(scores) - 1 - i)
            weights.append(weight)
            values.append(entry.get('percent', 0))

        total_weight = sum(weights)
        if total_weight == 0:
            self.mastery_level = 0
            return

        weighted_avg = sum(v * w for v, w in zip(values, weights)) / total_weight
        self.mastery_level = round(min(100, max(0, weighted_avg)), 1)

    def _recalculate_stability(self):
        """Stability = 100 - stdev*2 последних оценок."""
        import statistics as stats

        scores = self.last_scores or []
        if len(scores) < 2:
            self.stability = 50
            return

        percents = [e.get('percent', 0) for e in scores]
        try:
            stdev = stats.stdev(percents)
        except stats.StatisticsError:
            stdev = 0

        self.stability = round(max(0, min(100, 100 - stdev * 2)), 1)

    def _recalculate_trend(self):
        """Trend по последним 3-5 попыткам (линейная регрессия)."""
        scores = self.last_scores or []
        if len(scores) < 3:
            self.trend = 'new'
            return

        recent = scores[-5:]
        percents = [e.get('percent', 0) for e in recent]

        n = len(percents)
        x_mean = (n - 1) / 2
        y_mean = sum(percents) / n
        numerator = sum((i - x_mean) * (p - y_mean) for i, p in enumerate(percents))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            self.trend = 'stable'
            return

        slope = numerator / denominator

        if slope > 3:
            self.trend = 'rising'
        elif slope < -3:
            self.trend = 'falling'
        else:
            self.trend = 'stable'

    def _recalculate_status(self):
        """Status на основе mastery + stability + attempted_count."""
        if self.attempted_count == 0:
            self.status = 'not_started'
        elif self.attempted_count < 3:
            self.status = 'learning'
        elif self.mastery_level >= 80 and self.stability >= 60:
            self.status = 'mastered'
        elif self.mastery_level >= 50:
            self.status = 'practiced'
        elif self.trend == 'falling' and self.attempted_count >= 3:
            self.status = 'needs_review'
        else:
            self.status = 'learning'
