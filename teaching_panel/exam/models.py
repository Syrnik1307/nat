"""
Модуль симуляции экзаменов ЕГЭ/ОГЭ.

Архитектура:
  ExamBlueprint — шаблон экзамена (структура: какие задания, сколько баллов, время)
    └── ExamTaskSlot — спецификация слота задания (номер, тип ответа, баллы)
  
  ExamTask — задание из банка (привязано к слоту через blueprint + task_number)
  
  ExamVariant — сгенерированный вариант (набор конкретных ExamTask)
    └── ExamVariantTask — привязка задания к варианту
  
  ExamAttempt — попытка ученика (расширяет StudentSubmission таймером и баллами)

Связи с существующими модулями:
  - ExamBlueprint.subject → knowledge_map.Subject (ЕГЭ Информатика, ОГЭ Математика...)
  - ExamTask.question → homework.Question (переиспользует существующие типы вопросов)
  - ExamVariant.homework → homework.Homework (вариант создаёт обычное ДЗ)
  - ExamAttempt.submission → homework.StudentSubmission (расширяет попытку таймером)
"""

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class ExamBlueprint(models.Model):
    """
    Шаблон структуры экзамена.
    
    Определяет:
    - Какой экзамен (ЕГЭ/ОГЭ, предмет, год)
    - Сколько заданий и какого типа
    - Длительность
    - Шкала перевода баллов (первичные → тестовые)
    
    Примеры:
    - "ЕГЭ Информатика 2026" — 27 заданий, 235 минут, макс 29 первичных
    - "ОГЭ Математика 2026" — 25 заданий, 235 минут, макс 32 первичных
    """
    
    subject = models.ForeignKey(
        'knowledge_map.Subject',
        on_delete=models.PROTECT,
        related_name='exam_blueprints',
        help_text='Предмет (ЕГЭ Информатика, ОГЭ Математика...)'
    )
    
    title = models.CharField(
        max_length=255,
        help_text='Название: "ЕГЭ Информатика 2026"'
    )
    year = models.PositiveIntegerField(
        default=2026,
        validators=[MinValueValidator(2020), MaxValueValidator(2035)],
        help_text='Год экзамена (для привязки шкалы ФИПИ)'
    )
    
    duration_minutes = models.PositiveIntegerField(
        default=235,
        help_text='Длительность экзамена в минутах'
    )
    total_primary_score = models.PositiveIntegerField(
        default=0,
        help_text='Максимальный первичный балл (сумма баллов всех заданий)'
    )
    
    # Шкала перевода первичных → тестовые (по ФИПИ)
    # Формат: {"0": 0, "1": 7, "2": 14, ..., "29": 100}
    score_scale = models.JSONField(
        default=dict, blank=True,
        help_text='Таблица перевода: {"первичный_балл": тестовый_балл, ...}'
    )
    
    # Пороги оценок (если нужно)
    # Формат: {"2": 0, "3": 40, "4": 57, "5": 72} — минимальный тестовый балл для оценки
    grade_thresholds = models.JSONField(
        default=dict, blank=True,
        help_text='Пороги оценок: {"оценка": мин_тестовый_балл, ...}'
    )
    
    description = models.TextField(
        blank=True, default='',
        help_text='Описание / инструкции к экзамену'
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text='Активен ли шаблон (неактивные скрыты в UI)'
    )
    is_public = models.BooleanField(
        default=False,
        help_text='Доступен ли всем учителям платформы (иначе только автору)'
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_blueprints',
        help_text='Автор шаблона'
    )
    school = models.ForeignKey(
        'tenants.School',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='exam_blueprints',
        help_text='Школа (multi-tenant)'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Шаблон экзамена'
        verbose_name_plural = 'Шаблоны экзаменов'
        ordering = ['-year', 'subject__name']
        indexes = [
            models.Index(fields=['subject', 'year'], name='exam_bp_subject_year_idx'),
            models.Index(fields=['is_active'], name='exam_bp_active_idx'),
        ]

    def __str__(self):
        return self.title

    def recalculate_total_score(self):
        """Пересчитать total_primary_score из суммы слотов."""
        total = self.task_slots.aggregate(
            total=models.Sum('max_points')
        )['total'] or 0
        self.total_primary_score = total
        self.save(update_fields=['total_primary_score'])
        return total

    def convert_to_test_score(self, primary_score: int):
        """Конвертировать первичный балл → тестовый по шкале ФИПИ."""
        if not self.score_scale:
            return None
        # Ищем точное совпадение
        key = str(primary_score)
        if key in self.score_scale:
            return self.score_scale[key]
        # Интерполяция между ближайшими точками
        points = sorted([(int(k), v) for k, v in self.score_scale.items()])
        if not points:
            return None
        if primary_score <= points[0][0]:
            return points[0][1]
        if primary_score >= points[-1][0]:
            return points[-1][1]
        for i in range(len(points) - 1):
            lo_p, lo_t = points[i]
            hi_p, hi_t = points[i + 1]
            if lo_p <= primary_score <= hi_p:
                ratio = (primary_score - lo_p) / (hi_p - lo_p) if hi_p != lo_p else 0
                return round(lo_t + ratio * (hi_t - lo_t))
        return None


class ExamTaskSlot(models.Model):
    """
    Спецификация одного слота (номера задания) в шаблоне экзамена.
    
    Определяет:
    - Номер задания в КИМ (1, 2, ... 27)
    - Тип ответа (краткий числовой, последовательность, развёрнутый...)
    - Максимальный балл
    - Связь с темой knowledge_map (для аналитики)
    """
    
    ANSWER_TYPE_CHOICES = [
        # Краткие ответы (часть 1)
        ('short_number', 'Краткий числовой ответ'),
        ('short_text', 'Краткий текстовый ответ'),
        ('digit_sequence', 'Последовательность цифр'),
        ('letter_sequence', 'Последовательность букв (АБВГД)'),
        ('decimal_number', 'Десятичная дробь'),
        ('number_range', 'Диапазон чисел (через дефис)'),
        ('multiple_numbers', 'Несколько чисел через пробел'),
        
        # Структурированные ответы
        ('matching', 'Соответствие (таблица)'),
        ('ordered_sequence', 'Упорядоченная последовательность'),
        ('single_choice', 'Один вариант ответа'),
        ('multi_choice', 'Несколько вариантов ответа'),
        
        # Развёрнутые ответы (часть 2)
        ('extended_text', 'Развёрнутый текстовый ответ'),
        ('essay', 'Сочинение / эссе'),
        ('math_solution', 'Математическое решение'),
        ('code_solution', 'Программный код (в редакторе)'),
        ('code_file', 'Файл с программой'),
    ]

    blueprint = models.ForeignKey(
        ExamBlueprint,
        on_delete=models.CASCADE,
        related_name='task_slots',
        help_text='Шаблон экзамена'
    )
    task_number = models.PositiveIntegerField(
        help_text='Номер задания в КИМ (1-27 и т.д.)'
    )
    
    title = models.CharField(
        max_length=255, blank=True, default='',
        help_text='Краткое описание типа задания: "Анализ информационных моделей"'
    )
    
    answer_type = models.CharField(
        max_length=30,
        choices=ANSWER_TYPE_CHOICES,
        default='short_number',
        help_text='Формат ожидаемого ответа'
    )
    max_points = models.PositiveIntegerField(
        default=1,
        help_text='Максимальный балл за задание'
    )
    
    # Связь с knowledge_map для аналитики
    topic = models.ForeignKey(
        'knowledge_map.Topic',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='exam_task_slots',
        help_text='Тема из карты знаний (для аналитики слабых мест)'
    )
    
    # Дополнительные настройки формата ответа
    answer_config = models.JSONField(
        default=dict, blank=True,
        help_text='Параметры формата ответа (зависит от answer_type)'
    )
    
    description = models.TextField(
        blank=True, default='',
        help_text='Описание типа задания (видно учителю при создании банка)'
    )
    
    order = models.PositiveIntegerField(
        default=0,
        help_text='Порядок отображения (обычно = task_number)'
    )

    class Meta:
        verbose_name = 'Слот задания'
        verbose_name_plural = 'Слоты заданий'
        ordering = ['task_number']
        unique_together = ['blueprint', 'task_number']

    def __str__(self):
        return f"Задание {self.task_number}: {self.title or self.get_answer_type_display()}"


class ExamTask(models.Model):
    """
    Конкретное задание в банке заданий.
    
    Привязано к blueprint + task_number (т.е. к слоту).
    Содержит текст задания, правильный ответ и метаданные.
    """
    
    DIFFICULTY_CHOICES = [
        ('easy', 'Лёгкое'),
        ('medium', 'Среднее'),
        ('hard', 'Сложное'),
    ]
    
    SOURCE_CHOICES = [
        ('fipi', 'ФИПИ (официальный банк)'),
        ('reshu_ege', 'Решу ЕГЭ / Решу ОГЭ'),
        ('author', 'Авторское задание'),
        ('textbook', 'Учебник'),
        ('olympiad', 'Олимпиадное'),
        ('other', 'Другой источник'),
    ]
    
    blueprint = models.ForeignKey(
        ExamBlueprint,
        on_delete=models.CASCADE,
        related_name='tasks',
        help_text='Шаблон экзамена'
    )
    task_number = models.PositiveIntegerField(
        help_text='Номер задания в КИМ (к какому слоту относится)'
    )
    
    # Переиспользуем Question для хранения текста и config
    question = models.OneToOneField(
        'homework.Question',
        on_delete=models.CASCADE,
        related_name='exam_task',
        help_text='Вопрос с текстом, config и вариантами ответа'
    )
    
    difficulty = models.CharField(
        max_length=10,
        choices=DIFFICULTY_CHOICES,
        default='medium',
    )
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default='author',
    )
    source_reference = models.CharField(
        max_length=255, blank=True, default='',
        help_text='Номер в банке ФИПИ / ссылка на источник'
    )
    
    tags = models.JSONField(
        default=list, blank=True,
        help_text='Теги для фильтрации: ["рекурсия", "сортировка", ...]'
    )
    
    usage_count = models.PositiveIntegerField(
        default=0,
        help_text='Сколько раз использовано в вариантах'
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text='Активно (неактивные не выбираются при генерации)'
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_exam_tasks',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Задание банка'
        verbose_name_plural = 'Задания банка'
        ordering = ['task_number', '-created_at']
        indexes = [
            models.Index(fields=['blueprint', 'task_number'], name='exam_task_bp_num_idx'),
            models.Index(fields=['difficulty'], name='exam_task_diff_idx'),
            models.Index(fields=['is_active'], name='exam_task_active_idx'),
        ]

    def __str__(self):
        return f"Банк #{self.id}: задание {self.task_number} ({self.get_difficulty_display()})"


class ExamVariant(models.Model):
    """
    Сгенерированный вариант экзамена.
    
    При назначении группе создаёт обычный Homework,
    чтобы переиспользовать всю систему проверки.
    """
    
    blueprint = models.ForeignKey(
        ExamBlueprint,
        on_delete=models.CASCADE,
        related_name='variants',
    )
    
    homework = models.OneToOneField(
        'homework.Homework',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='exam_variant',
        help_text='Связанное ДЗ (создаётся при назначении)'
    )
    
    variant_number = models.PositiveIntegerField(
        default=1,
        help_text='Номер варианта'
    )
    title = models.CharField(
        max_length=255, blank=True, default='',
        help_text='Название варианта: "Вариант 1"'
    )
    
    is_manual = models.BooleanField(
        default=False,
        help_text='Собран вручную (True) или сгенерирован (False)'
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_variants',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Вариант экзамена'
        verbose_name_plural = 'Варианты экзаменов'
        ordering = ['variant_number']
        unique_together = ['blueprint', 'variant_number']

    def __str__(self):
        return f"{self.blueprint.title} — Вариант {self.variant_number}"

    @property
    def task_count(self):
        return self.variant_tasks.count()


class ExamVariantTask(models.Model):
    """
    Привязка конкретного задания к варианту.
    """
    
    variant = models.ForeignKey(
        ExamVariant,
        on_delete=models.CASCADE,
        related_name='variant_tasks',
    )
    task = models.ForeignKey(
        ExamTask,
        on_delete=models.CASCADE,
        related_name='variant_usages',
    )
    task_number = models.PositiveIntegerField(
        help_text='Номер задания в варианте'
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Задание в варианте'
        verbose_name_plural = 'Задания в вариантах'
        ordering = ['task_number']
        unique_together = ['variant', 'task_number']

    def __str__(self):
        return f"Вариант {self.variant.variant_number}, задание {self.task_number}"


class ExamAttempt(models.Model):
    """
    Попытка прохождения экзамена учеником.
    Расширяет StudentSubmission таймером и баллами.
    """
    
    submission = models.OneToOneField(
        'homework.StudentSubmission',
        on_delete=models.CASCADE,
        related_name='exam_attempt',
    )
    variant = models.ForeignKey(
        ExamVariant,
        on_delete=models.CASCADE,
        related_name='attempts',
    )
    
    # Таймер
    started_at = models.DateTimeField(
        null=True, blank=True,
        help_text='Когда ученик начал экзамен'
    )
    deadline_at = models.DateTimeField(
        null=True, blank=True,
        help_text='Дедлайн = started_at + duration_minutes'
    )
    auto_submitted = models.BooleanField(
        default=False,
        help_text='Сдан автоматически по таймеру'
    )
    
    # Баллы
    primary_score = models.PositiveIntegerField(null=True, blank=True)
    test_score = models.PositiveIntegerField(null=True, blank=True)
    grade = models.CharField(max_length=5, blank=True, default='')
    
    # Детальные результаты по заданиям
    # [{"task_number": 1, "score": 1, "max": 1, "answer_type": "short_number"}, ...]
    task_scores = models.JSONField(default=list, blank=True)
    
    # Аналитика
    time_spent_seconds = models.PositiveIntegerField(null=True, blank=True)
    fullscreen_exits = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Попытка экзамена'
        verbose_name_plural = 'Попытки экзаменов'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['variant', 'started_at'], name='exam_att_variant_idx'),
            models.Index(fields=['deadline_at'], name='exam_att_deadline_idx'),
        ]

    def __str__(self):
        student = self.submission.student.email if self.submission_id else '?'
        return f"{student}: {self.variant}"

    def calculate_scores(self):
        """Пересчитать первичный балл, тестовый балл и оценку."""
        self.submission.compute_auto_score()
        self.primary_score = self.submission.total_score or 0
        
        blueprint = self.variant.blueprint
        self.test_score = blueprint.convert_to_test_score(self.primary_score)
        
        if self.test_score is not None and blueprint.grade_thresholds:
            thresholds = sorted(
                [(int(grade), min_score) for grade, min_score in blueprint.grade_thresholds.items()],
                key=lambda x: x[1],
                reverse=True
            )
            self.grade = ''
            for grade_val, min_score in thresholds:
                if self.test_score >= min_score:
                    self.grade = str(grade_val)
                    break
        
        self._fill_task_scores()
        
        self.save(update_fields=[
            'primary_score', 'test_score', 'grade', 'task_scores'
        ])
        return self.primary_score, self.test_score, self.grade

    def _fill_task_scores(self):
        """Заполнить task_scores из ответов ученика."""
        from homework.models import Answer
        
        task_scores = []
        variant_tasks = self.variant.variant_tasks.select_related(
            'task', 'task__question'
        ).order_by('task_number')
        
        for vt in variant_tasks:
            question = vt.task.question
            try:
                answer = Answer.objects.get(
                    submission=self.submission,
                    question=question
                )
                score = answer.teacher_score if answer.teacher_score is not None else (answer.auto_score or 0)
            except Answer.DoesNotExist:
                score = 0
            
            slot = ExamTaskSlot.objects.filter(
                blueprint=self.variant.blueprint,
                task_number=vt.task_number
            ).first()
            
            task_scores.append({
                'task_number': vt.task_number,
                'score': score,
                'max': question.points,
                'answer_type': slot.answer_type if slot else 'short_number',
            })
        
        self.task_scores = task_scores
