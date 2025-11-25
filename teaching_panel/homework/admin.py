from django.contrib import admin
from .models import Homework, Question, Choice, StudentSubmission, Answer

@admin.register(Homework)
class HomeworkAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'teacher', 'lesson', 'created_at')
    search_fields = ('title', 'description')

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'homework', 'question_type', 'points', 'order')
    list_filter = ('question_type',)

@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'text', 'is_correct')
    list_filter = ('is_correct',)

@admin.register(StudentSubmission)
class StudentSubmissionAdmin(admin.ModelAdmin):
    list_display = ('id', 'homework', 'student', 'status', 'total_score', 'created_at')
    list_filter = ('status',)

@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('id', 'submission', 'question', 'auto_score', 'needs_manual_review')
    list_filter = ('needs_manual_review',)
