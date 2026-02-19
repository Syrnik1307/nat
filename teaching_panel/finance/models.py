"""
Finance models for student-teacher billing.

This module handles internal lesson accounting between students and teachers.
NOT related to platform subscription payments (accounts.Subscription/Payment).

Key concepts:
- StudentFinancialProfile: A "wallet" for a student with a specific teacher
- Transaction: Immutable record of every financial event (charges, deposits, etc.)
"""
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class StudentFinancialProfile(models.Model):
    """
    Финансовый профиль (кошелёк) ученика у конкретного учителя.
    
    Один ученик может иметь профили у разных учителей.
    Баланс хранится в валюте, "остаток уроков" — вычисляемое значение.
    """
    
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='student_financial_profiles',
        limit_choices_to={'role': 'student'},
        verbose_name=_('ученик')
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='teacher_student_wallets',
        limit_choices_to={'role': 'teacher'},
        verbose_name=_('учитель')
    )
    
    balance = models.DecimalField(
        _('баланс'),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_('Текущий баланс. Положительный = предоплата, отрицательный = долг')
    )
    
    default_lesson_price = models.DecimalField(
        _('стоимость урока'),
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_('Стандартная стоимость одного урока для этого ученика')
    )
    
    currency = models.CharField(
        _('валюта'),
        max_length=3,
        default='RUB'
    )
    
    debt_limit = models.DecimalField(
        _('лимит долга'),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_('Максимальный допустимый долг. 0 = без лимита')
    )
    
    notes = models.TextField(
        _('заметки'),
        blank=True,
        help_text=_('Заметки учителя о финансах ученика')
    )
    
    created_at = models.DateTimeField(_('создан'), auto_now_add=True)
    updated_at = models.DateTimeField(_('обновлён'), auto_now=True)
    
    # === Multi-Tenant ===
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='financial_profiles',
        help_text='Школа'
    )
    
    class Meta:
        verbose_name = _('финансовый профиль ученика')
        verbose_name_plural = _('финансовые профили учеников')
        unique_together = ('student', 'teacher')
        ordering = ['student__last_name', 'student__first_name']
        indexes = [
            models.Index(fields=['teacher', 'student']),
            models.Index(fields=['balance']),
        ]
    
    def __str__(self):
        return f"{self.student.get_full_name()} @ {self.teacher.get_full_name()}: {self.balance} {self.currency}"
    
    @property
    def lessons_left(self) -> float:
        """Расчётное количество оставшихся уроков."""
        if self.default_lesson_price <= 0:
            return 0.0
        return float(self.balance / self.default_lesson_price)
    
    @property
    def is_debtor(self) -> bool:
        """Есть ли долг (отрицательный баланс)."""
        return self.balance < 0
    
    @property
    def debt_limit_exceeded(self) -> bool:
        """Превышен ли лимит долга."""
        if self.debt_limit <= 0:
            return False  # Без лимита
        return self.balance < -self.debt_limit
    
    @property
    def balance_status(self) -> str:
        """Статус баланса для отображения ученику."""
        if self.balance < 0:
            return 'debt'
        elif self.lessons_left < 2:
            return 'low'
        return 'ok'


class TransactionType(models.TextChoices):
    """Типы финансовых транзакций."""
    DEPOSIT = 'DEPOSIT', _('Пополнение')
    LESSON_CHARGE = 'LESSON_CHARGE', _('Списание за урок')
    ADJUSTMENT = 'ADJUSTMENT', _('Корректировка')
    REFUND = 'REFUND', _('Возврат')


class Transaction(models.Model):
    """
    Неизменяемая запись финансовой операции.
    
    После создания транзакция НЕ может быть изменена или удалена.
    Для исправления ошибок создаётся новая транзакция типа ADJUSTMENT или REFUND.
    """
    
    wallet = models.ForeignKey(
        StudentFinancialProfile,
        on_delete=models.PROTECT,  # Нельзя удалить кошелёк с транзакциями
        related_name='transactions',
        verbose_name=_('кошелёк')
    )
    
    amount = models.DecimalField(
        _('сумма'),
        max_digits=10,
        decimal_places=2,
        help_text=_('Положительное = приход, отрицательное = расход')
    )
    
    transaction_type = models.CharField(
        _('тип'),
        max_length=20,
        choices=TransactionType.choices
    )
    
    lesson = models.ForeignKey(
        'schedule.Lesson',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='finance_transactions',
        verbose_name=_('связанный урок'),
        help_text=_('Урок, за который списаны/возвращены деньги')
    )
    
    is_group_lesson = models.BooleanField(
        _('групповой урок'),
        default=False,
        help_text=_('True если урок был групповым (>1 ученика)')
    )
    
    override_price = models.DecimalField(
        _('изменённая цена'),
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('Если задано — использовалась вместо default_lesson_price (скидка, пробный и т.д.)')
    )
    
    description = models.TextField(
        _('описание'),
        blank=True
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_finance_transactions',
        verbose_name=_('создал')
    )
    
    # Флаг автоматического создания (signal vs manual)
    auto_created = models.BooleanField(
        _('автоматически'),
        default=False,
        help_text=_('True если создано автоматически при завершении урока')
    )
    
    created_at = models.DateTimeField(_('создан'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('транзакция')
        verbose_name_plural = _('транзакции')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['wallet', '-created_at']),
            models.Index(fields=['lesson']),
            models.Index(fields=['transaction_type', '-created_at']),
        ]
    
    def __str__(self):
        sign = '+' if self.amount > 0 else ''
        return f"{self.get_transaction_type_display()}: {sign}{self.amount} ({self.wallet.student.get_full_name()})"
    
    def save(self, *args, **kwargs):
        # Immutable: запрет редактирования после создания
        if self.pk:
            raise ValueError(_('Транзакции нельзя редактировать. Создайте корректировку.'))
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        # Запрет удаления
        raise ValueError(_('Транзакции нельзя удалять. Создайте возврат или корректировку.'))
