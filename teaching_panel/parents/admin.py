from django.contrib import admin
from .models import ParentAccess, ParentAccessGrant, ParentComment


class ParentAccessGrantInline(admin.TabularInline):
    model = ParentAccessGrant
    extra = 0
    readonly_fields = ('created_at',)


class ParentCommentInline(admin.TabularInline):
    model = ParentComment
    extra = 0
    readonly_fields = ('created_at',)


@admin.register(ParentAccess)
class ParentAccessAdmin(admin.ModelAdmin):
    list_display = ('student', 'token', 'is_active', 'telegram_connected', 'view_count', 'last_viewed_at')
    list_filter = ('is_active', 'telegram_connected')
    search_fields = ('student__email', 'student__first_name', 'student__last_name', 'parent_name')
    readonly_fields = ('token', 'created_at', 'last_viewed_at', 'view_count')
    inlines = [ParentAccessGrantInline]


@admin.register(ParentAccessGrant)
class ParentAccessGrantAdmin(admin.ModelAdmin):
    list_display = ('subject_label', 'teacher', 'parent_access', 'group', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('subject_label', 'teacher__email', 'parent_access__student__email')
    readonly_fields = ('created_at',)
    inlines = [ParentCommentInline]


@admin.register(ParentComment)
class ParentCommentAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'grant', 'text_preview', 'created_at')
    readonly_fields = ('created_at',)

    def text_preview(self, obj):
        return obj.text[:80] + '...' if len(obj.text) > 80 else obj.text
    text_preview.short_description = 'Текст'
