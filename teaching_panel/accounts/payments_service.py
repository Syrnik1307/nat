"""
YooKassa payment integration service
Handles payment creation and processing for subscriptions
"""
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
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
        Обработать webhook от YooKassa о статусе платежа
        
        Args:
            payment_data: dict с данными от YooKassa
            
        Returns:
            bool: успешность обработки
        """
        try:
            from .models import Payment, Subscription
            
            payment_id = payment_data['object']['id']
            status = payment_data['object']['status']
            metadata = payment_data['object'].get('metadata', {})
            
            # Находим платёж в БД
            try:
                payment = Payment.objects.select_related('subscription').get(payment_id=payment_id)
            except Payment.DoesNotExist:
                logger.error(f"Payment {payment_id} not found in database")
                return False
            
            if status == 'succeeded':
                payment.status = Payment.STATUS_SUCCEEDED
                payment.paid_at = timezone.now()
                payment.save()
                
                sub = payment.subscription
                
                # Обработка подписки
                message = None

                if 'plan' in metadata:
                    plan = metadata['plan']
                    if plan == 'monthly':
                        sub.expires_at = timezone.now() + timedelta(days=28)
                        sub.plan = Subscription.PLAN_MONTHLY
                        sub.base_storage_gb = 10
                    elif plan == 'yearly':
                        sub.expires_at = timezone.now() + timedelta(days=365)
                        sub.plan = Subscription.PLAN_YEARLY
                        sub.base_storage_gb = 10
                    
                    sub.status = Subscription.STATUS_ACTIVE
                    sub.total_paid += payment.amount
                    sub.last_payment_date = timezone.now()
                    sub.payment_method = 'yookassa'
                    sub.save()
                    
                    # Создаём папку на Google Drive при первой оплате
                    if not sub.gdrive_folder_id:
                        try:
                            from .gdrive_folder_service import create_teacher_folder_on_subscription
                            create_teacher_folder_on_subscription(sub)
                            logger.info(f"Created GDrive folder for subscription {sub.id}")
                        except Exception as e:
                            logger.error(f"Failed to create GDrive folder for subscription {sub.id}: {e}")
                    
                    logger.info(f"Subscription {sub.id} activated with plan {plan}")

                    message = (
                        "💳 Оплата подписки прошла успешно!\n"
                        f"План: {sub.get_plan_display()}.\n"
                        f"Подписка активна до {sub.expires_at.strftime('%d.%m.%Y')}"
                    )

                # Zoom add-on
                elif metadata.get('zoom_addon'):
                    now = timezone.now()
                    base_dt = sub.zoom_addon_expires_at if sub.zoom_addon_expires_at and sub.zoom_addon_expires_at > now else now
                    sub.zoom_addon_expires_at = base_dt + relativedelta(months=1)

                    auto_renew_raw = metadata.get('zoom_addon_auto_renew', False)
                    auto_renew = str(auto_renew_raw).strip().lower() in ('1', 'true', 'yes', 'y', 'on')
                    if auto_renew:
                        # Сохраняем payment_method.id если YooKassa его вернула.
                        try:
                            payment_method = payment_data.get('object', {}).get('payment_method', {})
                            payment_method_id = payment_method.get('id') or ''
                        except Exception:
                            payment_method_id = ''

                        sub.zoom_addon_auto_renew = True
                        if payment_method_id:
                            sub.zoom_addon_payment_method_id = payment_method_id

                    sub.total_paid += payment.amount
                    sub.last_payment_date = timezone.now()
                    update_fields = ['zoom_addon_expires_at', 'total_paid', 'last_payment_date', 'updated_at']
                    if auto_renew:
                        update_fields.extend(['zoom_addon_auto_renew', 'zoom_addon_payment_method_id'])
                    sub.save(update_fields=update_fields)

                    logger.info(f"Zoom add-on activated for subscription {sub.id}")

                    message = (
                        "Оплата Zoom-подписки прошла успешно!\n"
                        f"Действует до {sub.zoom_addon_expires_at.strftime('%d.%m.%Y')}"
                    )
                
                # Обработка хранилища
                elif 'storage_gb' in metadata:
                    gb = int(metadata['storage_gb'])
                    sub.extra_storage_gb += gb
                    sub.total_paid += payment.amount
                    sub.last_payment_date = timezone.now()
                    sub.save()
                    
                    logger.info(f"Added {gb} GB storage to subscription {sub.id}")

                    message = (
                        "☁️ Дополнительное хранилище оплачено!\n"
                        f"Добавлено: {gb} ГБ. Общий объём: {sub.total_storage_gb} ГБ"
                    )

                if message:
                    send_telegram_notification(
                        sub.user,
                        'payment_success',
                        f"{message}\nСумма: {payment.amount} {payment.currency}"
                    )
                
                # Уведомление админа о новом платеже
                plan_name = metadata.get('plan')
                storage_gb = int(metadata['storage_gb']) if 'storage_gb' in metadata else None
                notify_admin_payment(payment, sub, plan_name=plan_name, storage_gb=storage_gb, zoom_addon=bool(metadata.get('zoom_addon')))

                # Реферальная комиссия: проверяем ReferralLink или referred_by
                try:
                    user = sub.user
                    from .models import ReferralCommission, ReferralAttribution, ReferralLink
                    
                    # Проверяем, есть ли уже комиссия для этого платежа
                    if not ReferralCommission.objects.filter(payment=payment).exists():
                        # Сначала проверяем ReferralAttribution (код ссылки)
                        attribution = ReferralAttribution.objects.filter(user=user).first()
                        if attribution and attribution.referral_code:
                            ref_link = ReferralLink.objects.filter(code__iexact=attribution.referral_code, is_active=True).first()
                            if ref_link:
                                # Записываем оплату для ReferralLink
                                ref_link.record_payment(ref_link.commission_amount)
                                logger.info(f"ReferralLink {ref_link.code} payment recorded for user={user.email}")
                        
                        # Также проверяем referred_by (личные реферальные коды пользователей)
                        if user.referred_by:
                            ReferralCommission.objects.create(
                                referrer=user.referred_by,
                                referred_user=user,
                                payment=payment,
                                amount=Decimal('750.00'),
                                status=ReferralCommission.STATUS_PENDING,
                                notes=f"Комиссия за оплату {user.email}: {metadata}"
                            )
                            logger.info(f"Referral commission created: referrer={user.referred_by.email} user={user.email} payment={payment.payment_id}")
                except Exception as ref_e:
                    logger.warning(f"Failed to create referral commission: {ref_e}")
                
                return True
            
            elif status == 'canceled':
                payment.status = Payment.STATUS_FAILED
                payment.save()
                logger.info(f"Payment {payment_id} was canceled")
                return True
            
            else:
                logger.info(f"Payment {payment_id} status: {status}")
                return True
                
        except Exception as e:
            logger.exception(f"Webhook processing error: {e}")

            # Process-level alert (best-effort, must not break webhook response)
            try:
                from teaching_panel.observability.process_events import emit_process_event

                payment_id = None
                status = None
                metadata = None
                try:
                    payment_id = (payment_data or {}).get('object', {}).get('id')
                    status = (payment_data or {}).get('object', {}).get('status')
                    metadata = (payment_data or {}).get('object', {}).get('metadata')
                except Exception:
                    pass

                teacher = None
                try:
                    teacher = locals().get('sub', None)
                    teacher = getattr(teacher, 'user', None)
                except Exception:
                    teacher = None

                emit_process_event(
                    event_type='payment_webhook_processing_error',
                    severity='critical',
                    actor_user=teacher,
                    teacher=teacher,
                    context={
                        'payment_system': 'yookassa',
                        'payment_id': payment_id,
                        'status': status,
                        'metadata': metadata,
                    },
                    exc=e,
                    dedupe_seconds=900,
                )
            except Exception:
                pass
            return False
