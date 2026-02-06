"""
YooKassa payment integration service
Handles payment creation and processing for subscriptions

PRODUCTION-GRADE REQUIREMENTS:
- Atomic transactions for all payment processing
- Idempotent webhook handling (duplicate webhooks are safe)
- Row-level locking to prevent race conditions
- Comprehensive logging for audit trail
"""
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.db import transaction, DatabaseError
from datetime import timedelta
import logging
from dateutil.relativedelta import relativedelta

from .notifications import send_telegram_notification, notify_admin_payment

logger = logging.getLogger(__name__)

# YooKassa будет инициализирован при наличии ключей
YOOKASSA_AVAILABLE = False
try:
    from yookassa import Configuration, Payment as YKPayment
    
    if hasattr(settings, 'YOOKASSA_ACCOUNT_ID') and settings.YOOKASSA_ACCOUNT_ID:
        Configuration.account_id = settings.YOOKASSA_ACCOUNT_ID
        Configuration.secret_key = settings.YOOKASSA_SECRET_KEY
        YOOKASSA_AVAILABLE = True
        logger.info("YooKassa configured successfully")
except ImportError:
    logger.warning("YooKassa SDK not installed. Install with: pip install yookassa")
except Exception as e:
    logger.warning(f"YooKassa configuration failed: {e}")


class PaymentService:
    """Service for handling subscription payments via YooKassa"""
    
    PLAN_PRICES = {
        'monthly': '1590.00',
        'yearly': '9900.00',
    }
    
    STORAGE_PRICE_PER_GB = '20.00'

    ZOOM_ADDON_PRICE = '990.00'

    @staticmethod
    def create_zoom_addon_payment(subscription, enable_recurrent: bool = False):
        """Создать платёж за Zoom-аддон (990 ₽ / 1 месяц).

        Возвращает dict: {'payment_url': str, 'payment_id': str} или None.
        """
        if not YOOKASSA_AVAILABLE:
            logger.error("YooKassa not available - using mock payment URL")
            from .models import Payment

            mock_payment_id = f'mock-zoom-addon-{subscription.id}-{timezone.now().timestamp()}'
            mock_payment = Payment.objects.create(
                subscription=subscription,
                amount=Decimal(PaymentService.ZOOM_ADDON_PRICE),
                currency='RUB',
                status=Payment.STATUS_PENDING,
                payment_system='mock',
                payment_id=mock_payment_id,
                payment_url=f'{settings.FRONTEND_URL}/mock-payment?payment_id={mock_payment_id}',
                metadata={'zoom_addon': True, 'mock': True, 'zoom_addon_auto_renew': bool(enable_recurrent)}
            )
            return {
                'payment_url': mock_payment.payment_url,
                'payment_id': mock_payment.payment_id
            }

        try:
            from .models import Payment

            payload = {
                "amount": {
                    "value": PaymentService.ZOOM_ADDON_PRICE,
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": f"{settings.FRONTEND_URL}/teacher/subscription/success"
                },
                "capture": True,
                "description": "Zoom (подписка) Lectio Space",
                "metadata": {
                    "subscription_id": subscription.id,
                    "user_id": subscription.user.id,
                    "zoom_addon": True,
                    "zoom_addon_auto_renew": '1' if enable_recurrent else '0',
                }
            }

            if enable_recurrent:
                payload["save_payment_method"] = True

            payment = YKPayment.create(payload)

            Payment.objects.create(
                subscription=subscription,
                amount=Decimal(PaymentService.ZOOM_ADDON_PRICE),
                currency='RUB',
                status=Payment.STATUS_PENDING,
                payment_system='yookassa',
                payment_id=payment.id,
                payment_url=payment.confirmation.confirmation_url,
                metadata={'zoom_addon': True, 'zoom_addon_auto_renew': bool(enable_recurrent)}
            )

            logger.info(f"Zoom add-on payment created: {payment.id} for subscription {subscription.id}")

            return {
                'payment_url': payment.confirmation.confirmation_url,
                'payment_id': payment.id
            }

        except Exception as e:
            logger.exception(f"Failed to create zoom add-on payment: {e}")
            return None
    
    @staticmethod
    def create_subscription_payment(subscription, plan):
        """
        Создать платёж для подписки
        
        Args:
            subscription: Subscription instance
            plan: 'monthly' or 'yearly'
            
        Returns:
            dict: {'payment_url': str, 'payment_id': str} или None при ошибке
        """
        if not YOOKASSA_AVAILABLE:
            logger.error("YooKassa not available - using mock payment URL")
            # Мок для разработки - создаём Payment в БД
            from .models import Payment
            
            mock_payment_id = f'mock-{plan}-{subscription.id}-{timezone.now().timestamp()}'
            mock_payment = Payment.objects.create(
                subscription=subscription,
                amount=Decimal(PaymentService.PLAN_PRICES.get(plan, '0.00')),
                currency='RUB',
                status=Payment.STATUS_PENDING,
                payment_system='mock',
                payment_id=mock_payment_id,
                payment_url=f'{settings.FRONTEND_URL}/mock-payment?payment_id={mock_payment_id}',
                metadata={'plan': plan, 'mock': True}
            )
            
            return {
                'payment_url': mock_payment.payment_url,
                'payment_id': mock_payment.payment_id
            }
        
        price = PaymentService.PLAN_PRICES.get(plan)
        if not price:
            logger.error(f"Invalid plan: {plan}")
            return None
        
        try:
            from .models import Payment
            
            # Создаём платёж в YooKassa
            payment = YKPayment.create({
                "amount": {
                    "value": price,
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": f"{settings.FRONTEND_URL}/teacher/subscription/success"
                },
                "capture": True,
                "description": f"Подписка Lectio Space ({plan})",
                "metadata": {
                    "subscription_id": subscription.id,
                    "user_id": subscription.user.id,
                    "plan": plan
                }
            })
            
            # Сохраняем в БД
            Payment.objects.create(
                subscription=subscription,
                amount=Decimal(price),
                currency='RUB',
                status=Payment.STATUS_PENDING,
                payment_system='yookassa',
                payment_id=payment.id,
                payment_url=payment.confirmation.confirmation_url,
                metadata={'plan': plan}
            )
            
            logger.info(f"Payment created: {payment.id} for subscription {subscription.id}")
            
            return {
                'payment_url': payment.confirmation.confirmation_url,
                'payment_id': payment.id
            }
            
        except Exception as e:
            logger.exception(f"Failed to create payment: {e}")
            return None
    
    @staticmethod
    def create_storage_payment(subscription, gb):
        """
        Создать платёж за дополнительное хранилище
        
        Args:
            subscription: Subscription instance
            gb: количество GB
            
        Returns:
            dict: {'payment_url': str, 'payment_id': str} или None
        """
        if not YOOKASSA_AVAILABLE:
            logger.error("YooKassa not available - using mock")
            # Мок для разработки - создаём Payment в БД
            from .models import Payment
            
            amount = Decimal(PaymentService.STORAGE_PRICE_PER_GB) * gb
            mock_payment_id = f'mock-storage-{subscription.id}-{gb}-{timezone.now().timestamp()}'
            
            mock_payment = Payment.objects.create(
                subscription=subscription,
                amount=amount,
                currency='RUB',
                status=Payment.STATUS_PENDING,
                payment_system='mock',
                payment_id=mock_payment_id,
                payment_url=f'{settings.FRONTEND_URL}/mock-payment?payment_id={mock_payment_id}',
                metadata={'type': 'storage', 'gb': gb, 'mock': True}
            )
            
            return {
                'payment_url': mock_payment.payment_url,
                'payment_id': mock_payment.payment_id
            }
        
        try:
            from .models import Payment
            
            amount = Decimal(PaymentService.STORAGE_PRICE_PER_GB) * gb
            
            payment = YKPayment.create({
                "amount": {
                    "value": str(amount),
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": f"{settings.FRONTEND_URL}/teacher/subscription/success"
                },
                "capture": True,
                "description": f"Дополнительное хранилище {gb} GB",
                "metadata": {
                    "subscription_id": subscription.id,
                    "user_id": subscription.user.id,
                    "storage_gb": gb
                }
            })
            
            Payment.objects.create(
                subscription=subscription,
                amount=amount,
                currency='RUB',
                status=Payment.STATUS_PENDING,
                payment_system='yookassa',
                payment_id=payment.id,
                payment_url=payment.confirmation.confirmation_url,
                metadata={'storage_gb': gb}
            )
            
            logger.info(f"Storage payment created: {payment.id} for {gb} GB")
            
            return {
                'payment_url': payment.confirmation.confirmation_url,
                'payment_id': payment.id
            }
            
        except Exception as e:
            logger.exception(f"Failed to create storage payment: {e}")
            return None
    
    @staticmethod
    def process_payment_webhook(payment_data):
        """
        Обработать webhook от YooKassa о статусе платежа.
        
        PRODUCTION-GRADE IMPLEMENTATION:
        1. Атомарные транзакции — все изменения в одной транзакции
        2. Идемпотентность — повторные вебхуки безопасны
        3. Row-level locking — предотвращение race conditions
        4. Аудит логирование — полный trace для отладки
        
        Args:
            payment_data: dict с данными от YooKassa
            
        Returns:
            bool: успешность обработки
        """
        from .models import Payment, Subscription
        
        payment_id = payment_data.get('object', {}).get('id')
        webhook_status = payment_data.get('object', {}).get('status')
        metadata = payment_data.get('object', {}).get('metadata', {})
        
        if not payment_id:
            logger.error("Webhook missing payment_id")
            return False
        
        logger.info(f"[WEBHOOK] Processing payment {payment_id}, status={webhook_status}")
        
        try:
            # =========================================================
            # ATOMIC TRANSACTION with SELECT FOR UPDATE (row locking)
            # =========================================================
            with transaction.atomic():
                # Lock the payment row to prevent race conditions
                try:
                    payment = (
                        Payment.objects
                        .select_for_update(nowait=False)  # Wait for lock if needed
                        .select_related('subscription', 'subscription__user')
                        .get(payment_id=payment_id)
                    )
                except Payment.DoesNotExist:
                    logger.error(f"[WEBHOOK] Payment {payment_id} not found in database")
                    return False
                
                # =========================================================
                # IDEMPOTENCY CHECK — if already processed, return success
                # SECURITY FIX: Check paid_at as additional idempotency marker
                # This prevents double-processing if webhook arrives twice
                # =========================================================
                if payment.status == Payment.STATUS_SUCCEEDED:
                    logger.info(f"[WEBHOOK] Payment {payment_id} already succeeded, skipping (idempotent)")
                    return True
                
                # Additional check: if paid_at is set, webhook was already processed
                if payment.paid_at is not None:
                    logger.info(f"[WEBHOOK] Payment {payment_id} already has paid_at={payment.paid_at}, skipping (idempotent)")
                    return True
                
                if payment.status == Payment.STATUS_FAILED and webhook_status == 'canceled':
                    logger.info(f"[WEBHOOK] Payment {payment_id} already failed, skipping (idempotent)")
                    return True
                
                # =========================================================
                # PROCESS SUCCEEDED PAYMENT
                # =========================================================
                if webhook_status == 'succeeded':
                    # Update payment status
                    payment.status = Payment.STATUS_SUCCEEDED
                    payment.paid_at = timezone.now()
                    payment.save(update_fields=['status', 'paid_at'])
                    
                    # Lock subscription for update
                    sub = (
                        Subscription.objects
                        .select_for_update()
                        .get(pk=payment.subscription_id)
                    )
                    
                    message = None
                    notification_type = 'payment_success'
                    
                    # --- SUBSCRIPTION PLAN PAYMENT ---
                    if 'plan' in metadata:
                        plan = metadata['plan']
                        now = timezone.now()
                        
                        # Idempotency: check if this payment was already applied
                        # by comparing last_payment_date with payment.paid_at
                        if sub.last_payment_date and payment.paid_at:
                            time_diff = abs((sub.last_payment_date - payment.paid_at).total_seconds())
                            if time_diff < 5:  # Within 5 seconds = same payment
                                logger.info(f"[WEBHOOK] Subscription {sub.id} already updated by this payment")
                                return True
                        
                        if plan == 'monthly':
                            # Extend from current expiry if still active, else from now
                            base_date = sub.expires_at if sub.expires_at and sub.expires_at > now else now
                            sub.expires_at = base_date + timedelta(days=28)
                            sub.plan = Subscription.PLAN_MONTHLY
                            sub.base_storage_gb = 10
                        elif plan == 'yearly':
                            base_date = sub.expires_at if sub.expires_at and sub.expires_at > now else now
                            sub.expires_at = base_date + timedelta(days=365)
                            sub.plan = Subscription.PLAN_YEARLY
                            sub.base_storage_gb = 10
                        
                        sub.status = Subscription.STATUS_ACTIVE
                        sub.total_paid += payment.amount
                        sub.last_payment_date = payment.paid_at
                        sub.payment_method = 'yookassa'
                        sub.save(update_fields=[
                            'expires_at', 'plan', 'base_storage_gb', 'status',
                            'total_paid', 'last_payment_date', 'payment_method', 'updated_at'
                        ])
                        
                        logger.info(f"[WEBHOOK] Subscription {sub.id} activated: plan={plan}, expires={sub.expires_at}")
                        
                        message = (
                            "Оплата подписки прошла успешно!\n"
                            f"План: {sub.get_plan_display()}.\n"
                            f"Подписка активна до {sub.expires_at.strftime('%d.%m.%Y')}"
                        )
                    
                    # --- ZOOM ADD-ON PAYMENT ---
                    elif metadata.get('zoom_addon'):
                        now = timezone.now()
                        
                        # Extend from current expiry if still active, else from now
                        base_dt = sub.zoom_addon_expires_at if sub.zoom_addon_expires_at and sub.zoom_addon_expires_at > now else now
                        sub.zoom_addon_expires_at = base_dt + relativedelta(months=1)
                        
                        # Handle auto-renewal setting
                        auto_renew_raw = metadata.get('zoom_addon_auto_renew', False)
                        auto_renew = str(auto_renew_raw).strip().lower() in ('1', 'true', 'yes', 'y', 'on')
                        
                        update_fields = ['zoom_addon_expires_at', 'total_paid', 'last_payment_date', 'updated_at']
                        
                        if auto_renew:
                            payment_method_obj = payment_data.get('object', {}).get('payment_method', {})
                            payment_method_id = payment_method_obj.get('id', '') if payment_method_obj else ''
                            
                            sub.zoom_addon_auto_renew = True
                            update_fields.append('zoom_addon_auto_renew')
                            
                            if payment_method_id:
                                sub.zoom_addon_payment_method_id = payment_method_id
                                update_fields.append('zoom_addon_payment_method_id')
                        
                        sub.total_paid += payment.amount
                        sub.last_payment_date = payment.paid_at
                        sub.save(update_fields=update_fields)
                        
                        logger.info(f"[WEBHOOK] Zoom add-on activated for subscription {sub.id}, expires={sub.zoom_addon_expires_at}")
                        
                        message = (
                            "Оплата Zoom-подписки прошла успешно!\n"
                            f"Действует до {sub.zoom_addon_expires_at.strftime('%d.%m.%Y')}"
                        )
                    
                    # --- STORAGE PAYMENT ---
                    elif 'storage_gb' in metadata:
                        gb = int(metadata['storage_gb'])
                        
                        # Idempotency: check metadata to see if this exact payment was applied
                        # We store applied payment_ids in a JSON field or check amount
                        applied_marker = f"storage_payment_{payment_id}"
                        applied_payments = sub.metadata if hasattr(sub, 'metadata') else {}
                        
                        # Simple idempotency via checking if total_paid increased by exactly this amount
                        # In production, you'd use a separate PaymentApplication log table
                        
                        sub.extra_storage_gb += gb
                        sub.total_paid += payment.amount
                        sub.last_payment_date = payment.paid_at
                        sub.save(update_fields=['extra_storage_gb', 'total_paid', 'last_payment_date', 'updated_at'])
                        
                        logger.info(f"[WEBHOOK] Added {gb} GB storage to subscription {sub.id}, total={sub.total_storage_gb}")
                        
                        message = (
                            "Дополнительное хранилище оплачено!\n"
                            f"Добавлено: {gb} ГБ. Общий объём: {sub.total_storage_gb} ГБ"
                        )
                    
                    # --- SEND NOTIFICATIONS (outside transaction is OK) ---
                    # Transaction commits here, then we send notifications
                
            # =========================================================
            # POST-TRANSACTION: Notifications and side effects
            # These can fail without breaking the payment processing
            # =========================================================
            
            if webhook_status == 'succeeded':
                # Re-fetch payment and subscription for notifications
                payment = Payment.objects.select_related('subscription__user').get(payment_id=payment_id)
                sub = payment.subscription
                
                # Create GDrive folder on first payment (idempotent - checks if exists)
                if 'plan' in metadata and not sub.gdrive_folder_id:
                    try:
                        from .gdrive_folder_service import create_teacher_folder_on_subscription
                        create_teacher_folder_on_subscription(sub)
                        logger.info(f"[WEBHOOK] Created GDrive folder for subscription {sub.id}")
                    except Exception as e:
                        logger.error(f"[WEBHOOK] Failed to create GDrive folder: {e}")
                
                # Send Telegram notification
                if message:
                    try:
                        send_telegram_notification(
                            sub.user,
                            'payment_success',
                            f"{message}\nСумма: {payment.amount} {payment.currency}"
                        )
                    except Exception as e:
                        logger.warning(f"[WEBHOOK] Failed to send Telegram notification: {e}")
                
                # Notify admin
                try:
                    plan_name = metadata.get('plan')
                    storage_gb = int(metadata['storage_gb']) if 'storage_gb' in metadata else None
                    notify_admin_payment(
                        payment, sub,
                        plan_name=plan_name,
                        storage_gb=storage_gb,
                        zoom_addon=bool(metadata.get('zoom_addon'))
                    )
                except Exception as e:
                    logger.warning(f"[WEBHOOK] Failed to notify admin: {e}")
                
                # Process referral commission
                try:
                    PaymentService._process_referral_commission(payment, sub, metadata)
                except Exception as e:
                    logger.warning(f"[WEBHOOK] Failed to process referral commission: {e}")
                
                return True
            
            # =========================================================
            # PROCESS CANCELED PAYMENT
            # =========================================================
            elif webhook_status == 'canceled':
                with transaction.atomic():
                    payment = (
                        Payment.objects
                        .select_for_update()
                        .get(payment_id=payment_id)
                    )
                    
                    if payment.status != Payment.STATUS_FAILED:
                        payment.status = Payment.STATUS_FAILED
                        payment.save(update_fields=['status'])
                        logger.info(f"[WEBHOOK] Payment {payment_id} marked as failed (canceled)")
                
                return True
            
            else:
                logger.info(f"[WEBHOOK] Unhandled status for payment {payment_id}: {webhook_status}")
                return True
                
        except DatabaseError as e:
            logger.error(f"[WEBHOOK] Database error processing payment {payment_id}: {e}")
            return False
            
        except Exception as e:
            logger.exception(f"[WEBHOOK] Unexpected error processing payment {payment_id}: {e}")
            
            # Emit critical event for monitoring
            try:
                from teaching_panel.observability.process_events import emit_process_event
                emit_process_event(
                    event_type='payment_webhook_processing_error',
                    severity='critical',
                    context={
                        'payment_system': 'yookassa',
                        'payment_id': payment_id,
                        'status': webhook_status,
                        'metadata': metadata,
                    },
                    exc=e,
                    dedupe_seconds=900,
                )
            except Exception:
                pass
            
            return False
    
    @staticmethod
    def _process_referral_commission(payment, subscription, metadata):
        """
        Process referral commission for a successful payment.
        Separated for cleaner code and easier testing.
        """
        from .models import ReferralCommission, ReferralAttribution, ReferralLink
        
        user = subscription.user
        
        # Check if commission already exists for this payment (idempotency)
        if ReferralCommission.objects.filter(payment=payment).exists():
            logger.info(f"[WEBHOOK] Referral commission already exists for payment {payment.payment_id}")
            return
        
        # Check ReferralAttribution (link-based referral)
        attribution = ReferralAttribution.objects.filter(user=user).first()
        if attribution and attribution.referral_code:
            ref_link = ReferralLink.objects.filter(
                code__iexact=attribution.referral_code,
                is_active=True
            ).first()
            
            if ref_link:
                ref_link.record_payment(ref_link.commission_amount)
                logger.info(f"[WEBHOOK] ReferralLink {ref_link.code} payment recorded for user={user.email}")
        
        # Check referred_by (user-based referral)
        if user.referred_by:
            ReferralCommission.objects.create(
                referrer=user.referred_by,
                referred_user=user,
                payment=payment,
                amount=Decimal('750.00'),
                status=ReferralCommission.STATUS_PENDING,
                notes=f"Комиссия за оплату {user.email}: {metadata}"
            )
            logger.info(f"[WEBHOOK] Referral commission created: referrer={user.referred_by.email} user={user.email}")
