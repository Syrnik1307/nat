from uuid import uuid4
from decimal import Decimal

from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from .models import Subscription, Payment
from .subscriptions_utils import get_subscription, require_active_subscription
from .serializers import SubscriptionSerializer, PaymentSerializer
from .payments_service import PaymentService
from .models import Payment


def _get_or_create_subscription(user: "Subscription.user") -> Subscription:
    sub = getattr(user, 'subscription', None)
    if sub:
        return sub
    # Создаем пробную подписку на 7 дней, активную сразу
    now = timezone.now()
    sub = Subscription.objects.create(
        user=user,
        plan=Subscription.PLAN_TRIAL,
        status=Subscription.STATUS_ACTIVE,
        expires_at=now + timezone.timedelta(days=7),
        auto_renew=False,
    )
    return sub


class SubscriptionMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sub = get_subscription(request.user)
        data = SubscriptionSerializer(sub).data
        return Response(data)


class SubscriptionCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        sub = get_subscription(request.user)
        if sub.status == Subscription.STATUS_CANCELLED:
            return Response({'detail': 'Подписка уже отменена'}, status=status.HTTP_200_OK)
        sub.status = Subscription.STATUS_CANCELLED
        sub.cancelled_at = timezone.now()
        sub.auto_renew = False
        sub.save(update_fields=['status', 'cancelled_at', 'auto_renew', 'updated_at'])
        return Response(SubscriptionSerializer(sub).data)


class SubscriptionEnableAutoRenewView(APIView):
    """Включает автопродление подписки (auto_renew=True).

    Если подписка была отменена (STATUS_CANCELLED) но срок ещё не истёк — просто включаем флаг.
    Если срок истёк или статус EXPIRED — активируем на 30 дней от текущего момента.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        sub = get_subscription(request.user)
        if sub.auto_renew:
            return Response(SubscriptionSerializer(sub).data)
        now = timezone.now()
        # Если истекла или отменена и истекла — активируем заново на 30 дней
        if sub.expires_at and sub.expires_at < now:
            sub.expires_at = now + timezone.timedelta(days=30)
        if sub.status in (Subscription.STATUS_CANCELLED, Subscription.STATUS_EXPIRED):
            sub.status = Subscription.STATUS_ACTIVE
        sub.auto_renew = True
        sub.save(update_fields=['auto_renew', 'expires_at', 'status', 'updated_at'])
        return Response(SubscriptionSerializer(sub).data)


class SubscriptionPaymentStatusView(APIView):
    """Возвращает статус конкретного платежа и актуальные данные подписки.

    GET /api/subscription/payment-status/<payment_id>/

    Ответ:
    {
      "payment": {"payment_id": str, "status": str},
      "subscription": {...}
    }
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, payment_id: str):
        try:
            payment = Payment.objects.select_related('subscription').get(payment_id=payment_id)
        except Payment.DoesNotExist:
            return Response({'detail': 'Платёж не найден'}, status=status.HTTP_404_NOT_FOUND)

        # Проверяем что платёж принадлежит текущему пользователю
        if payment.subscription.user_id != request.user.id:
            return Response({'detail': 'Недоступно'}, status=status.HTTP_403_FORBIDDEN)

        return Response({
            'payment': {
                'payment_id': payment.payment_id,
                'status': payment.status,
                'paid_at': payment.paid_at,
            },
            'subscription': SubscriptionSerializer(payment.subscription).data,
        })


class SubscriptionCreatePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        plan = str(request.data.get('plan', '')).lower().strip()
        if plan not in (Subscription.PLAN_MONTHLY, Subscription.PLAN_YEARLY):
            return Response({'detail': 'Укажите план: monthly или yearly'}, status=status.HTTP_400_BAD_REQUEST)

        sub = get_subscription(request.user)

        # Переводим подписку в ожидающую оплаты выбранного плана
        sub.plan = plan
        sub.status = Subscription.STATUS_PENDING
        sub.save(update_fields=['plan', 'status', 'updated_at'])

        # Создаём платёж через YooKassa
        payment_result = PaymentService.create_subscription_payment(sub, plan)
        
        if not payment_result:
            return Response({'detail': 'Не удалось создать платёж'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Возвращаем URL для оплаты
        payment = Payment.objects.get(payment_id=payment_result['payment_id'])
        
        return Response({
            'subscription': SubscriptionSerializer(sub).data,
            'payment': PaymentSerializer(payment).data,
            'payment_url': payment_result['payment_url']
        }, status=status.HTTP_201_CREATED)


class SubscriptionAddStorageView(APIView):
    """Запрос на покупку дополнительного объема хранилища (GB).

    POST body: { "gb": 10 }
    Создает Payment через YooKassa.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            gb = int(request.data.get('gb', 0))
        except (TypeError, ValueError):
            gb = 0
        if gb <= 0 or gb > 1000:
            return Response({'detail': 'Некорректное значение GB (1..1000)'}, status=status.HTTP_400_BAD_REQUEST)
        
        sub = get_subscription(request.user)
        
        # Создаём платёж через YooKassa
        payment_result = PaymentService.create_storage_payment(sub, gb)
        
        if not payment_result:
            return Response({'detail': 'Не удалось создать платёж'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        payment = Payment.objects.get(payment_id=payment_result['payment_id'])
        
        return Response({
            'payment': PaymentSerializer(payment).data,
            'subscription': SubscriptionSerializer(sub).data,
            'payment_url': payment_result['payment_url']
        }, status=status.HTTP_201_CREATED)


class AdminSubscriptionConfirmStoragePaymentView(APIView):
    """Админ подтверждает оплату за дополнительное хранилище и применяет объем."""
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, payment_id):
        try:
            payment = Payment.objects.select_related('subscription').get(payment_id=payment_id)
        except Payment.DoesNotExist:
            return Response({'detail': 'Платеж не найден'}, status=status.HTTP_404_NOT_FOUND)
        if payment.status != Payment.STATUS_PENDING:
            return Response({'detail': 'Платеж уже обработан'}, status=status.HTTP_400_BAD_REQUEST)
        gb = int(payment.metadata.get('storage_gb', 0))
        sub = payment.subscription
        sub.add_storage(gb)
        # обновляем платеж
        payment.status = Payment.STATUS_SUCCEEDED
        payment.paid_at = timezone.now()
        payment.save(update_fields=['status', 'paid_at'])
        # обновляем агрегаты подписки
        sub.total_paid += payment.amount
        sub.last_payment_date = payment.paid_at
        if not sub.is_active() and sub.status in (Subscription.STATUS_PENDING, Subscription.STATUS_CANCELLED, Subscription.STATUS_EXPIRED):
            sub.status = Subscription.STATUS_ACTIVE
            # продлеваем на 30 дней если истекла
            if sub.expires_at < timezone.now():
                sub.expires_at = timezone.now() + timezone.timedelta(days=30)
        sub.save(update_fields=['extra_storage_gb', 'total_paid', 'last_payment_date', 'status', 'expires_at', 'updated_at'])
        return Response({
            'subscription': SubscriptionSerializer(sub).data,
            'payment': PaymentSerializer(payment).data,
        })


class AdminSubscriptionsListView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        qs = Subscription.objects.select_related('user').all().order_by('-updated_at')
        search = str(request.query_params.get('search', '')).strip().lower()
        plan = str(request.query_params.get('plan', '')).strip().lower()
        status_q = str(request.query_params.get('status', '')).strip().lower()

        if search:
            qs = qs.filter(
                user__email__icontains=search
            ) | qs.filter(user__first_name__icontains=search) | qs.filter(user__last_name__icontains=search)

        if plan in (Subscription.PLAN_TRIAL, Subscription.PLAN_MONTHLY, Subscription.PLAN_YEARLY):
            qs = qs.filter(plan=plan)

        if status_q in (Subscription.STATUS_ACTIVE, Subscription.STATUS_PENDING, Subscription.STATUS_CANCELLED, Subscription.STATUS_EXPIRED):
            qs = qs.filter(status=status_q)

        data = SubscriptionSerializer(qs, many=True).data
        return Response({'results': data})


class AdminSubscriptionExtendTrialView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, sub_id):
        try:
            sub = Subscription.objects.get(id=sub_id)
        except Subscription.DoesNotExist:
            return Response({'detail': 'Подписка не найдена'}, status=status.HTTP_404_NOT_FOUND)

        if sub.plan != Subscription.PLAN_TRIAL:
            return Response({'detail': 'Продление доступно только для пробной подписки'}, status=status.HTTP_400_BAD_REQUEST)

        sub.expires_at = (sub.expires_at or timezone.now()) + timezone.timedelta(days=7)
        sub.save(update_fields=['expires_at', 'updated_at'])
        return Response(SubscriptionSerializer(sub).data)


class AdminSubscriptionCancelView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, sub_id):
        try:
            sub = Subscription.objects.get(id=sub_id)
        except Subscription.DoesNotExist:
            return Response({'detail': 'Подписка не найдена'}, status=status.HTTP_404_NOT_FOUND)

        sub.status = Subscription.STATUS_CANCELLED
        sub.cancelled_at = timezone.now()
        sub.auto_renew = False
        sub.save(update_fields=['status', 'cancelled_at', 'auto_renew', 'updated_at'])
        return Response(SubscriptionSerializer(sub).data)


class AdminSubscriptionActivateView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, sub_id):
        try:
            sub = Subscription.objects.get(id=sub_id)
        except Subscription.DoesNotExist:
            return Response({'detail': 'Подписка не найдена'}, status=status.HTTP_404_NOT_FOUND)

        now = timezone.now()
        sub.status = Subscription.STATUS_ACTIVE
        if not sub.expires_at or sub.expires_at < now:
            # Активируем на 30 дней если срок истёк или отсутствует
            sub.expires_at = now + timezone.timedelta(days=30)
        sub.save(update_fields=['status', 'expires_at', 'updated_at'])
        return Response(SubscriptionSerializer(sub).data)
