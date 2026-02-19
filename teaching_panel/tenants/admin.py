from django.contrib import admin
from .models import (
    Tenant, TenantMembership, TenantResourceLimits,
    TenantUsageStats, TenantInvite, TenantVideoSettings,
)


class TenantMembershipInline(admin.TabularInline):
    model = TenantMembership
    extra = 0
    readonly_fields = ('joined_at', 'updated_at')
    raw_id_fields = ('user',)


class TenantResourceLimitsInline(admin.StackedInline):
    model = TenantResourceLimits
    extra = 0


class TenantUsageStatsInline(admin.StackedInline):
    model = TenantUsageStats
    extra = 0
    readonly_fields = (
        'current_teachers', 'current_students', 'current_groups',
        'current_courses', 'current_storage_mb', 'lessons_this_month',
        'homeworks_total', 'last_recalculated_at', 'updated_at',
    )


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'status', 'owner', 'created_at')
    list_filter = ('status',)
    search_fields = ('name', 'slug', 'owner__email')
    readonly_fields = ('id', 'created_at', 'updated_at')
    raw_id_fields = ('owner',)
    prepopulated_fields = {'slug': ('name',)}
    inlines = [TenantMembershipInline, TenantResourceLimitsInline, TenantUsageStatsInline]

    fieldsets = (
        ('Основное', {
            'fields': ('id', 'name', 'slug', 'status', 'owner')
        }),
        ('Контакты', {
            'fields': ('email', 'phone', 'website', 'logo_url')
        }),
        ('Локализация', {
            'fields': ('timezone', 'locale')
        }),
        ('Метаданные (JSON)', {
            'classes': ('collapse',),
            'fields': ('metadata',)
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        from .middleware import TenantMiddleware
        TenantMiddleware.clear_cache()


@admin.register(TenantMembership)
class TenantMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'tenant', 'role', 'is_active', 'joined_at')
    list_filter = ('role', 'is_active', 'tenant')
    search_fields = ('user__email', 'tenant__name')
    raw_id_fields = ('user', 'tenant')


@admin.register(TenantInvite)
class TenantInviteAdmin(admin.ModelAdmin):
    list_display = ('email', 'tenant', 'role', 'status', 'created_at')
    list_filter = ('status', 'role')
    search_fields = ('email', 'tenant__name')
