from django.db import models
from django.conf import settings
from schedule.models import Lesson
from schedule.models import Group


class HomeworkGroupAssignment(models.Model):
    """
    Промежуточная модель для назначения ДЗ группе с опциональным ограничением 
    по конкретным ученикам внутри группы.
    
    Если students пустой - ДЗ видят все ученики группы.
    Если students заполнен - ДЗ видят только указанные ученики.
    """
    homework = models.ForeignKey(
        'Homework',
        on_delete=models.CASCADE,
        related_name='group_assignments'
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='homework_assignments'
    )
    # Если пусто - все ученики группы. Если заполнено - только выбранные.
    students = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='homework_group_assignments',
        limit_choices_to={'role': 'student'},
        help_text='Конкретные ученики в группе (если пусто - все ученики)'
    )
    # Дедлайн может быть разным для разных групп
    deadline = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Персональный дедлайн для этой группы (если отличается от общего)'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['homework', 'group']
        verbose_name = 'назначение ДЗ группе'
        verbose_name_plural = 'назначения ДЗ группам'
        ordering = ['-created_at']

    def __str__(self):
        student_count = self.students.count()
        if student_count:
            return f"{self.homework.title} -> {self.group.name} ({student_count} уч.)"
        return f"{self.homework.title} -> {self.group.name} (все)"

    def get_target_students(self):
        """Получить список учеников, которым назначено это ДЗ."""
        if self.students.exists():
            return self.students.all()
        return self.group.students.filter(is_active=True)


class Homework(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Черновик'),
        ('published', 'Опубликовано'),
        ('archived', 'Архивировано'),
    )
    
    AI_PROVIDER_CHOICES = (
        ('none', 'Без AI'),
        ('deepseek', 'DeepSeek'),
        ('openai', 'OpenAI'),
    )
    
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='homeworks', limit_choices_to={'role': 'teacher'})
    lesson = models.ForeignKey(Lesson, on_delete=models.SET_NULL, null=True, blank=True, related_name='homeworks')

    # Assignment targeting (independent from lesson)
    assigned_groups = models.ManyToManyField(
        Group,
        blank=True,
        related_name='homeworks',
        help_text='Группы, которым назначено ДЗ (без привязки к уроку)'
    )
    assigned_students = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='assigned_homeworks',
        limit_choices_to={'role': 'student'},
        help_text='Индивидуально назначенные ученики (показывать даже без группы)'
    )

    # Templates / archive
    is_template = models.BooleanField(
        default=False,
        help_text='Если true — это шаблон (архив) для переиспользования'
    )

    # Storage / structure on Google Drive
    gdrive_folder_id = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='ID папки Google Drive, где лежат материалы ДЗ/шаблона'
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    deadline = models.DateTimeField(null=True, blank=True, help_text='Крайний срок сдачи')
    max_score = models.IntegerField(default=100, help_text='Максимальный балл (UI/контрольная сумма)')
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # AI проверка
    ai_grading_enabled = models.BooleanField(default=False, help_text='Включить AI проверку текстовых ответов')
    ai_provider = models.CharField(max_length=20, choices=AI_PROVIDER_CHOICES, default='deepseek', help_text='Провайдер AI для проверки')
    ai_grading_prompt = models.TextField(blank=True, help_text='Дополнительные инструкции для AI при проверке (контекст темы, критерии оценки)')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'домашнее задание'
        verbose_name_plural = 'домашние задания'

    def __str__(self):
        return self.title


class Question(models.Model):
    QUESTION_TYPES = (
        ('TEXT', 'Текстовый ответ'),
        ('SINGLE_CHOICE', 'Один вариант'),
        ('MULTI_CHOICE', 'Несколько вариантов'),
        ('LISTENING', 'Лисенинг'),
        ('MATCHING', 'Сопоставление'),
        ('DRAG_DROP', 'Перетаскивание'),
        ('FILL_BLANKS', 'Заполнение пропусков'),
        ('HOTSPOT', 'Хотспот на изображении'),
        ('CODE', 'Программирование'),
    )
    homework = models.ForeignKey(Homework, on_delete=models.CASCADE, related_name='questions')
    prompt = models.TextField(blank=True, default='')  # blank allowed for image-only questions
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    points = models.IntegerField(default=1)
    order = models.IntegerField(default=0)
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['order']
        verbose_name = 'вопрос'
        verbose_name_plural = 'вопросы'

    def __str__(self):
        return f"Q{self.order}: {self.prompt[:40]}"


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'вариант ответа'
        verbose_name_plural = 'варианты ответов'

    def __str__(self):
        return self.text


class StudentSubmission(models.Model):
    STATUS_CHOICES = (
        ('in_progress', 'В процессе'),
        ('submitted', 'Отправлено'),
        ('graded', 'Проверено'),
    )
    homework = models.ForeignKey(Homework, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='homework_submissions', limit_choices_to={'role': 'student'})
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    total_score = models.IntegerField(null=True, blank=True)
    teacher_feedback_summary = models.JSONField(
        default=dict,
        blank=True,
        help_text='Общий комментарий учителя к работе: {"text": "...", "attachments": [...]}'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    graded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['homework', 'student']
        indexes = [
            models.Index(fields=['homework', 'status'], name='hw_status_idx'),
            models.Index(fields=['student', 'status'], name='student_status_idx'),
            models.Index(fields=['created_at'], name='submission_created_idx'),
        ]
        ordering = ['-created_at']
        verbose_name = 'попытка ученика'
        verbose_name_plural = 'попытки учеников'

    def __str__(self):
        return f"{self.student.email} -> {self.homework.title}"

    def compute_auto_score(self):
        total = 0
        for answer in self.answers.select_related('question').all():
            # Приоритет: teacher_score > auto_score
            if answer.teacher_score is not None:
                total += answer.teacher_score
            elif answer.auto_score is not None:
                total += answer.auto_score
        self.total_score = total
        self.save(update_fields=['total_score'])
        return total


class Answer(models.Model):
    submission = models.ForeignKey(StudentSubmission, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    text_answer = models.TextField(blank=True)
    selected_choices = models.ManyToManyField(Choice, blank=True, related_name='selected_in_answers')
    auto_score = models.IntegerField(null=True, blank=True)
    teacher_score = models.IntegerField(null=True, blank=True, help_text='Оценка учителя (переопределяет auto_score)')
    teacher_feedback = models.TextField(blank=True, help_text='Комментарий учителя')
    needs_manual_review = models.BooleanField(default=False)
    
    # === НОВЫЕ ПОЛЯ ДЛЯ АНАЛИТИКИ ===
    answered_at = models.DateTimeField(
        null=True, blank=True,
        help_text='Время ответа на вопрос (для анализа порядка и скорости)'
    )
    time_spent_seconds = models.IntegerField(
        null=True, blank=True,
        help_text='Время в секундах, затраченное на ответ'
    )
    started_at = models.DateTimeField(
        null=True, blank=True,
        help_text='Когда ученик начал отвечать на вопрос'
    )
    revision_count = models.IntegerField(
        default=0,
        help_text='Сколько раз ученик изменял ответ (самокоррекция)'
    )

    class Meta:
        verbose_name = 'ответ'
        verbose_name_plural = 'ответы'
        indexes = [
            models.Index(fields=['submission', 'answered_at'], name='answer_timing_idx'),
        ]

    def __str__(self):
        return f"Answer q{self.question.id} by submission {self.submission.id}"

    def evaluate(self, use_ai: bool = False):
        """Автоматическая оценка ответа на основе типа вопроса и config.
        
        Args:
            use_ai: Использовать AI для проверки TEXT вопросов
        """
        q = self.question
        config = q.config or {}
        homework = q.homework
        
        if q.question_type == 'TEXT':
            # Сначала проверяем, есть ли correctAnswer в config
            correct_answer = config.get('correctAnswer', '').strip()
            student_answer = (self.text_answer or '').strip()
            
            if correct_answer:
                # Есть эталонный ответ - сравниваем (регистронезависимо)
                if student_answer.lower() == correct_answer.lower():
                    self.auto_score = q.points
                    self.needs_manual_review = False
                else:
                    self.auto_score = 0
                    self.needs_manual_review = False
            elif use_ai and homework.ai_grading_enabled:
                # Нет эталонного ответа, но включена AI проверка
                self._evaluate_with_ai(homework)
            else:
                # Нет эталонного ответа и нет AI - ручная проверка
                self.needs_manual_review = True
                self.auto_score = None
            
        elif q.question_type == 'SINGLE_CHOICE':
            # Один правильный вариант
            chosen = self.selected_choices.first()
            correct_id = config.get('correctOptionId')
            if correct_id and chosen and str(chosen.id) == str(correct_id):
                self.auto_score = q.points
            else:
                # Fallback: проверяем по is_correct в Choice
                self.auto_score = q.points if (chosen and chosen.is_correct) else 0
                
        elif q.question_type == 'MULTI_CHOICE':
            # Множественный выбор
            chosen = list(self.selected_choices.all())
            correct_ids = config.get('correctOptionIds', [])
            
            if correct_ids:
                # Проверка по config
                chosen_ids = set(str(c.id) for c in chosen)
                correct_ids_set = set(str(cid) for cid in correct_ids)
                
                if chosen_ids == correct_ids_set:
                    self.auto_score = q.points
                else:
                    # Частичный балл
                    true_pos = len(chosen_ids & correct_ids_set)
                    false_pos = len(chosen_ids - correct_ids_set)
                    partial = max(0, true_pos - false_pos)
                    self.auto_score = int(q.points * (partial / len(correct_ids_set))) if correct_ids_set else 0
            else:
                # Fallback: по is_correct
                correct = list(q.choices.filter(is_correct=True))
                if not correct:
                    self.auto_score = 0
                else:
                    chosen_ids = set(c.id for c in chosen)
                    correct_ids_set = set(c.id for c in correct)
                    
                    if chosen_ids == correct_ids_set:
                        self.auto_score = q.points
                    else:
                        true_pos = len(chosen_ids & correct_ids_set)
                        false_pos = len(chosen_ids - correct_ids_set)
                        partial = max(0, true_pos - false_pos)
                        self.auto_score = int(q.points * (partial / len(correct_ids_set))) if correct_ids_set else 0
                        
        elif q.question_type == 'LISTENING':
            # Проверяем ответы на подвопросы
            sub_questions = config.get('subQuestions', [])
            if not sub_questions:
                self.needs_manual_review = True
                self.auto_score = None
            else:
                # Парсим text_answer как JSON (словарь {subQuestionId: answer})
                try:
                    import json
                    student_answers = json.loads(self.text_answer) if self.text_answer else {}
                except (json.JSONDecodeError, TypeError):
                    student_answers = {}
                
                correct_count = 0
                total_count = len(sub_questions)
                
                for subq in sub_questions:
                    subq_id = str(subq.get('id', ''))
                    correct_answer = subq.get('answer', '').strip().lower()
                    student_answer = student_answers.get(subq_id, '').strip().lower()
                    
                    if correct_answer and student_answer == correct_answer:
                        correct_count += 1
                
                if total_count > 0:
                    self.auto_score = int(q.points * (correct_count / total_count))
                else:
                    self.auto_score = 0
                    
        elif q.question_type == 'MATCHING':
            # Сопоставление пар
            pairs = config.get('pairs', [])
            if not pairs:
                self.needs_manual_review = True
                self.auto_score = None
            else:
                try:
                    import json
                    student_matches = json.loads(self.text_answer) if self.text_answer else {}
                except (json.JSONDecodeError, TypeError):
                    student_matches = {}
                
                correct_count = 0
                total_count = len(pairs)
                
                for pair in pairs:
                    pair_id = str(pair.get('id', ''))
                    correct_right = pair.get('right', '').strip()
                    student_right = student_matches.get(pair_id, '').strip()
                    
                    if correct_right and student_right == correct_right:
                        correct_count += 1
                
                if total_count > 0:
                    self.auto_score = int(q.points * (correct_count / total_count))
                else:
                    self.auto_score = 0
                    
        elif q.question_type == 'DRAG_DROP':
            # Перетаскивание для упорядочивания
            correct_order = config.get('correctOrder', [])
            if not correct_order:
                self.needs_manual_review = True
                self.auto_score = None
            else:
                try:
                    import json
                    student_order = json.loads(self.text_answer) if self.text_answer else []
                except (json.JSONDecodeError, TypeError):
                    student_order = []
                
                # Сравниваем списки ID
                correct_order_str = [str(x) for x in correct_order]
                student_order_str = [str(x) for x in student_order]
                
                if correct_order_str == student_order_str:
                    self.auto_score = q.points
                else:
                    # Частичный балл: считаем позиции которые совпадают
                    correct_positions = sum(1 for i, item in enumerate(student_order_str) 
                                           if i < len(correct_order_str) and item == correct_order_str[i])
                    total_positions = len(correct_order_str)
                    self.auto_score = int(q.points * (correct_positions / total_positions)) if total_positions > 0 else 0
                    
        elif q.question_type == 'FILL_BLANKS':
            # Заполнение пропусков
            correct_answers = config.get('answers', [])
            if not correct_answers:
                self.needs_manual_review = True
                self.auto_score = None
            else:
                try:
                    import json
                    student_answers = json.loads(self.text_answer) if self.text_answer else []
                except (json.JSONDecodeError, TypeError):
                    student_answers = []
                
                correct_count = 0
                total_count = len(correct_answers)
                
                for i, correct in enumerate(correct_answers):
                    if i < len(student_answers):
                        student = student_answers[i].strip().lower()
                        correct_normalized = correct.strip().lower()
                        if student == correct_normalized:
                            correct_count += 1
                
                if total_count > 0:
                    self.auto_score = int(q.points * (correct_count / total_count))
                else:
                    self.auto_score = 0
                    
        elif q.question_type == 'HOTSPOT':
            # Хотспот - выбор зон на изображении
            hotspots = config.get('hotspots', [])
            if not hotspots:
                self.needs_manual_review = True
                self.auto_score = None
            else:
                try:
                    import json
                    student_selections = json.loads(self.text_answer) if self.text_answer else []
                except (json.JSONDecodeError, TypeError):
                    student_selections = []
                
                # Определяем правильные хотспоты
                correct_hotspot_ids = set(str(h.get('id')) for h in hotspots if h.get('isCorrect'))
                student_hotspot_ids = set(str(x) for x in student_selections)
                
                if student_hotspot_ids == correct_hotspot_ids:
                    self.auto_score = q.points
                else:
                    # Частичный балл
                    if correct_hotspot_ids:
                        true_pos = len(student_hotspot_ids & correct_hotspot_ids)
                        false_pos = len(student_hotspot_ids - correct_hotspot_ids)
                        partial = max(0, true_pos - false_pos)
                        self.auto_score = int(q.points * (partial / len(correct_hotspot_ids)))
                    else:
                        self.auto_score = 0
                        
        elif q.question_type == 'CODE':
            # Программирование - результаты тестов передаются из браузера
            # config содержит: language, starterCode, testCases[{input, expectedOutput}]
            # text_answer содержит JSON: {code: "...", testResults: [{passed, input, expected, actual}]}
            test_cases = config.get('testCases', [])
            if not test_cases:
                # Нет тестов - требуется ручная проверка
                self.needs_manual_review = True
                self.auto_score = None
            else:
                try:
                    import json
                    answer_data = json.loads(self.text_answer) if self.text_answer else {}
                except (json.JSONDecodeError, TypeError):
                    answer_data = {}
                
                test_results = answer_data.get('testResults', [])
                
                if not test_results:
                    # Код не был запущен - 0 баллов
                    self.auto_score = 0
                else:
                    # Считаем пройденные тесты
                    passed_count = sum(1 for tr in test_results if tr.get('passed'))
                    total_count = len(test_cases)
                    
                    if total_count > 0:
                        self.auto_score = int(q.points * (passed_count / total_count))
                    else:
                        self.auto_score = 0
        else:
            # Неизвестный тип
            self.needs_manual_review = True
            self.auto_score = None
            
        self.save()
        return self.auto_score

    def _evaluate_with_ai(self, homework):
        """Проверка текстового ответа с помощью AI.
        
        Args:
            homework: Объект Homework с настройками AI
        """
        from .ai_grading_service import grade_text_answer
        
        q = self.question
        config = q.config or {}
        
        # Получаем эталонный ответ если есть
        correct_answer = config.get('correctAnswer', '')
        
        try:
            result = grade_text_answer(
                question_text=q.prompt,
                student_answer=self.text_answer,
                max_points=q.points,
                provider=homework.ai_provider or 'deepseek',
                correct_answer=correct_answer if correct_answer else None,
                teacher_context=homework.ai_grading_prompt if homework.ai_grading_prompt else None
            )
            
            if result.error:
                # AI не смог проверить - требуется ручная проверка
                self.needs_manual_review = True
                self.auto_score = None
                self.teacher_feedback = f"[AI ошибка: {result.error}] {result.feedback}"
            else:
                # AI успешно проверил
                self.auto_score = result.score
                self.teacher_feedback = f"[AI оценка, уверенность: {result.confidence:.0%}] {result.feedback}"
                # Если уверенность низкая - всё равно требуем ручную проверку
                self.needs_manual_review = result.confidence < 0.7
                
        except Exception as e:
            # При любой ошибке - ручная проверка
            import logging
            logger = logging.getLogger(__name__)
            logger.exception(f"AI grading failed for answer {self.id}")
            self.needs_manual_review = True
            self.auto_score = None
            self.teacher_feedback = f"[AI недоступен] Требуется ручная проверка"


# =============================================================================
# МОДЕЛИ ДЛЯ РАСШИРЕННОЙ АНАЛИТИКИ УЧЕНИКОВ
# =============================================================================

class AnswerVersion(models.Model):
    """
    Версия ответа для отслеживания самокоррекции.
    Каждое изменение ответа сохраняется как новая версия.
    """
    answer = models.ForeignKey(
        Answer,
        on_delete=models.CASCADE,
        related_name='versions',
        verbose_name='ответ'
    )
    version_number = models.PositiveIntegerField(
        default=1,
        help_text='Номер версии (1 = первый ответ)'
    )
    text_content = models.TextField(
        blank=True,
        help_text='Текст ответа на момент этой версии'
    )
    selected_choice_ids = models.JSONField(
        default=list,
        blank=True,
        help_text='ID выбранных вариантов на момент этой версии'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'версия ответа'
        verbose_name_plural = 'версии ответов'
        ordering = ['answer', 'version_number']
        unique_together = ('answer', 'version_number')
        indexes = [
            models.Index(fields=['answer', '-created_at'], name='answer_version_idx'),
        ]
    
    def __str__(self):
        return f"Answer {self.answer_id} v{self.version_number}"


class StudentQuestion(models.Model):
    """
    Вопрос от ученика (для анализа качества вопросов: "как?" vs "почему?").
    Может быть задан в чате, на уроке или через форму.
    """
    QUESTION_QUALITY_CHOICES = (
        ('procedural', 'Процедурный (как?)'),
        ('conceptual', 'Концептуальный (почему?)'),
        ('clarification', 'Уточнение'),
        ('off_topic', 'Не по теме'),
        ('unclassified', 'Не классифицирован'),
    )
    
    SOURCE_CHOICES = (
        ('chat', 'Чат группы'),
        ('lesson', 'На уроке'),
        ('homework', 'В домашнем задании'),
        ('direct', 'Личное сообщение'),
    )
    
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='asked_questions',
        limit_choices_to={'role': 'student'},
        verbose_name='ученик'
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_questions',
        limit_choices_to={'role': 'teacher'},
        verbose_name='учитель'
    )
    group = models.ForeignKey(
        'schedule.Group',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_questions',
        verbose_name='группа'
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_questions',
        verbose_name='урок'
    )
    
    question_text = models.TextField(verbose_name='текст вопроса')
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default='chat',
        verbose_name='источник'
    )
    quality = models.CharField(
        max_length=20,
        choices=QUESTION_QUALITY_CHOICES,
        default='unclassified',
        verbose_name='качество вопроса'
    )
    
    # AI-анализ вопроса
    ai_quality_score = models.FloatField(
        null=True,
        blank=True,
        help_text='AI оценка качества вопроса 0-1'
    )
    ai_classification = models.JSONField(
        default=dict,
        blank=True,
        help_text='AI классификация: {"type": "...", "confidence": 0.9, "topics": [...]}'
    )
    
    is_answered = models.BooleanField(default=False)
    answer_text = models.TextField(blank=True)
    answered_at = models.DateTimeField(null=True, blank=True)
    answered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='answered_student_questions',
        verbose_name='ответил'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'вопрос ученика'
        verbose_name_plural = 'вопросы учеников'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['student', '-created_at'], name='student_questions_idx'),
            models.Index(fields=['quality', 'created_at'], name='question_quality_idx'),
        ]
    
    def __str__(self):
        return f"{self.student.get_full_name()}: {self.question_text[:50]}..."

