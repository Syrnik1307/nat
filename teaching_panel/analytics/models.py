from django.db import models
from django.conf import settings
from schedule.models import Lesson, Group


class ControlPoint(models.Model):
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='control_points', limit_choices_to={'role': 'teacher'})
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='control_points')
    lesson = models.ForeignKey(Lesson, on_delete=models.SET_NULL, null=True, blank=True, related_name='control_points')
    title = models.CharField(max_length=255)
    max_points = models.IntegerField(default=100)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        verbose_name = 'контрольная точка'
        verbose_name_plural = 'контрольные точки'

    def __str__(self):
        return f"{self.title} ({self.group.name})"

class ControlPointResult(models.Model):
    control_point = models.ForeignKey(ControlPoint, on_delete=models.CASCADE, related_name='results')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='control_point_results', limit_choices_to={'role': 'student'})
    points = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['control_point', 'student']
        verbose_name = 'результат контрольной точки'
        verbose_name_plural = 'результаты контрольных точек'

    def __str__(self):
        return f"{self.student.email} -> {self.control_point.title}: {self.points}"


class StudentAIReport(models.Model):
    """AI-анализ ошибок и прогресса студента"""
    
    REPORT_STATUS = (
        ('pending', 'Ожидает генерации'),
        ('generating', 'Генерируется'),
        ('completed', 'Готов'),
        ('failed', 'Ошибка'),
    )
    
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='ai_reports',
        limit_choices_to={'role': 'student'}
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='student_ai_reports',
        limit_choices_to={'role': 'teacher'}
    )
    group = models.ForeignKey(
        Group, 
        on_delete=models.CASCADE, 
        related_name='ai_reports',
        null=True, 
        blank=True
    )
    
    status = models.CharField(max_length=20, choices=REPORT_STATUS, default='pending')
    
    # Период анализа
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    
    # Статистика (кэшированная)
    total_submissions = models.IntegerField(default=0)
    avg_score_percent = models.FloatField(null=True, blank=True)
    total_questions_answered = models.IntegerField(default=0)
    questions_needing_review = models.IntegerField(default=0)
    
    # AI-генерированный анализ (JSON)
    ai_analysis = models.JSONField(default=dict, blank=True, help_text='''
    {
        "strengths": ["Сильная сторона 1", "Сильная сторона 2"],
        "weaknesses": ["Слабая сторона 1", "Слабая сторона 2"],
        "common_mistakes": [
            {"topic": "Present Perfect", "frequency": 5, "examples": ["..."]},
        ],
        "recommendations": ["Рекомендация 1", "Рекомендация 2"],
        "progress_trend": "improving|stable|declining",
        "summary": "Краткое резюме о прогрессе студента..."
    }
    ''')
    
    # AI метаданные
    ai_provider = models.CharField(max_length=20, default='deepseek')
    ai_confidence = models.FloatField(null=True, blank=True)
    ai_tokens_used = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'AI-отчет по студенту'
        verbose_name_plural = 'AI-отчеты по студентам'
        # Один отчёт на студента на период
        unique_together = ['student', 'teacher', 'period_start', 'period_end']
    
    def __str__(self):
        return f"AI Report: {self.student.email} ({self.created_at.strftime('%Y-%m-%d')})"


class StudentBehaviorReport(models.Model):
    """
    AI-анализ поведения студента:
    - Посещаемость и опоздания
    - Сдача ДЗ (вовремя/с опозданием/не сдано)
    - Динамика оценок
    - Риск ухода
    """
    
    REPORT_STATUS = (
        ('pending', 'Ожидает генерации'),
        ('generating', 'Генерируется'),
        ('completed', 'Готов'),
        ('failed', 'Ошибка'),
    )
    
    RISK_LEVELS = (
        ('low', '🟢 Низкий'),
        ('medium', '🟡 Средний'),
        ('high', '🔴 Высокий'),
    )
    
    TREND_CHOICES = (
        ('improving', '📈 Улучшается'),
        ('stable', '➡️ Стабильно'),
        ('declining', '📉 Ухудшается'),
    )
    
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='behavior_reports',
        limit_choices_to={'role': 'student'}
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='student_behavior_reports',
        limit_choices_to={'role': 'teacher'}
    )
    group = models.ForeignKey(
        Group, 
        on_delete=models.CASCADE, 
        related_name='behavior_reports',
        null=True, 
        blank=True
    )
    
    status = models.CharField(max_length=20, choices=REPORT_STATUS, default='pending')
    
    # Период анализа
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    
    # ===== Собранные метрики (кэшированные) =====
    
    # Посещаемость
    total_lessons = models.IntegerField(default=0, help_text='Всего занятий за период')
    attended_lessons = models.IntegerField(default=0, help_text='Посещено занятий')
    missed_lessons = models.IntegerField(default=0, help_text='Пропущено занятий')
    late_arrivals = models.IntegerField(default=0, help_text='Опоздания на занятия')
    attendance_rate = models.FloatField(null=True, blank=True, help_text='Процент посещаемости')
    
    # Домашние задания
    total_homework = models.IntegerField(default=0, help_text='Всего ДЗ за период')
    submitted_on_time = models.IntegerField(default=0, help_text='Сдано вовремя')
    submitted_late = models.IntegerField(default=0, help_text='Сдано с опозданием')
    not_submitted = models.IntegerField(default=0, help_text='Не сдано')
    homework_rate = models.FloatField(null=True, blank=True, help_text='Процент сданных ДЗ')
    
    # Оценки
    avg_score = models.FloatField(null=True, blank=True, help_text='Средний балл')
    score_trend = models.CharField(max_length=20, choices=TREND_CHOICES, null=True, blank=True)
    control_points_count = models.IntegerField(default=0, help_text='Контрольных точек')
    control_points_avg = models.FloatField(null=True, blank=True, help_text='Средний балл контрольных')
    
    # ===== AI-генерированный анализ =====
    
    risk_level = models.CharField(max_length=10, choices=RISK_LEVELS, null=True, blank=True)
    reliability_score = models.IntegerField(null=True, blank=True, help_text='Балл надёжности 0-100')
    
    ai_analysis = models.JSONField(default=dict, blank=True, help_text='''
    {
        "profile_type": "responsible|needs_attention|at_risk",
        "strengths": ["Регулярно посещает занятия", ...],
        "concerns": ["Часто опаздывает", "Не сдаёт ДЗ вовремя", ...],
        "patterns": [
            {"type": "attendance", "description": "Пропускает занятия по понедельникам"},
            {"type": "homework", "description": "Сдаёт ДЗ в последний момент"}
        ],
        "recommendations": [
            {"priority": "high", "action": "Связаться с учеником по поводу пропусков"},
            {"priority": "medium", "action": "Предложить записи пропущенных занятий"}
        ],
        "alerts": [
            {"type": "warning", "message": "Пропустил 3 занятия подряд"}
        ],
        "predicted_completion_probability": 75,
        "summary": "Краткое резюме о поведении ученика..."
    }
    ''')
    
    # AI метаданные
    ai_provider = models.CharField(max_length=20, default='deepseek')
    ai_confidence = models.FloatField(null=True, blank=True)
    ai_tokens_used = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Поведенческий AI-отчёт'
        verbose_name_plural = 'Поведенческие AI-отчёты'
        unique_together = ['student', 'teacher', 'group', 'period_start', 'period_end']
    
    def __str__(self):
        return f"Behavior: {self.student.email} ({self.get_risk_level_display() or 'N/A'})"