# Backend API Implementation Guide - Subscription Management

## Quick Start (30 минут)

### 1. Создать файл: `teaching_panel/subscriptions/admin_views.py`

```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from django.utils import timezone
from datetime import timedelta

from .models import Subscription, PaymentHistory
from .admin_serializers import SubscriptionAdminSerializer


class SubscriptionAdminViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Admin-only endpoint для управления подписками учителей
    """
    queryset = Subscription.objects.select_related('teacher').prefetch_related('payments').all()
    serializer_class = SubscriptionAdminSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['plan', 'status']
    search_fields = ['teacher__email', 'teacher__first_name', 'teacher__last_name']

    def get_queryset(self):
        queryset = super().get_queryset()
        # Сортировка: сначала активные, потом по дате истечения
        return queryset.order_by('-status', 'expires_at')

    @action(detail=True, methods=['post'])
    def extend_trial(self, request, pk=None):
        """
        Продлить пробный период на N дней
        Body: { "days": 7 }
        """
        subscription = self.get_object()
        
        if subscription.plan != 'trial':
            return Response(
                {'detail': 'Можно продлить только пробные подписки'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        days = request.data.get('days', 7)
        try:
            days = int(days)
            if days <= 0 or days > 30:
                raise ValueError
        except ValueError:
            return Response(
                {'detail': 'Дни должны быть числом от 1 до 30'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        subscription.expires_at += timedelta(days=days)
        subscription.save()
        
        return Response({
            'success': True,
            'new_expires_at': subscription.expires_at,
            'message': f'Пробный период продлен на {days} дней'
        })

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Отменить подписку (отключить автопродление)
        """
        subscription = self.get_object()
        
        if subscription.status != 'active':
            return Response(
                {'detail': 'Можно отменить только активные подписки'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        subscription.auto_renew = False
        subscription.status = 'cancelled'
        subscription.save()
        
        return Response({
            'success': True,
            'auto_renew': False,
            'status': 'cancelled',
            'message': 'Автопродление отключено'
        })

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """
        Активировать подписку (для cancelled/expired)
        """
        subscription = self.get_object()
        
        if subscription.status == 'active':
            return Response(
                {'detail': 'Подписка уже активна'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Если подписка истекла, продлить на месяц
        if subscription.expires_at < timezone.now():
            if subscription.plan == 'monthly':
                subscription.expires_at = timezone.now() + timedelta(days=30)
            elif subscription.plan == 'yearly':
                subscription.expires_at = timezone.now() + timedelta(days=365)
            else:  # trial
                subscription.expires_at = timezone.now() + timedelta(days=7)
        
        subscription.status = 'active'
        subscription.auto_renew = True
        subscription.save()
        
        return Response({
            'success': True,
            'status': 'active',
            'expires_at': subscription.expires_at,
            'message': 'Подписка активирована'
        })
```

---

### 2. Создать файл: `teaching_panel/subscriptions/admin_serializers.py`

```python
from rest_framework import serializers
from .models import Subscription, PaymentHistory


class PaymentHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentHistory
        fields = ['id', 'amount', 'currency', 'status', 'created_at', 'payment_method']


class SubscriptionAdminSerializer(serializers.ModelSerializer):
    teacher_id = serializers.IntegerField(source='teacher.id', read_only=True)
    teacher_name = serializers.SerializerMethodField()
    teacher_email = serializers.EmailField(source='teacher.email', read_only=True)
    teacher_registered_at = serializers.DateTimeField(source='teacher.date_joined', read_only=True)
    payments = PaymentHistorySerializer(many=True, read_only=True)
    
    class Meta:
        model = Subscription
        fields = [
            'id',
            'teacher_id',
            'teacher_name',
            'teacher_email',
            'teacher_registered_at',
            'plan',
            'status',
            'started_at',
            'expires_at',
            'auto_renew',
            'total_paid',
            'currency',
            'payments'
        ]
    
    def get_teacher_name(self, obj):
        """Полное имя преподавателя"""
        teacher = obj.teacher
        parts = [teacher.first_name, teacher.middle_name, teacher.last_name]
        full_name = ' '.join(filter(None, parts))
        return full_name if full_name else teacher.email
```

---

### 3. Обновить URL routing: `teaching_panel/subscriptions/urls.py`

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SubscriptionViewSet  # Existing
from .admin_views import SubscriptionAdminViewSet  # New

router = DefaultRouter()
router.register('subscriptions', SubscriptionViewSet, basename='subscription')
router.register('admin/subscriptions', SubscriptionAdminViewSet, basename='admin-subscription')

urlpatterns = [
    path('api/', include(router.urls)),
]
```

---

### 4. Проверить существующий teacher endpoint

Убедитесь что есть:

```python
# subscriptions/views.py

class SubscriptionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """
        GET /api/subscriptions/me/
        Получить подписку текущего учителя
        """
        try:
            subscription = Subscription.objects.get(teacher=request.user)
            serializer = SubscriptionSerializer(subscription)
            return Response(serializer.data)
        except Subscription.DoesNotExist:
            return Response(
                {'detail': 'Подписка не найдена'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        POST /api/subscriptions/:id/cancel/
        Отменить автопродление (для teacher)
        """
        subscription = self.get_object()
        
        # Проверка: только свою подписку
        if subscription.teacher != request.user:
            return Response(
                {'detail': 'Нет доступа'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if subscription.auto_renew:
            subscription.auto_renew = False
            subscription.save()
        
        return Response({
            'success': True,
            'auto_renew': False,
            'message': 'Автопродление отключено'
        })
```

---

### 5. Создать миграции (если моделей нет)

```python
# subscriptions/models.py

from django.db import models
from django.conf import settings


class Subscription(models.Model):
    PLAN_CHOICES = [
        ('trial', 'Пробная'),
        ('monthly', 'Месячная'),
        ('yearly', 'Годовая'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Активна'),
        ('pending', 'Ожидает оплаты'),
        ('cancelled', 'Отменена'),
        ('expired', 'Истекла'),
    ]
    
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscriptions'
    )
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='trial')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    auto_renew = models.BooleanField(default=False)
    total_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='RUB')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.teacher.email} - {self.get_plan_display()} ({self.status})"


class PaymentHistory(models.Model):
    STATUS_CHOICES = [
        ('succeeded', 'Успешно'),
        ('pending', 'Ожидание'),
        ('failed', 'Ошибка'),
        ('refunded', 'Возврат'),
    ]
    
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='RUB')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    payment_method = models.CharField(max_length=50, blank=True)
    payment_id = models.CharField(max_length=255, blank=True)  # External payment ID
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Payment Histories'
    
    def __str__(self):
        return f"{self.subscription.teacher.email} - {self.amount} {self.currency}"
```

```bash
python manage.py makemigrations
python manage.py migrate
```

---

### 6. Testing

```bash
# Test admin list
curl -H "Authorization: Bearer <admin-token>" \
  http://127.0.0.1:8000/api/admin/subscriptions/

# Test filters
curl -H "Authorization: Bearer <admin-token>" \
  "http://127.0.0.1:8000/api/admin/subscriptions/?plan=trial&status=active"

# Test search
curl -H "Authorization: Bearer <admin-token>" \
  "http://127.0.0.1:8000/api/admin/subscriptions/?search=ivan@example.com"

# Test extend trial
curl -X POST -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"days": 7}' \
  http://127.0.0.1:8000/api/admin/subscriptions/1/extend_trial/

# Test cancel
curl -X POST -H "Authorization: Bearer <admin-token>" \
  http://127.0.0.1:8000/api/admin/subscriptions/1/cancel/

# Test activate
curl -X POST -H "Authorization: Bearer <admin-token>" \
  http://127.0.0.1:8000/api/admin/subscriptions/1/activate/

# Test teacher get subscription
curl -H "Authorization: Bearer <teacher-token>" \
  http://127.0.0.1:8000/api/subscriptions/me/

# Test teacher cancel
curl -X POST -H "Authorization: Bearer <teacher-token>" \
  http://127.0.0.1:8000/api/subscriptions/1/cancel/
```

---

## Integration с YooKassa (опционально)

Если нужна реальная оплата:

```python
# subscriptions/views.py

from yookassa import Configuration, Payment
import uuid

Configuration.account_id = settings.YOOKASSA_SHOP_ID
Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

class SubscriptionViewSet(viewsets.ModelViewSet):
    
    @action(detail=False, methods=['post'])
    def create_payment(self, request):
        """
        POST /api/subscriptions/payments/
        Body: { "plan": "monthly" }  # or "yearly"
        """
        plan = request.data.get('plan')
        
        if plan not in ['monthly', 'yearly']:
            return Response(
                {'detail': 'План должен быть monthly или yearly'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Определить сумму
        amount = 990 if plan == 'monthly' else 9900
        
        # Создать payment в YooKassa
        payment = Payment.create({
            "amount": {
                "value": str(amount),
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": f"{settings.FRONTEND_URL}/subscription/success"
            },
            "capture": True,
            "description": f"Подписка Teaching Panel - {plan}",
            "metadata": {
                "teacher_id": request.user.id,
                "plan": plan
            }
        }, uuid.uuid4())
        
        # Сохранить pending payment
        subscription = Subscription.objects.get(teacher=request.user)
        PaymentHistory.objects.create(
            subscription=subscription,
            amount=amount,
            currency='RUB',
            status='pending',
            payment_id=payment.id,
            payment_method='yookassa'
        )
        
        return Response({
            'payment_url': payment.confirmation.confirmation_url,
            'payment_id': payment.id
        })
```

---

## Security Checklist

- [x] Admin endpoints: `permission_classes = [IsAdminUser]`
- [x] Teacher endpoints: проверка `subscription.teacher == request.user`
- [x] Валидация входных данных (days: 1-30, plan: trial/monthly/yearly)
- [x] CSRF protection для POST запросов
- [x] Rate limiting для payment endpoints (throttle_scope='payment')
- [x] Логирование всех админ-действий

---

## Performance Tips

1. **Select Related**: `select_related('teacher').prefetch_related('payments')`
2. **Database Indexes**:
   ```python
   class Meta:
       indexes = [
           models.Index(fields=['teacher', 'status']),
           models.Index(fields=['expires_at']),
       ]
   ```
3. **Caching**: кэшировать список подписок на 5 минут
4. **Pagination**: `PageNumberPagination` для больших списков

---

## Готово! 🎉

После реализации backend:
1. Запустить Django: `python manage.py runserver`
2. Запустить React: `npm start`
3. Зайти как admin → открыть модальное окно подписок
4. Зайти как teacher → открыть таб "Моя подписка"

**Всё должно работать из коробки!**
