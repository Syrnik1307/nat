from django.contrib import admin
from django.utils.html import format_html
from .models import Homework, Question, Choice, StudentSubmission, Answer, HomeworkFile

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


@admin.register(HomeworkFile)
class HomeworkFileAdmin(admin.ModelAdmin):
    """Админка для просмотра загруженных файлов ДЗ (картинки, аудио от учеников)."""
    list_display = ('id', 'original_name', 'teacher_link', 'storage', 'size_kb', 'gdrive_link', 'created_at', 'migrated_at')
    list_filter = ('storage', 'created_at')
    search_fields = ('id', 'original_name', 'teacher__email', 'teacher__first_name', 'teacher__last_name')
    readonly_fields = ('id', 'teacher', 'original_name', 'mime_type', 'size', 'storage', 
                       'local_path', 'gdrive_file_id', 'gdrive_url', 'created_at', 'migrated_at')
    ordering = ('-created_at',)
    
    def teacher_link(self, obj):
        if obj.teacher:
            return format_html(
                '<a href="/admin/accounts/customuser/{}/change/">{}</a>',
                obj.teacher.id, obj.teacher.email
            )
        return '-'
    teacher_link.short_description = 'Учитель'
    
    def size_kb(self, obj):
        return f"{obj.size // 1024} KB"
    size_kb.short_description = 'Размер'
    
    def gdrive_link(self, obj):
        if obj.gdrive_file_id:
            return format_html(
                '<a href="https://drive.google.com/file/d/{}/view" target="_blank">GDrive</a>',
                obj.gdrive_file_id
            )
        return '-'
    gdrive_link.short_description = 'GDrive'
