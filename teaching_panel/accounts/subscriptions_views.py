from uuid import uuid4

from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from .models import Subscription, Payment
from .serializers import SubscriptionSerializer, PaymentSerializer


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
        sub = _get_or_create_subscription(request.user)
        data = SubscriptionSerializer(sub).data
        return Response(data)


class SubscriptionCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        sub = _get_or_create_subscription(request.user)
        if sub.status == Subscription.STATUS_CANCELLED:
            return Response({'detail': 'Подписка уже отменена'}, status=status.HTTP_200_OK)
        sub.status = Subscription.STATUS_CANCELLED
        sub.cancelled_at = timezone.now()
        sub.auto_renew = False
        sub.save(update_fields=['status', 'cancelled_at', 'auto_renew', 'updated_at'])
        return Response(SubscriptionSerializer(sub).data)


class SubscriptionCreatePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    PRICES = {
        Subscription.PLAN_MONTHLY: ('990.00', 'RUB'),
        Subscription.PLAN_YEARLY: ('9900.00', 'RUB'),
    }

    def post(self, request):
        plan = str(request.data.get('plan', '')).lower().strip()
        if plan not in (Subscription.PLAN_MONTHLY, Subscription.PLAN_YEARLY):
            return Response({'detail': 'Укажите план: monthly или yearly'}, status=status.HTTP_400_BAD_REQUEST)

        sub = _get_or_create_subscription(request.user)
        amount_str, currency = self.PRICES[plan]

        # Переводим подписку в ожидающую оплаты выбранного плана
        sub.plan = plan
        sub.status = Subscription.STATUS_PENDING
        sub.payment_method = 'yookassa'
        sub.save(update_fields=['plan', 'status', 'payment_method', 'updated_at'])

        payment_id = str(uuid4())
        payment = Payment.objects.create(
            subscription=sub,
            amount=amount_str,
            currency=currency,
            status=Payment.STATUS_PENDING,
            payment_system='yookassa',
            payment_id=payment_id,
            payment_url=f'https://checkout.yookassa.ru/payments/{payment_id}',
            metadata={'plan': plan},
        )

        return Response({
            'subscription': SubscriptionSerializer(sub).data,
            'payment': PaymentSerializer(payment).data,
        }, status=status.HTTP_201_CREATED)
