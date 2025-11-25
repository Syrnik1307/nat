from django.contrib import admin
from .models import ZoomAccount, ZoomPoolUsageMetrics


@admin.register(ZoomAccount)
class ZoomAccountAdmin(admin.ModelAdmin):
    list_display = ['email', 'current_meetings', 'max_concurrent_meetings', 
                    'is_active', 'last_used_at']
    list_filter = ['is_active']
    search_fields = ['email']
    readonly_fields = ['current_meetings', 'last_used_at', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('email', 'zoom_user_id')
        }),
        ('API Credentials', {
            'fields': ('api_key', 'api_secret')
        }),
        ('Настройки', {
            'fields': ('max_concurrent_meetings', 'is_active')
        }),
        ('Статистика', {
            'fields': ('current_meetings', 'last_used_at', 'created_at', 'updated_at')
        }),
    )


@admin.register(ZoomPoolUsageMetrics)
class ZoomPoolUsageMetricsAdmin(admin.ModelAdmin):
    list_display = ['current_in_use', 'peak_in_use', 'updated_at']
    readonly_fields = ['current_in_use', 'peak_in_use', 'created_at', 'updated_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
