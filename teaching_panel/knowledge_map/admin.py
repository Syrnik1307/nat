from django.contrib import admin
from .models import (
    ExamType, Subject, Section, Topic,
    StudentExamAssignment, StudentTopicMastery,
)


class TopicInline(admin.TabularInline):
    model = Topic
    extra = 0
    fields = ['code', 'name', 'task_number', 'max_score', 'difficulty', 'order']


class SectionInline(admin.TabularInline):
    model = Section
    extra = 0
    fields = ['code', 'name', 'order']
    show_change_link = True


@admin.register(ExamType)
class ExamTypeAdmin(admin.ModelAdmin):
    list_display = ['code', 'name']


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'exam_type', 'code', 'max_primary_score', 'total_tasks', 'order']
    list_filter = ['exam_type']
    inlines = [SectionInline]


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'subject', 'code', 'order']
    list_filter = ['subject__exam_type', 'subject']
    inlines = [TopicInline]


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'task_number', 'difficulty', 'max_score', 'section']
    list_filter = ['section__subject__exam_type', 'section__subject', 'difficulty']
    search_fields = ['name', 'code', 'fipi_code']


@admin.register(StudentExamAssignment)
class StudentExamAssignmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'subject', 'assigned_at']
    list_filter = ['subject__exam_type', 'subject']


@admin.register(StudentTopicMastery)
class StudentTopicMasteryAdmin(admin.ModelAdmin):
    list_display = [
        'student', 'topic', 'mastery_level', 'stability',
        'trend', 'status', 'attempted_count',
    ]
    list_filter = ['status', 'trend', 'topic__section__subject']
    search_fields = ['student__email', 'student__last_name', 'topic__name']
    readonly_fields = ['updated_at', 'first_attempt_at', 'last_attempt_at']
