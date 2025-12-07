from django.db import models
from django.conf import settings
from schedule.models import Lesson


class Homework(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Черновик'),
        ('published', 'Опубликовано'),
        ('archived', 'Архивировано'),
    )
    
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='homeworks', limit_choices_to={'role': 'teacher'})
    lesson = models.ForeignKey(Lesson, on_delete=models.SET_NULL, null=True, blank=True, related_name='homeworks')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
    )
    homework = models.ForeignKey(Homework, on_delete=models.CASCADE, related_name='questions')
    prompt = models.TextField()
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

    class Meta:
        verbose_name = 'ответ'
        verbose_name_plural = 'ответы'

    def __str__(self):
        return f"Answer q{self.question.id} by submission {self.submission.id}"

    def evaluate(self):
        """Автоматическая оценка ответа на основе типа вопроса и config."""
        q = self.question
        config = q.config or {}
        
        if q.question_type == 'TEXT':
            # Текстовые ответы требуют ручной проверки
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
        else:
            # Неизвестный тип
            self.needs_manual_review = True
            self.auto_score = None
            
        self.save()
        return self.auto_score
