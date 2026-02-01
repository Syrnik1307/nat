"""
Market admin configuration.
"""
from django.contrib import admin
from .models import Product, MarketOrder


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['title', 'product_type', 'price', 'is_active', 'sort_order', 'created_at']
    list_filter = ['is_active', 'product_type']
    search_fields = ['title', 'description']
    list_editable = ['is_active', 'sort_order', 'price']
    ordering = ['sort_order', 'title']


@admin.register(MarketOrder)
class MarketOrderAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user_email', 'product', 'status', 'total_amount',
        'contact_info_display', 'auto_connect_display', 'created_at', 'paid_at'
    ]
    list_filter = ['status', 'product', 'created_at']
    search_fields = ['user__email', 'payment_id', 'order_details']
    readonly_fields = [
        'payment_id', 'payment_url', 'created_at', 'updated_at',
        'zoom_details_display'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Основное', {
            'fields': ('user', 'product', 'status', 'total_amount')
        }),
        ('Платеж', {
            'fields': ('payment_id', 'payment_url', 'paid_at')
        }),
        ('Детали Zoom', {
            'fields': ('zoom_details_display', 'order_details'),
            'classes': ('collapse',),
        }),
        ('Администрирование', {
            'fields': ('admin_notes', 'completed_at')
        }),
        ('Метаданные', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Пользователь'
    user_email.admin_order_field = 'user__email'
    
    def contact_info_display(self, obj):
        return obj.contact_info or '-'
    contact_info_display.short_description = 'Контакт'
    
    def auto_connect_display(self, obj):
        return 'Да' if obj.auto_connect else 'Нет'
    auto_connect_display.short_description = 'Авто-подключение'
    
    def zoom_details_display(self, obj):
        """Display Zoom order details in a readable format."""
        if obj.product.product_type != 'zoom':
            return 'Не Zoom заказ'
        
        details = []
        details.append(f"Тип: {'Новый аккаунт' if obj.is_new_account else 'Существующий'}")
        details.append(f"Email/Login: {obj.zoom_email or '-'}")
        details.append(f"Пароль: {obj.zoom_password or '-'}")
        details.append(f"Контакт: {obj.contact_info or '-'}")
        details.append(f"Авто-подключение: {'Да' if obj.auto_connect else 'Нет'}")
        return '\n'.join(details)
    zoom_details_display.short_description = 'Данные Zoom'
