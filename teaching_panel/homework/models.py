from django.db import models
from django.conf import settings
from schedule.models import Lesson


class Homework(models.Model):
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='homeworks', limit_choices_to={'role': 'teacher'})
    lesson = models.ForeignKey(Lesson, on_delete=models.SET_NULL, null=True, blank=True, related_name='homeworks')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
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
    )
    homework = models.ForeignKey(Homework, on_delete=models.CASCADE, related_name='questions')
    prompt = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    points = models.IntegerField(default=1)
    order = models.IntegerField(default=0)

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
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    total_score = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
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
        q = self.question
        if q.question_type == 'TEXT':
            self.needs_manual_review = True
            self.auto_score = None
        elif q.question_type == 'SINGLE_CHOICE':
            chosen = self.selected_choices.first()
            self.auto_score = q.points if (chosen and chosen.is_correct) else 0
        elif q.question_type == 'MULTI_CHOICE':
            chosen = list(self.selected_choices.all())
            correct = list(q.choices.filter(is_correct=True))
            if not correct:
                self.auto_score = 0
            else:
                # Полный балл только если множества совпадают
                if set(c.id for c in chosen) == set(c.id for c in correct):
                    self.auto_score = q.points
                else:
                    # Частичный балл: доля правильных выбранных минус неправильные
                    correct_ids = set(c.id for c in correct)
                    chosen_ids = set(c.id for c in chosen)
                    true_pos = len(chosen_ids & correct_ids)
                    false_pos = len(chosen_ids - correct_ids)
                    partial = max(0, true_pos - false_pos)
                    self.auto_score = int(q.points * (partial / len(correct_ids))) if correct_ids else 0
        self.save()
        return self.auto_score
