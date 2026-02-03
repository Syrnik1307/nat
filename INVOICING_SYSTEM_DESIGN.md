# Invoicing System — Архитектурный Дизайн

## 1. Analysis of Current State

### 1.1 Существующие модели (accounts/models.py)

| Модель | Назначение | Связь с Invoicing |
|--------|-----------|-------------------|
| `CustomUser` | Пользователи (student/teacher/admin) | Teacher = продавец, Student = плательщик |
| `Subscription` | Подписка учителя на платформу | Не связано напрямую, но можно проверять active subscription для создания счетов |
| `Payment` | Платежи за подписку | Шаблон для `InvoicePayment` |

### 1.2 Существующие модели (schedule/models.py)

| Модель | Назначение | Связь с Invoicing |
|--------|-----------|-------------------|
| `Group` | Учебные группы | Счёт может быть привязан к группе (оплата курса) |
| `Lesson` | Уроки | Счёт может оплачивать конкретные уроки |

### 1.3 Существующие модели (market/models.py)

| Модель | Назначение | Связь с Invoicing |
|--------|-----------|-------------------|
| `Product` | Цифровые товары (Zoom) | Можно расширить для услуг репетитора |
| `MarketOrder` | Заказы товаров | Шаблон для структуры Invoice |

### 1.4 Текущая интеграция T-Bank (tbank_service.py)

**Что реализовано:**
- `create_subscription_payment()` — одностадийные платежи картой
- `charge_recurring()` — рекуррентные платежи по RebillId
- `process_notification()` — обработка webhook'ов
- `_generate_token()` / `_verify_notification_token()` — подпись запросов

**Что НЕ реализовано:**
- Платежи через СБП (QR-код)
- Агентская схема (Agent) в чеке
- Расщепление платежа (Shops / Marketplace)

---

## 2. Database Schema Design

### 2.1 Новые модели

```python
# teaching_panel/invoicing/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
import uuid


class TeacherPaymentSettings(models.Model):
    """
    Платёжные настройки преподавателя.
    Хранит ИНН, название ИП/ООО для формирования чеков.
    """
    teacher = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payment_settings',
        limit_choices_to={'role': 'teacher'}
    )
    
    # Юридические данные для чека (агентская схема)
    legal_name = models.CharField(
        'Наименование ИП/ООО',
        max_length=255,
        help_text='Например: ИП Иванов Иван Иванович'
    )
    inn = models.CharField(
        'ИНН',
        max_length=12,
        help_text='ИНН преподавателя (12 цифр для ИП, 10 для ООО)'
    )
    phone = models.CharField(
        'Телефон для чека',
        max_length=20,
        blank=True,
        default='',
        help_text='Телефон поставщика для печати в чеке'
    )
    
    # Банковские реквизиты для вывода (опционально, для будущего)
    bank_account = models.CharField(
        'Расчётный счёт',
        max_length=20,
        blank=True,
        default=''
    )
    bank_bik = models.CharField(
        'БИК банка',
        max_length=9,
        blank=True,
        default=''
    )
    
    # Комиссия платформы (можно настраивать индивидуально)
    platform_fee_percent = models.DecimalField(
        'Комиссия платформы (%)',
        max_digits=5,
        decimal_places=2,
        default=Decimal('5.00'),
        help_text='Процент комиссии платформы с каждого платежа'
    )
    
    is_verified = models.BooleanField(
        'Верифицирован',
        default=False,
        help_text='Прошёл ли преподаватель проверку документов'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Платёжные настройки преподавателя'
        verbose_name_plural = 'Платёжные настройки преподавателей'
    
    def __str__(self):
        return f"Платёжные настройки: {self.teacher.email}"


class Invoice(models.Model):
    """
    Счёт на оплату от преподавателя ученику.
    """
    STATUS_DRAFT = 'draft'
    STATUS_SENT = 'sent'
    STATUS_PAID = 'paid'
    STATUS_PARTIALLY_PAID = 'partially_paid'
    STATUS_CANCELLED = 'cancelled'
    STATUS_EXPIRED = 'expired'
    STATUS_REFUNDED = 'refunded'
    
    STATUS_CHOICES = (
        (STATUS_DRAFT, 'Черновик'),
        (STATUS_SENT, 'Отправлен'),
        (STATUS_PAID, 'Оплачен'),
        (STATUS_PARTIALLY_PAID, 'Частично оплачен'),
        (STATUS_CANCELLED, 'Отменён'),
        (STATUS_EXPIRED, 'Просрочен'),
        (STATUS_REFUNDED, 'Возврат'),
    )
    
    TYPE_LESSON_PACK = 'lesson_pack'
    TYPE_SINGLE_LESSON = 'single_lesson'
    TYPE_COURSE = 'course'
    TYPE_CUSTOM = 'custom'
    
    TYPE_CHOICES = (
        (TYPE_LESSON_PACK, 'Пакет уроков'),
        (TYPE_SINGLE_LESSON, 'Один урок'),
        (TYPE_COURSE, 'Курс'),
        (TYPE_CUSTOM, 'Произвольный'),
    )
    
    # Уникальный публичный ID для ссылки (вместо sequential ID)
    public_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )
    
    # Номер счёта (для бухгалтерии)
    invoice_number = models.CharField(
        'Номер счёта',
        max_length=50,
        unique=True,
        help_text='Формат: INV-{teacher_id}-{year}-{seq}'
    )
    
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='issued_invoices',
        limit_choices_to={'role': 'teacher'},
        verbose_name='Преподаватель'
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_invoices',
        limit_choices_to={'role': 'student'},
        verbose_name='Ученик'
    )
    
    # Опциональные связи
    group = models.ForeignKey(
        'schedule.Group',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoices',
        verbose_name='Группа'
    )
    
    invoice_type = models.CharField(
        'Тип счёта',
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_CUSTOM
    )
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT
    )
    
    # Суммы
    amount = models.DecimalField(
        'Сумма счёта',
        max_digits=10,
        decimal_places=2
    )
    paid_amount = models.DecimalField(
        'Оплаченная сумма',
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    currency = models.CharField(
        'Валюта',
        max_length=3,
        default='RUB'
    )
    
    # Для пакетов уроков
    lessons_count = models.PositiveIntegerField(
        'Количество уроков',
        default=0,
        help_text='Сколько уроков входит в счёт (для lesson_pack)'
    )
    lessons_used = models.PositiveIntegerField(
        'Использовано уроков',
        default=0
    )
    
    # Описание
    title = models.CharField(
        'Название',
        max_length=255,
        help_text='Например: "Оплата за 10 уроков математики"'
    )
    description = models.TextField(
        'Описание',
        blank=True,
        help_text='Детальное описание за что счёт'
    )
    
    # Сроки
    due_date = models.DateTimeField(
        'Срок оплаты',
        null=True,
        blank=True
    )
    
    # Ссылка на оплату (генерируется T-Bank)
    payment_url = models.URLField(
        'Ссылка на оплату',
        max_length=500,
        blank=True
    )
    qr_code_data = models.TextField(
        'Данные QR-кода СБП',
        blank=True,
        help_text='Payload для генерации QR-кода'
    )
    
    # Даты
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sent_at = models.DateTimeField('Отправлен', null=True, blank=True)
    paid_at = models.DateTimeField('Оплачен', null=True, blank=True)
    expires_at = models.DateTimeField('Истекает', null=True, blank=True)
    
    # Метаданные
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        verbose_name = 'Счёт'
        verbose_name_plural = 'Счета'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['teacher', 'status']),
            models.Index(fields=['student', 'status']),
            models.Index(fields=['public_id']),
        ]
    
    def __str__(self):
        return f"{self.invoice_number}: {self.title} ({self.get_status_display()})"
    
    @property
    def remaining_amount(self):
        return self.amount - self.paid_amount
    
    @property
    def remaining_lessons(self):
        return max(0, self.lessons_count - self.lessons_used)
    
    @property
    def is_expired(self):
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    def get_payment_link(self):
        """Возвращает ссылку на страницу оплаты"""
        from django.conf import settings
        return f"{settings.FRONTEND_URL}/pay/{self.public_id}"
    
    def generate_invoice_number(self):
        """Генерирует уникальный номер счёта"""
        year = timezone.now().year
        seq = Invoice.objects.filter(
            teacher=self.teacher,
            created_at__year=year
        ).count() + 1
        return f"INV-{self.teacher.id}-{year}-{seq:04d}"
    
    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = self.generate_invoice_number()
        super().save(*args, **kwargs)


class InvoiceItem(models.Model):
    """
    Позиция в счёте (для детализации).
    """
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='items'
    )
    
    name = models.CharField('Наименование', max_length=255)
    description = models.TextField('Описание', blank=True)
    quantity = models.PositiveIntegerField('Количество', default=1)
    unit_price = models.DecimalField('Цена за единицу', max_digits=10, decimal_places=2)
    
    # Связь с уроком (опционально)
    lesson = models.ForeignKey(
        'schedule.Lesson',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoice_items'
    )
    
    class Meta:
        verbose_name = 'Позиция счёта'
        verbose_name_plural = 'Позиции счёта'
    
    @property
    def total_price(self):
        return self.quantity * self.unit_price
    
    def __str__(self):
        return f"{self.name} x{self.quantity}"


class InvoicePayment(models.Model):
    """
    Платёж по счёту (может быть несколько при частичной оплате).
    """
    STATUS_PENDING = 'pending'
    STATUS_SUCCEEDED = 'succeeded'
    STATUS_FAILED = 'failed'
    STATUS_REFUNDED = 'refunded'
    
    STATUS_CHOICES = (
        (STATUS_PENDING, 'Ожидает'),
        (STATUS_SUCCEEDED, 'Успешно'),
        (STATUS_FAILED, 'Ошибка'),
        (STATUS_REFUNDED, 'Возврат'),
    )
    
    PAYMENT_METHOD_CARD = 'card'
    PAYMENT_METHOD_SBP = 'sbp'
    
    PAYMENT_METHOD_CHOICES = (
        (PAYMENT_METHOD_CARD, 'Банковская карта'),
        (PAYMENT_METHOD_SBP, 'СБП (QR-код)'),
    )
    
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    
    amount = models.DecimalField('Сумма', max_digits=10, decimal_places=2)
    currency = models.CharField('Валюта', max_length=3, default='RUB')
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    
    payment_method = models.CharField(
        'Способ оплаты',
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default=PAYMENT_METHOD_SBP
    )
    
    # T-Bank данные
    tbank_payment_id = models.CharField(
        'T-Bank PaymentId',
        max_length=100,
        unique=True
    )
    tbank_order_id = models.CharField(
        'T-Bank OrderId',
        max_length=100
    )
    
    # Комиссии
    platform_fee = models.DecimalField(
        'Комиссия платформы',
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    acquiring_fee = models.DecimalField(
        'Комиссия эквайринга',
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    teacher_payout = models.DecimalField(
        'Выплата преподавателю',
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        verbose_name = 'Платёж по счёту'
        verbose_name_plural = 'Платежи по счетам'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Платёж {self.tbank_payment_id} на {self.amount} RUB"


class LessonBalance(models.Model):
    """
    Баланс уроков ученика у конкретного преподавателя.
    Обновляется при оплате счетов и проведении уроков.
    """
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='lesson_balances',
        limit_choices_to={'role': 'student'}
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='student_balances',
        limit_choices_to={'role': 'teacher'}
    )
    group = models.ForeignKey(
        'schedule.Group',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lesson_balances'
    )
    
    # Баланс
    total_lessons = models.PositiveIntegerField(
        'Всего уроков куплено',
        default=0
    )
    used_lessons = models.PositiveIntegerField(
        'Использовано уроков',
        default=0
    )
    
    # Денежный баланс (альтернатива урокам)
    balance_amount = models.DecimalField(
        'Денежный баланс',
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Остаток средств (если оплата не привязана к урокам)'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Баланс уроков'
        verbose_name_plural = 'Балансы уроков'
        unique_together = ['student', 'teacher', 'group']
    
    @property
    def remaining_lessons(self):
        return max(0, self.total_lessons - self.used_lessons)
    
    def add_lessons(self, count: int, invoice: Invoice = None):
        """Добавить уроки после оплаты"""
        self.total_lessons += count
        self.save(update_fields=['total_lessons', 'updated_at'])
        
        # Логируем операцию
        LessonBalanceLog.objects.create(
            balance=self,
            operation='add',
            lessons_delta=count,
            invoice=invoice,
            notes=f'Оплата счёта {invoice.invoice_number}' if invoice else 'Ручное добавление'
        )
    
    def use_lesson(self, lesson=None):
        """Списать урок после проведения"""
        if self.remaining_lessons <= 0:
            return False
        self.used_lessons += 1
        self.save(update_fields=['used_lessons', 'updated_at'])
        
        LessonBalanceLog.objects.create(
            balance=self,
            operation='use',
            lessons_delta=-1,
            lesson=lesson,
            notes=f'Урок {lesson.id}' if lesson else 'Списание урока'
        )
        return True
    
    def __str__(self):
        return f"{self.student.email} → {self.teacher.email}: {self.remaining_lessons} уроков"


class LessonBalanceLog(models.Model):
    """
    Лог изменений баланса уроков.
    """
    OPERATION_ADD = 'add'
    OPERATION_USE = 'use'
    OPERATION_REFUND = 'refund'
    OPERATION_MANUAL = 'manual'
    
    OPERATION_CHOICES = (
        (OPERATION_ADD, 'Пополнение'),
        (OPERATION_USE, 'Списание'),
        (OPERATION_REFUND, 'Возврат'),
        (OPERATION_MANUAL, 'Ручная корректировка'),
    )
    
    balance = models.ForeignKey(
        LessonBalance,
        on_delete=models.CASCADE,
        related_name='logs'
    )
    operation = models.CharField(
        'Операция',
        max_length=20,
        choices=OPERATION_CHOICES
    )
    lessons_delta = models.IntegerField(
        'Изменение уроков',
        help_text='Положительное = добавление, отрицательное = списание'
    )
    
    # Связи с источником операции
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    lesson = models.ForeignKey(
        'schedule.Lesson',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    notes = models.TextField('Примечания', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name = 'Лог баланса уроков'
        verbose_name_plural = 'Логи баланса уроков'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_operation_display()}: {self.lessons_delta} уроков"


class TeacherPayout(models.Model):
    """
    Выплата преподавателю (агрегация платежей за период).
    На первом этапе — информационная модель.
    """
    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    
    STATUS_CHOICES = (
        (STATUS_PENDING, 'Ожидает'),
        (STATUS_PROCESSING, 'В обработке'),
        (STATUS_COMPLETED, 'Выплачено'),
        (STATUS_FAILED, 'Ошибка'),
    )
    
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payouts'
    )
    
    period_start = models.DateField('Начало периода')
    period_end = models.DateField('Конец периода')
    
    gross_amount = models.DecimalField(
        'Общая сумма платежей',
        max_digits=10,
        decimal_places=2
    )
    platform_fee = models.DecimalField(
        'Комиссия платформы',
        max_digits=10,
        decimal_places=2
    )
    acquiring_fee = models.DecimalField(
        'Комиссия эквайринга',
        max_digits=10,
        decimal_places=2
    )
    net_amount = models.DecimalField(
        'К выплате',
        max_digits=10,
        decimal_places=2
    )
    
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )
    
    payments = models.ManyToManyField(
        InvoicePayment,
        related_name='payouts'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Выплата преподавателю'
        verbose_name_plural = 'Выплаты преподавателям'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Выплата {self.teacher.email}: {self.net_amount} RUB"
```

---

## 3. API Flow — Создание и оплата счёта через СБП

### 3.1 Sequence Diagram

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│ Teacher  │     │ Frontend │     │ Backend  │     │  T-Bank  │     │ Student  │
└────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘
     │                │                │                │                │
     │ 1. Создать счёт│                │                │                │
     │───────────────>│                │                │                │
     │                │ POST /invoices │                │                │
     │                │───────────────>│                │                │
     │                │                │ create Invoice │                │
     │                │                │ (status=draft) │                │
     │                │<───────────────│                │                │
     │                │                │                │                │
     │ 2. Отправить   │                │                │                │
     │    ученику     │                │                │                │
     │───────────────>│                │                │                │
     │                │ POST /invoices │                │                │
     │                │ /{id}/send     │                │                │
     │                │───────────────>│                │                │
     │                │                │ Update status= │                │
     │                │                │ sent + Telegram│                │
     │                │                │────────────────────────────────>│
     │                │                │                │   Ссылка на    │
     │                │                │                │   оплату       │
     │                │                │                │                │
     │                │                │                │ 3. Открыть     │
     │                │                │                │    ссылку      │
     │                │                │                │<───────────────│
     │                │                │                │                │
     │                │                │ GET /pay/{uuid}│                │
     │                │                │<───────────────────────────────│
     │                │                │                │                │
     │                │                │ 4. POST Init   │                │
     │                │                │   (СБП + Agent)│                │
     │                │                │───────────────>│                │
     │                │                │                │                │
     │                │                │   PaymentURL + │                │
     │                │                │   QR data      │                │
     │                │                │<───────────────│                │
     │                │                │                │                │
     │                │                │ Redirect/QR    │                │
     │                │                │────────────────────────────────>│
     │                │                │                │                │
     │                │                │                │ 5. Оплата в    │
     │                │                │                │    банке       │
     │                │                │                │<───────────────│
     │                │                │                │                │
     │                │                │ 6. Webhook     │                │
     │                │                │ CONFIRMED      │                │
     │                │                │<───────────────│                │
     │                │                │                │                │
     │                │                │ Update Invoice │                │
     │                │                │ + LessonBalance│                │
     │                │                │ + Notify       │                │
     │                │                │────────────────────────────────>│
     │<─ ─ ─ ─ ─ ─ ─ ─│                │                │   Оплачено!   │
     │   Уведомление  │                │                │                │
     │                │                │                │                │
```

### 3.2 API Endpoints

```python
# teaching_panel/invoicing/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('invoices', views.InvoiceViewSet, basename='invoice')
router.register('payment-settings', views.TeacherPaymentSettingsViewSet, basename='payment-settings')
router.register('lesson-balances', views.LessonBalanceViewSet, basename='lesson-balance')

urlpatterns = [
    path('', include(router.urls)),
    path('pay/<uuid:public_id>/', views.PaymentPageView.as_view(), name='payment-page'),
    path('webhook/invoice/', views.InvoiceWebhookView.as_view(), name='invoice-webhook'),
]
```

**Endpoints:**

| Method | URL | Описание | Доступ |
|--------|-----|----------|--------|
| `POST` | `/api/invoicing/invoices/` | Создать счёт | Teacher |
| `GET` | `/api/invoicing/invoices/` | Список счетов | Teacher/Student |
| `GET` | `/api/invoicing/invoices/{id}/` | Детали счёта | Teacher/Student |
| `POST` | `/api/invoicing/invoices/{id}/send/` | Отправить ученику | Teacher |
| `POST` | `/api/invoicing/invoices/{id}/cancel/` | Отменить счёт | Teacher |
| `GET` | `/api/invoicing/pay/{public_id}/` | Страница оплаты (public) | Public |
| `POST` | `/api/invoicing/pay/{public_id}/init/` | Инициировать платёж | Public |
| `POST` | `/api/invoicing/webhook/invoice/` | Webhook от T-Bank | T-Bank |
| `GET` | `/api/invoicing/lesson-balances/` | Балансы уроков | Teacher/Student |

---

## 4. T-Bank Integration — СБП + Agent Scheme

### 4.1 Что такое Агентская схема?

Платформа выступает **Агентом** (посредником), который принимает платежи **в пользу Принципала** (преподавателя). Это означает:

1. **Чек содержит данные реального продавца** (ИП преподавателя), а не платформы
2. **Комиссия платформы не облагается НДС** (это агентское вознаграждение)
3. **Преподаватель декларирует доход** как полученный от своих учеников

### 4.2 Receipt Schema для агентской схемы

```python
# Пример структуры чека для T-Bank Init

{
    "Receipt": {
        "Email": "student@example.com",
        "Phone": "+79001234567",
        "EmailCompany": "support@lectiospace.ru",
        "Taxation": "usn_income",  # УСН доходы (для платформы-агента)
        "Items": [
            {
                "Name": "Занятие по математике (10 уроков)",
                "Price": 1000000,  # 10000 ₽ в копейках
                "Quantity": 1,
                "Amount": 1000000,
                "PaymentMethod": "full_prepayment",
                "PaymentObject": "service",
                "Tax": "none",  # Без НДС
                
                # === АГЕНТСКАЯ СХЕМА ===
                "AgentData": {
                    "AgentSign": "another",  # Тип агента: "another" = прочий агент
                    "OperationName": "Репетиторские услуги"
                },
                "SupplierInfo": {
                    "Phones": ["+79009876543"],  # Телефон преподавателя
                    "Name": "ИП Иванов Иван Иванович",  # Название ИП/ООО
                    "Inn": "123456789012"  # ИНН преподавателя
                }
            }
        ]
    }
}
```

### 4.3 Изменения в tbank_service.py

```python
# teaching_panel/accounts/tbank_invoice_service.py

"""
T-Bank invoice payment service for direct teacher-student payments.
Uses SBP (СБП) for lower fees (0.4-0.7%) and Agent scheme for proper taxation.
"""
import hashlib
import requests
import logging
from decimal import Decimal
from datetime import timedelta
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

TBANK_API_URL = 'https://securepay.tinkoff.ru/v2'


class TBankInvoiceService:
    """
    Service for invoice payments via T-Bank SBP (СБП).
    
    Key differences from subscription payments:
    - Uses SBP (QR-code) for lower fees
    - Includes AgentData in Receipt for agent scheme
    - Supports SupplierInfo for teacher's legal entity
    """
    
    @staticmethod
    def create_invoice_payment(invoice, payment_method: str = 'sbp'):
        """
        Create payment for an invoice via SBP or Card.
        
        Args:
            invoice: Invoice model instance
            payment_method: 'sbp' or 'card'
            
        Returns:
            dict: {
                'payment_url': str,
                'payment_id': str,
                'qr_payload': str (for SBP)
            }
        """
        from invoicing.models import InvoicePayment
        
        if not TBankInvoiceService._is_available():
            logger.warning("T-Bank not configured")
            return None
        
        teacher_settings = getattr(invoice.teacher, 'payment_settings', None)
        if not teacher_settings or not teacher_settings.is_verified:
            logger.error(f"Teacher {invoice.teacher.id} payment settings not verified")
            return None
        
        amount_kopecks = int(invoice.remaining_amount * 100)
        
        # Minimum SBP amount is 10 RUB = 1000 kopecks
        if payment_method == 'sbp' and amount_kopecks < 1000:
            logger.error(f"Amount {amount_kopecks} below SBP minimum")
            return None
        
        order_id = f"inv-{invoice.id}-{int(timezone.now().timestamp())}"
        
        # Build Receipt with Agent scheme
        receipt = TBankInvoiceService._build_agent_receipt(
            invoice=invoice,
            teacher_settings=teacher_settings,
            amount_kopecks=amount_kopecks
        )
        
        request_data = {
            'Amount': amount_kopecks,
            'OrderId': order_id,
            'Description': invoice.title[:140],  # Max 140 chars
            'CustomerKey': str(invoice.student.id),
            'SuccessURL': f"{settings.FRONTEND_URL}/invoices/{invoice.public_id}?status=success",
            'FailURL': f"{settings.FRONTEND_URL}/invoices/{invoice.public_id}?status=fail",
            'NotificationURL': f"{settings.SITE_URL}/api/invoicing/webhook/invoice/",
            'PayType': 'O',  # One-stage payment
            'Language': 'ru',
            'Receipt': receipt,
            'DATA': {
                'invoice_id': str(invoice.id),
                'invoice_public_id': str(invoice.public_id),
                'teacher_id': str(invoice.teacher.id),
                'student_id': str(invoice.student.id),
                'payment_method': payment_method,
                'Email': invoice.student.email,
            }
        }
        
        # SBP-specific: QR code lifetime
        if payment_method == 'sbp':
            # QR valid for 15 minutes
            redirect_due_date = timezone.now() + timedelta(minutes=15)
            request_data['RedirectDueDate'] = redirect_due_date.strftime('%Y-%m-%dT%H:%M:%S+03:00')
        
        result = TBankInvoiceService._make_request('Init', request_data)
        
        if result.get('Success'):
            # Create InvoicePayment record
            payment = InvoicePayment.objects.create(
                invoice=invoice,
                amount=invoice.remaining_amount,
                status=InvoicePayment.STATUS_PENDING,
                payment_method=payment_method,
                tbank_payment_id=result['PaymentId'],
                tbank_order_id=order_id,
                metadata={
                    'terminal_key': settings.TBANK_TERMINAL_KEY,
                    'teacher_inn': teacher_settings.inn,
                }
            )
            
            # Update invoice with payment URL
            invoice.payment_url = result['PaymentURL']
            invoice.save(update_fields=['payment_url', 'updated_at'])
            
            logger.info(f"T-Bank invoice payment created: {result['PaymentId']} for invoice {invoice.id}")
            
            return {
                'payment_url': result['PaymentURL'],
                'payment_id': result['PaymentId'],
                'qr_payload': result.get('QRCodeData', ''),  # For SBP
            }
        else:
            logger.error(f"Failed to create invoice payment: {result.get('Message')}")
            return None
    
    @staticmethod
    def _build_agent_receipt(invoice, teacher_settings, amount_kopecks: int) -> dict:
        """
        Build Receipt object with AgentData for agent scheme.
        
        AgentSign values:
        - "bank_paying_agent" — банковский платежный агент
        - "bank_paying_subagent" — банковский платежный субагент
        - "paying_agent" — платежный агент
        - "paying_subagent" — платежный субагент
        - "attorney" — поверенный
        - "commission_agent" — комиссионер
        - "another" — прочий агент (ЭТО НАШ СЛУЧАЙ)
        """
        
        # Get student contact
        student_email = invoice.student.email
        student_phone = invoice.student.phone_number or ''
        
        # Supplier (teacher) info
        supplier_phones = [teacher_settings.phone] if teacher_settings.phone else []
        
        receipt = {
            'Email': student_email,
            'EmailCompany': settings.PLATFORM_SUPPORT_EMAIL,
            'Taxation': 'usn_income',  # УСН доходы (для платформы)
            'Items': []
        }
        
        if student_phone:
            receipt['Phone'] = student_phone
        
        # Build items from invoice
        for item in invoice.items.all():
            item_amount = int(item.total_price * 100)  # kopecks
            
            receipt_item = {
                'Name': item.name[:128],  # Max 128 chars
                'Price': int(item.unit_price * 100),
                'Quantity': item.quantity,
                'Amount': item_amount,
                'PaymentMethod': 'full_prepayment',
                'PaymentObject': 'service',
                'Tax': 'none',  # Без НДС
                
                # === AGENT SCHEME ===
                'AgentData': {
                    'AgentSign': 'another',  # Прочий агент
                    'OperationName': 'Образовательные услуги'
                },
                'SupplierInfo': {
                    'Name': teacher_settings.legal_name,
                    'Inn': teacher_settings.inn,
                }
            }
            
            if supplier_phones:
                receipt_item['SupplierInfo']['Phones'] = supplier_phones
            
            receipt['Items'].append(receipt_item)
        
        # If no items, create single item from invoice
        if not receipt['Items']:
            receipt['Items'].append({
                'Name': invoice.title[:128],
                'Price': amount_kopecks,
                'Quantity': 1,
                'Amount': amount_kopecks,
                'PaymentMethod': 'full_prepayment',
                'PaymentObject': 'service',
                'Tax': 'none',
                'AgentData': {
                    'AgentSign': 'another',
                    'OperationName': 'Образовательные услуги'
                },
                'SupplierInfo': {
                    'Name': teacher_settings.legal_name,
                    'Inn': teacher_settings.inn,
                }
            })
            
            if supplier_phones:
                receipt['Items'][0]['SupplierInfo']['Phones'] = supplier_phones
        
        return receipt
    
    @staticmethod
    def process_invoice_webhook(notification_data: dict) -> bool:
        """
        Process webhook notification for invoice payment.
        """
        from invoicing.models import Invoice, InvoicePayment, LessonBalance
        
        # Verify token
        if not TBankInvoiceService._verify_token(notification_data):
            logger.warning("Invalid invoice webhook token")
            return False
        
        payment_id = str(notification_data.get('PaymentId', ''))
        status = notification_data.get('Status', '')
        
        logger.info(f"Invoice webhook: PaymentId={payment_id}, Status={status}")
        
        try:
            payment = InvoicePayment.objects.select_related(
                'invoice', 
                'invoice__teacher', 
                'invoice__student'
            ).get(tbank_payment_id=payment_id)
        except InvoicePayment.DoesNotExist:
            logger.error(f"InvoicePayment not found: {payment_id}")
            return False
        
        invoice = payment.invoice
        
        if status == 'CONFIRMED':
            payment.status = InvoicePayment.STATUS_SUCCEEDED
            payment.paid_at = timezone.now()
            
            # Calculate fees
            teacher_settings = getattr(invoice.teacher, 'payment_settings', None)
            platform_fee_percent = teacher_settings.platform_fee_percent if teacher_settings else Decimal('5.00')
            acquiring_fee_percent = Decimal('0.7')  # СБП ~0.4-0.7%
            
            payment.platform_fee = payment.amount * platform_fee_percent / 100
            payment.acquiring_fee = payment.amount * acquiring_fee_percent / 100
            payment.teacher_payout = payment.amount - payment.platform_fee - payment.acquiring_fee
            payment.save()
            
            # Update invoice
            invoice.paid_amount += payment.amount
            if invoice.paid_amount >= invoice.amount:
                invoice.status = Invoice.STATUS_PAID
                invoice.paid_at = timezone.now()
            else:
                invoice.status = Invoice.STATUS_PARTIALLY_PAID
            invoice.save()
            
            # Update lesson balance
            if invoice.lessons_count > 0:
                balance, created = LessonBalance.objects.get_or_create(
                    student=invoice.student,
                    teacher=invoice.teacher,
                    group=invoice.group,
                    defaults={'total_lessons': 0, 'used_lessons': 0}
                )
                balance.add_lessons(invoice.lessons_count, invoice)
            
            # Send notifications
            TBankInvoiceService._notify_payment_success(invoice, payment)
            
            return True
        
        elif status in ['REJECTED', 'CANCELED', 'DEADLINE_EXPIRED']:
            payment.status = InvoicePayment.STATUS_FAILED
            payment.metadata['failure_status'] = status
            payment.save()
            
            return True
        
        elif status == 'REFUNDED':
            payment.status = InvoicePayment.STATUS_REFUNDED
            payment.save()
            
            # Update invoice
            invoice.paid_amount -= payment.amount
            invoice.status = Invoice.STATUS_REFUNDED
            invoice.save()
            
            # Refund lesson balance
            if invoice.lessons_count > 0:
                try:
                    balance = LessonBalance.objects.get(
                        student=invoice.student,
                        teacher=invoice.teacher,
                        group=invoice.group
                    )
                    balance.total_lessons -= invoice.lessons_count
                    balance.save()
                except LessonBalance.DoesNotExist:
                    pass
            
            return True
        
        return True
    
    @staticmethod
    def _notify_payment_success(invoice, payment):
        """Send notifications about successful payment."""
        from accounts.notifications import send_telegram_notification
        
        # Notify student
        student_message = (
            f"Оплата прошла успешно!\n"
            f"Счёт: {invoice.title}\n"
            f"Сумма: {payment.amount} ₽\n"
            f"Преподаватель: {invoice.teacher.get_full_name()}"
        )
        if invoice.lessons_count > 0:
            student_message += f"\nДобавлено уроков: {invoice.lessons_count}"
        
        send_telegram_notification(invoice.student, 'payment_success', student_message)
        
        # Notify teacher
        teacher_message = (
            f"Ученик оплатил счёт!\n"
            f"Счёт: {invoice.title}\n"
            f"Ученик: {invoice.student.get_full_name()}\n"
            f"Сумма: {payment.amount} ₽\n"
            f"К выплате: {payment.teacher_payout:.2f} ₽"
        )
        
        send_telegram_notification(invoice.teacher, 'payment_success', teacher_message)
    
    # === Helper methods (same as TBankService) ===
    
    @staticmethod
    def _is_available():
        return bool(getattr(settings, 'TBANK_TERMINAL_KEY', ''))
    
    @staticmethod
    def _generate_token(params: dict) -> str:
        sign_params = {k: v for k, v in params.items() 
                       if not isinstance(v, (dict, list)) and k != 'Token'}
        sign_params['Password'] = settings.TBANK_PASSWORD
        
        sorted_keys = sorted(sign_params.keys())
        values = []
        for k in sorted_keys:
            v = sign_params[k]
            if isinstance(v, bool):
                values.append('true' if v else 'false')
            else:
                values.append(str(v))
        concat_string = ''.join(values)
        
        return hashlib.sha256(concat_string.encode('utf-8')).hexdigest()
    
    @staticmethod
    def _verify_token(notification_data: dict) -> bool:
        received_token = notification_data.get('Token', '')
        if not received_token:
            return False
        expected_token = TBankInvoiceService._generate_token(notification_data)
        return received_token.lower() == expected_token.lower()
    
    @staticmethod
    def _make_request(method: str, data: dict) -> dict:
        url = f"{TBANK_API_URL}/{method}"
        
        data['TerminalKey'] = settings.TBANK_TERMINAL_KEY
        data['Token'] = TBankInvoiceService._generate_token(data)
        
        try:
            response = requests.post(url, json=data, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.exception(f"T-Bank API request failed: {e}")
            return {'Success': False, 'ErrorCode': 'network', 'Message': str(e)}
```

---

## 5. Step-by-Step Implementation Plan

### Phase 1: Database & Models (1-2 дня)

1. **Создать Django app `invoicing`:**
   ```bash
   python manage.py startapp invoicing
   ```

2. **Добавить модели** из раздела 2 в `invoicing/models.py`

3. **Добавить app в INSTALLED_APPS** (`settings.py`)

4. **Создать миграции:**
   ```bash
   python manage.py makemigrations invoicing
   python manage.py migrate
   ```

5. **Зарегистрировать в admin.py** для отладки

### Phase 2: Teacher Payment Settings (1 день)

1. **Создать `TeacherPaymentSettingsViewSet`** — CRUD для настроек

2. **Добавить страницу на Frontend** `/teacher/payment-settings`:
   - Форма ввода ИНН, названия ИП
   - Информация о комиссиях

3. **Валидация ИНН** (чек-сумма для ИП/ООО)

### Phase 3: Invoice CRUD (2-3 дня)

1. **Создать `InvoiceViewSet`:**
   - `create()` — создание счёта (только teacher)
   - `list()` — список счетов (filter by role)
   - `retrieve()` — детали счёта
   - `send()` — отправка ученику (меняет статус + Telegram)
   - `cancel()` — отмена

2. **Создать `InvoiceSerializer`** с вложенными items

3. **Frontend: страница создания счёта** `/teacher/invoices/new`

4. **Frontend: список счетов** `/teacher/invoices`

5. **Frontend: страница счёта** `/invoices/{id}`

### Phase 4: Payment Flow (2-3 дня)

1. **Создать `TBankInvoiceService`** из раздела 4

2. **Создать публичную страницу оплаты** `/pay/{public_id}`:
   - Показывает детали счёта
   - Кнопки "Оплатить картой" / "Оплатить через СБП"
   - QR-код для СБП

3. **Webhook endpoint** `/api/invoicing/webhook/invoice/`

4. **Интеграция с LessonBalance** — начисление уроков после оплаты

### Phase 5: Balance & Lesson Tracking (1-2 дня)

1. **Создать `LessonBalanceViewSet`:**
   - Teacher видит балансы всех учеников
   - Student видит свои балансы

2. **Интеграция с Lesson** — списание баланса при проведении урока:
   ```python
   # schedule/views.py LessonViewSet.start()
   # После успешного старта урока:
   balance = LessonBalance.objects.filter(
       student__in=lesson.group.students.all(),
       teacher=lesson.teacher
   ).first()
   if balance:
       balance.use_lesson(lesson)
   ```

3. **Frontend: виджет баланса** на странице ученика

4. **Frontend: список балансов** для учителя

### Phase 6: Notifications (1 день)

1. **Telegram уведомления:**
   - Ученику: новый счёт, напоминание, оплачено
   - Учителю: счёт оплачен, баланс ученика низкий

2. **Email уведомления** (опционально)

### Phase 7: Testing & Polish (2 дня)

1. **Unit tests** для моделей и сервисов

2. **Integration tests** с mock T-Bank API

3. **E2E тесты** основного flow

4. **Документация API** (Swagger/OpenAPI)

---

## 6. Комиссии и расчёты

### 6.1 Комиссия СБП

| Тип платежа | Комиссия |
|-------------|----------|
| СБП (QR) | 0.4% - 0.7% |
| Карта (Visa/MC) | 1.5% - 2.5% |

### 6.2 Пример расчёта

**Ученик оплачивает 10 уроков = 10,000 ₽**

| Статья | СБП | Карта |
|--------|-----|-------|
| Сумма платежа | 10,000 ₽ | 10,000 ₽ |
| Комиссия эквайринга (0.7% / 2%) | 70 ₽ | 200 ₽ |
| Комиссия платформы (5%) | 500 ₽ | 500 ₽ |
| **К выплате учителю** | **9,430 ₽** | **9,300 ₽** |

### 6.3 Агентская схема — налоговые последствия

1. **Платформа (агент):**
   - Декларирует только агентское вознаграждение (5%)
   - Платит налог с 500 ₽, а не с 10,000 ₽

2. **Преподаватель (принципал):**
   - Декларирует полную сумму услуги (10,000 ₽)
   - В чеке его ИНН и название

3. **Чек для ФНС:**
   - Содержит `AgentSign: another`
   - Содержит `SupplierInfo` с ИНН преподавателя
   - Соответствует ФФД 1.2

---

## 7. Settings Changes

```python
# teaching_panel/teaching_panel/settings.py

# Добавить app
INSTALLED_APPS = [
    ...
    'invoicing',
]

# Добавить настройки
PLATFORM_SUPPORT_EMAIL = 'support@lectiospace.ru'
PLATFORM_FEE_PERCENT = Decimal('5.00')

# T-Bank terminal для invoicing (может быть отдельный)
# Если один терминал — используем TBANK_TERMINAL_KEY
```

---

## 8. Future Enhancements

1. **Автоматическое расщепление платежа (Split)** — деньги сразу на счёт учителя
2. **Recurring invoices** — автопродление подписки на уроки
3. **Шаблоны счетов** — быстрое создание типовых счетов
4. **Аналитика** — статистика по счетам и выплатам
5. **Выплаты** — интеграция с банковским API для автовыплат

---

## 9. Files to Create/Modify

### New Files:
- `teaching_panel/invoicing/__init__.py`
- `teaching_panel/invoicing/models.py`
- `teaching_panel/invoicing/views.py`
- `teaching_panel/invoicing/serializers.py`
- `teaching_panel/invoicing/urls.py`
- `teaching_panel/invoicing/admin.py`
- `teaching_panel/invoicing/tbank_invoice_service.py`
- `frontend/src/components/InvoicesPage.js`
- `frontend/src/components/CreateInvoicePage.js`
- `frontend/src/components/PaymentPage.js`
- `frontend/src/components/TeacherPaymentSettingsPage.js`
- `frontend/src/components/LessonBalanceWidget.js`

### Modified Files:
- `teaching_panel/teaching_panel/settings.py` — add app
- `teaching_panel/teaching_panel/urls.py` — add routes
- `frontend/src/App.js` — add routes
- `frontend/src/apiService.js` — add API methods
- `teaching_panel/schedule/views.py` — integrate balance check

---

*Document created: 2026-02-03*
*Author: GitHub Copilot (Claude Opus 4.5)*
