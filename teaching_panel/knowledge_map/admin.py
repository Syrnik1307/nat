from django.contrib import admin
from .models import ExamType, Subject, Topic, ExamAssignment, StudentTopicScore


class TopicInline(admin.TabularInline):
    model = Topic
    extra = 0


@admin.register(ExamType)
class ExamTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_preset', 'created_at']
    list_filter = ['is_preset']


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'exam_type', 'slug', 'order']
    list_filter = ['exam_type']
    inlines = [TopicInline]


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ['number', 'title', 'subject', 'max_points']
    list_filter = ['subject__exam_type', 'subject']


@admin.register(ExamAssignment)
class ExamAssignmentAdmin(admin.ModelAdmin):
    list_display = ['subject', 'teacher', 'group', 'student', 'created_at']
    list_filter = ['subject__exam_type']


@admin.register(StudentTopicScore)
class StudentTopicScoreAdmin(admin.ModelAdmin):
    list_display = ['student', 'topic', 'score_percent', 'attempts_count', 'trend', 'updated_at']
    list_filter = ['trend', 'topic__subject']
    readonly_fields = ['updated_at']
