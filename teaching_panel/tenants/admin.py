from django.contrib import admin
from .models import School, SchoolMembership


class SchoolMembershipInline(admin.TabularInline):
    model = SchoolMembership
    extra = 0
    readonly_fields = ('joined_at',)
    raw_id_fields = ('user',)


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'owner', 'is_active', 'is_default', 'created_at')
    list_filter = ('is_active', 'is_default', 'currency')
    search_fields = ('name', 'slug', 'owner__email')
    readonly_fields = ('id', 'created_at', 'updated_at')
    raw_id_fields = ('owner',)
    prepopulated_fields = {'slug': ('name',)}
    inlines = [SchoolMembershipInline]
    
    fieldsets = (
        ('Основное', {
            'fields': ('id', 'name', 'slug', 'owner', 'is_active', 'is_default')
        }),
        ('Брендинг', {
            'fields': ('logo_url', 'favicon_url', 'primary_color', 'secondary_color')
        }),
        ('Домены', {
            'fields': ('custom_domain',),
            'description': 'Поддомен вычисляется из slug: slug.lectiospace.ru'
        }),
        ('Платежи', {
            'classes': ('collapse',),
            'fields': (
                'default_payment_provider',
                'yookassa_account_id', 'yookassa_secret_key',
                'tbank_terminal_key', 'tbank_password',
                'monthly_price', 'yearly_price', 'currency',
                'revenue_share_percent',
            )
        }),
        ('Telegram', {
            'classes': ('collapse',),
            'fields': ('telegram_bot_token', 'telegram_bot_username', 'telegram_bot_enabled')
        }),
        ('Feature Flags', {
            'classes': ('collapse',),
            'fields': (
                'zoom_enabled', 'google_meet_enabled', 'homework_enabled',
                'recordings_enabled', 'finance_enabled', 'concierge_enabled',
            )
        }),
        ('Лимиты', {
            'classes': ('collapse',),
            'fields': ('max_students', 'max_groups', 'max_teachers', 'max_storage_gb')
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Очистить кэш middleware при изменении школы
        from tenants.middleware import TenantMiddleware
        TenantMiddleware.clear_cache()


@admin.register(SchoolMembership)
class SchoolMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'school', 'role', 'is_active', 'joined_at')
    list_filter = ('role', 'is_active', 'school')
    search_fields = ('user__email', 'school__name')
    raw_id_fields = ('user', 'school')
