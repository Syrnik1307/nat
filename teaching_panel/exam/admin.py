from django.contrib import admin
from .models import (
    ExamBlueprint, ExamTaskSlot, ExamTask,
    ExamVariant, ExamVariantTask, ExamAttempt,
)


class ExamTaskSlotInline(admin.TabularInline):
    model = ExamTaskSlot
    extra = 0
    ordering = ['task_number']


@admin.register(ExamBlueprint)
class ExamBlueprintAdmin(admin.ModelAdmin):
    list_display = ['title', 'subject', 'year', 'duration_minutes', 'total_primary_score', 'is_active', 'created_by']
    list_filter = ['is_active', 'year', 'subject__exam_type']
    search_fields = ['title']
    inlines = [ExamTaskSlotInline]


@admin.register(ExamTask)
class ExamTaskAdmin(admin.ModelAdmin):
    list_display = ['id', 'blueprint', 'task_number', 'difficulty', 'source', 'usage_count', 'is_active']
    list_filter = ['blueprint', 'task_number', 'difficulty', 'source', 'is_active']
    search_fields = ['question__prompt', 'tags']


class ExamVariantTaskInline(admin.TabularInline):
    model = ExamVariantTask
    extra = 0
    ordering = ['task_number']


@admin.register(ExamVariant)
class ExamVariantAdmin(admin.ModelAdmin):
    list_display = ['id', 'blueprint', 'variant_number', 'title', 'is_manual', 'homework', 'created_at']
    list_filter = ['blueprint', 'is_manual']
    inlines = [ExamVariantTaskInline]


@admin.register(ExamAttempt)
class ExamAttemptAdmin(admin.ModelAdmin):
    list_display = ['id', 'submission', 'variant', 'started_at', 'deadline_at', 'auto_submitted', 'primary_score', 'test_score', 'grade']
    list_filter = ['auto_submitted', 'variant__blueprint']
    readonly_fields = ['task_scores']
