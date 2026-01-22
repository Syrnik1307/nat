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
from .tbank_service import TBankService
from .models import Payment
from django.conf import settings
from django.db.models import Count


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

        # Выбор платёжного провайдера: tbank или yookassa (по умолчанию)
        provider = str(request.data.get('provider', '')).lower().strip()
        if not provider:
            provider = getattr(settings, 'DEFAULT_PAYMENT_PROVIDER', 'yookassa')
        
        if provider not in ('yookassa', 'tbank'):
            return Response({'detail': 'Неизвестный провайдер: yookassa или tbank'}, status=status.HTTP_400_BAD_REQUEST)

        sub = get_subscription(request.user)

        # Переводим подписку в ожидающую оплаты выбранного плана
        sub.plan = plan
        sub.status = Subscription.STATUS_PENDING
        sub.save(update_fields=['plan', 'status', 'updated_at'])

        # Создаём платёж через выбранный провайдер
        if provider == 'tbank':
            payment_result = TBankService.create_subscription_payment(sub, plan)
        else:
            payment_result = PaymentService.create_subscription_payment(sub, plan)
        
        if not payment_result:
            return Response({'detail': 'Не удалось создать платёж'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Возвращаем URL для оплаты
        payment = Payment.objects.get(payment_id=payment_result['payment_id'])
        
        return Response({
            'subscription': SubscriptionSerializer(sub).data,
            'payment': PaymentSerializer(payment).data,
            'payment_url': payment_result['payment_url'],
            'provider': provider,
        }, status=status.HTTP_201_CREATED)


class SubscriptionAddStorageView(APIView):
    """Запрос на покупку дополнительного объема хранилища (GB).

    POST body: { "gb": 10, "provider": "tbank" } // provider опционально
    Создает Payment через YooKassa или T-Bank.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            gb = int(request.data.get('gb', 0))
        except (TypeError, ValueError):
            gb = 0
        if gb <= 0 or gb > 1000:
            return Response({'detail': 'Некорректное значение GB (1..1000)'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Выбор платёжного провайдера
        provider = str(request.data.get('provider', '')).lower().strip()
        if not provider:
            provider = getattr(settings, 'DEFAULT_PAYMENT_PROVIDER', 'yookassa')
        
        sub = get_subscription(request.user)
        
        # Создаём платёж через выбранный провайдер
        if provider == 'tbank':
            payment_result = TBankService.create_storage_payment(sub, gb)
        else:
            payment_result = PaymentService.create_storage_payment(sub, gb)
        
        if not payment_result:
            return Response({'detail': 'Не удалось создать платёж'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        payment = Payment.objects.get(payment_id=payment_result['payment_id'])
        
        return Response({
            'payment': PaymentSerializer(payment).data,
            'subscription': SubscriptionSerializer(sub).data,
            'payment_url': payment_result['payment_url'],
            'provider': provider,
        }, status=status.HTTP_201_CREATED)


class SubscriptionCreateZoomAddonPaymentView(APIView):
    """Создать платёж за Zoom-аддон (990 ₽ / 28 дней)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        provider = str(request.data.get('provider', '')).lower().strip()
        if not provider:
            provider = getattr(settings, 'DEFAULT_PAYMENT_PROVIDER', 'yookassa')

        if provider not in ('yookassa', 'tbank'):
            return Response({'detail': 'Неизвестный провайдер: yookassa или tbank'}, status=status.HTTP_400_BAD_REQUEST)

        sub = get_subscription(request.user)

        if provider == 'tbank':
            payment_result = TBankService.create_zoom_addon_payment(sub)
        else:
            payment_result = PaymentService.create_zoom_addon_payment(sub)

        if not payment_result:
            return Response({'detail': 'Не удалось создать платёж'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        payment = Payment.objects.get(payment_id=payment_result['payment_id'])

        return Response({
            'payment': PaymentSerializer(payment).data,
            'subscription': SubscriptionSerializer(sub).data,
            'payment_url': payment_result['payment_url'],
            'provider': provider,
        }, status=status.HTTP_201_CREATED)


class SubscriptionZoomAddonSetupView(APIView):
    """Настройка Zoom после оплаты Zoom-аддона.

    POST /api/subscription/zoom/setup/
    body:
      {"mode": "pool"}  -> выделить учителю аккаунт платформы (preferred_teachers)
      {"mode": "personal", "accountId": "...", "clientId": "...", "clientSecret": "...", "userId": "me"}
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != 'teacher':
            return Response({'detail': 'Только для учителей'}, status=status.HTTP_403_FORBIDDEN)

        sub = get_subscription(request.user)
        if not getattr(sub, 'is_zoom_addon_active', None) or not sub.is_zoom_addon_active():
            return Response({'detail': 'Zoom-подписка не активна'}, status=status.HTTP_403_FORBIDDEN)

        mode = str(request.data.get('mode', '')).lower().strip()
        if mode not in ('pool', 'personal'):
            return Response({'detail': 'mode: pool или personal'}, status=status.HTTP_400_BAD_REQUEST)

        if mode == 'personal':
            account_id = str(request.data.get('accountId', '')).strip()
            client_id = str(request.data.get('clientId', '')).strip()
            client_secret = str(request.data.get('clientSecret', '')).strip()
            user_id = str(request.data.get('userId', '')).strip() or 'me'

            if not (account_id and client_id and client_secret):
                return Response({'detail': 'Заполните Account ID, Client ID и Client Secret'}, status=status.HTTP_400_BAD_REQUEST)

            request.user.zoom_account_id = account_id
            request.user.zoom_client_id = client_id
            request.user.zoom_client_secret = client_secret
            request.user.zoom_user_id = user_id
            request.user.save(update_fields=['zoom_account_id', 'zoom_client_id', 'zoom_client_secret', 'zoom_user_id', 'updated_at'])

            return Response({
                'ok': True,
                'mode': 'personal',
                'subscription': SubscriptionSerializer(sub).data,
            })

        # mode == pool
        try:
            from zoom_pool.models import ZoomAccount
        except Exception:
            return Response({'detail': 'Zoom pool не доступен'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Выбираем аккаунт платформы с минимальной "нагрузкой" по предпочтениям.
        # Это не создаёт новый Zoom аккаунт в Zoom, а назначает выделенный из пула.
        account = (
            ZoomAccount.objects.filter(is_active=True)
            .annotate(preferred_count=Count('preferred_teachers'))
            .order_by('preferred_count', 'current_meetings', '-last_used_at')
            .first()
        )
        if not account:
            return Response({'detail': 'Нет доступных Zoom аккаунтов в пуле'}, status=status.HTTP_409_CONFLICT)

        account.preferred_teachers.add(request.user)
        return Response({
            'ok': True,
            'mode': 'pool',
            'assigned_zoom_email': account.email,
            'subscription': SubscriptionSerializer(sub).data,
        })


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


class SubscriptionStorageView(APIView):
    """Получить статистику использования хранилища для текущего учителя.
    
    GET /api/subscription/storage/
    
    Ответ: {
        'used_gb': float,
        'limit_gb': int,
        'available_gb': float,
        'usage_percent': float,
        'file_count': int,
        'gdrive_folder_link': str or None
    }
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'teacher':
            return Response({'detail': 'Только для учителей'}, status=status.HTTP_403_FORBIDDEN)
        
        sub = get_subscription(request.user)
        
        try:
            from .gdrive_folder_service import get_teacher_storage_usage, get_teacher_folder_link
            storage_stats = get_teacher_storage_usage(sub)
            storage_stats['gdrive_folder_link'] = get_teacher_folder_link(sub)
        except Exception as e:
            storage_stats = {
                'used_gb': float(sub.used_storage_gb),
                'limit_gb': sub.total_storage_gb,
                'available_gb': float(sub.total_storage_gb - sub.used_storage_gb),
                'usage_percent': float(sub.used_storage_gb / sub.total_storage_gb * 100) if sub.total_storage_gb > 0 else 0,
                'file_count': 0,
                'gdrive_folder_link': None,
                'error': str(e)
            }
        
        return Response(storage_stats)


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


class SyncPendingPaymentsView(APIView):
    """
    Sync pending T-Bank payments by checking their status via API.
    Can be called by frontend when user returns from payment page,
    or periodically by admin/cron.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Only sync payments for current user (unless admin)
        user = request.user
        
        if getattr(user, 'role', None) == 'admin' or user.is_staff:
            # Admin can sync all
            result = TBankService.sync_pending_payments()
        else:
            # Regular user - sync only their pending payments
            result = self._sync_user_payments(user)
        
        return Response(result)
    
    def _sync_user_payments(self, user):
        """Sync only pending payments for a specific user."""
        from .models import Payment
        
        try:
            sub = user.subscription
        except Subscription.DoesNotExist:
            return {'processed': 0, 'failed': 0, 'errors': []}
        
        pending = Payment.objects.filter(
            subscription=sub,
            status=Payment.STATUS_PENDING,
            payment_system='tbank'
        ).order_by('-id')[:10]
        
        processed = 0
        failed = 0
        
        for payment in pending:
            try:
                status_result = TBankService.check_payment_status(payment.payment_id)
                
                if not status_result.get('success'):
                    continue
                
                tbank_status = status_result.get('status')
                
                if tbank_status == 'CONFIRMED':
                    metadata = payment.metadata or {}
                    
                    payment.status = Payment.STATUS_SUCCEEDED
                    payment.paid_at = timezone.now()
                    payment.save()
                    
                    # Activate subscription
                    if 'plan' in metadata:
                        plan = metadata['plan']
                        if plan == 'monthly':
                            sub.expires_at = timezone.now() + timezone.timedelta(days=28)
                            sub.plan = Subscription.PLAN_MONTHLY
                            sub.base_storage_gb = 10
                        
                        sub.status = Subscription.STATUS_ACTIVE
                        sub.total_paid += payment.amount
                        sub.last_payment_date = timezone.now()
                        sub.payment_method = 'tbank'
                        sub.save()
                        
                        # Create GDrive folder on first payment
                        if not sub.gdrive_folder_id:
                            try:
                                from .gdrive_folder_service import create_teacher_folder_on_subscription
                                create_teacher_folder_on_subscription(sub)
                            except Exception:
                                pass
                    
                    # Add storage
                    elif 'storage_gb' in metadata:
                        gb = int(metadata['storage_gb'])
                        sub.extra_storage_gb += gb
                        sub.total_paid += payment.amount
                        sub.last_payment_date = timezone.now()
                        sub.save()

                    # Zoom add-on
                    elif metadata.get('zoom_addon'):
                        sub.zoom_addon_expires_at = timezone.now() + timezone.timedelta(days=28)
                        sub.total_paid += payment.amount
                        sub.last_payment_date = timezone.now()
                        sub.save(update_fields=['zoom_addon_expires_at', 'total_paid', 'last_payment_date', 'updated_at'])
                    
                    processed += 1
                    
                elif tbank_status in ('REJECTED', 'CANCELED', 'REFUNDED', 'DEADLINE_EXPIRED'):
                    payment.status = Payment.STATUS_FAILED
                    payment.save()
                    failed += 1
                    
            except Exception:
                pass
        
        return {'processed': processed, 'failed': failed, 'errors': []}

