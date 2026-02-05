"""
Django admin configuration for finance models.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import StudentFinancialProfile, Transaction


@admin.register(StudentFinancialProfile)
class StudentFinancialProfileAdmin(admin.ModelAdmin):
    """Админка для финансовых профилей учеников."""
    
    list_display = [
        'id',
        'student_display',
        'teacher_display',
        'balance_display',
        'default_lesson_price',
        'lessons_left_display',
        'status_display',
        'updated_at',
    ]
    list_filter = ['teacher', 'currency', 'created_at']
    search_fields = [
        'student__email',
        'student__first_name',
        'student__last_name',
        'teacher__email',
    ]
    readonly_fields = ['balance', 'created_at', 'updated_at']
    raw_id_fields = ['student', 'teacher']
    ordering = ['-updated_at']
    
    fieldsets = (
        ('Связи', {
            'fields': ('student', 'teacher')
        }),
        ('Финансы', {
            'fields': ('balance', 'default_lesson_price', 'currency', 'debt_limit')
        }),
        ('Заметки', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def student_display(self, obj):
        return f"{obj.student.get_full_name()} ({obj.student.email})"
    student_display.short_description = 'Ученик'
    
    def teacher_display(self, obj):
        return f"{obj.teacher.get_full_name()}"
    teacher_display.short_description = 'Учитель'
    
    def balance_display(self, obj):
        color = 'red' if obj.balance < 0 else 'green' if obj.balance > 0 else 'gray'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, obj.balance, obj.currency
        )
    balance_display.short_description = 'Баланс'
    
    def lessons_left_display(self, obj):
        lessons = obj.lessons_left
        if lessons < 0:
            color = 'red'
        elif lessons < 2:
            color = 'orange'
        else:
            color = 'green'
        return format_html(
            '<span style="color: {};">{:.1f}</span>',
            color, lessons
        )
    lessons_left_display.short_description = 'Уроков'
    
    def status_display(self, obj):
        if obj.debt_limit_exceeded:
            return format_html('<span style="color: red;">ЛИМИТ</span>')
        elif obj.is_debtor:
            return format_html('<span style="color: orange;">Долг</span>')
        return format_html('<span style="color: green;">OK</span>')
    status_display.short_description = 'Статус'


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """Админка для транзакций (только просмотр)."""
    
    list_display = [
        'id',
        'wallet_display',
        'amount_display',
        'transaction_type',
        'lesson_display',
        'auto_created',
        'created_by_display',
        'created_at',
    ]
    list_filter = ['transaction_type', 'is_group_lesson', 'auto_created', 'created_at']
    search_fields = [
        'wallet__student__email',
        'wallet__student__first_name',
        'wallet__student__last_name',
        'description',
    ]
    readonly_fields = [
        'wallet', 'amount', 'transaction_type', 'lesson',
        'is_group_lesson', 'override_price', 'description',
        'created_by', 'auto_created', 'created_at'
    ]
    raw_id_fields = ['wallet', 'lesson', 'created_by']
    ordering = ['-created_at']
    
    # Запрещаем создание/редактирование/удаление через админку
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def wallet_display(self, obj):
        return f"{obj.wallet.student.get_full_name()}"
    wallet_display.short_description = 'Ученик'
    
    def amount_display(self, obj):
        color = 'green' if obj.amount > 0 else 'red'
        sign = '+' if obj.amount > 0 else ''
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}{}</span>',
            color, sign, obj.amount
        )
    amount_display.short_description = 'Сумма'
    
    def lesson_display(self, obj):
        if obj.lesson:
            return f"#{obj.lesson.id}: {obj.lesson.display_name}"
        return '-'
    lesson_display.short_description = 'Урок'
    
    def created_by_display(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name()
        return '-'
    created_by_display.short_description = 'Создал'
