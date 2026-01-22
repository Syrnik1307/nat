"""
T-Bank (ex-Tinkoff) payment integration service
Handles payment creation and processing for subscriptions via T-Bank Acquiring API

API Documentation: https://developer.tbank.ru/eacq/api/init
"""
import hashlib
import requests
import logging
from decimal import Decimal
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.utils import timezone

from .notifications import (
    send_telegram_notification,
    notify_admin_payment,
    notify_payment_failed,
    notify_payment_refunded,
    notify_auto_renewal_success,
)

logger = logging.getLogger(__name__)

# T-Bank API endpoints
# DEMO terminals work on production API, not test API
TBANK_API_URL = 'https://securepay.tinkoff.ru/v2'


class TBankService:
    """
    Service for handling subscription payments via T-Bank Acquiring API
    
    Supports:
    - One-time payments (подписка monthly/yearly)
    - Recurring payments (автопродление) via RebillId
    - Storage purchases
    """
    
    PLAN_PRICES = {
        'monthly': Decimal('1590.00'),
        'yearly': Decimal('9900.00'),
    }
    
    STORAGE_PRICE_PER_GB = Decimal('20.00')

    ZOOM_ADDON_PRICE = Decimal('990.00')

    @staticmethod
    def create_zoom_addon_payment(subscription, enable_recurrent: bool = False):
        """Create payment for Zoom add-on (990 ₽ / 1 month)."""
        if not TBankService.is_available():
            logger.warning("T-Bank not configured, using mock payment")
            from .models import Payment

            mock_payment_id = f'mock-zoom-addon-{subscription.id}-{int(timezone.now().timestamp())}'
            mock_payment = Payment.objects.create(
                subscription=subscription,
                amount=TBankService.ZOOM_ADDON_PRICE,
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

        amount_kopecks = int(TBankService.ZOOM_ADDON_PRICE * 100)
        order_id = f"zoom-addon-{subscription.id}-{int(timezone.now().timestamp())}"

        request_data = {
            'Amount': amount_kopecks,
            'OrderId': order_id,
            'Description': 'Zoom (подписка) Lectio Space',
            'CustomerKey': str(subscription.user.id),
            'SuccessURL': f"{settings.FRONTEND_URL}/teacher/subscription?status=success",
            'FailURL': f"{settings.FRONTEND_URL}/teacher/subscription?status=fail",
            'NotificationURL': f"{settings.SITE_URL}/api/payments/tbank/webhook/",
            'PayType': 'O',
            'Language': 'ru',
            'DATA': {
                'subscription_id': str(subscription.id),
                'user_id': str(subscription.user.id),
                'zoom_addon': '1',
                'zoom_addon_auto_renew': '1' if enable_recurrent else '0',
                'Email': subscription.user.email,
            }
        }

        if enable_recurrent:
            request_data['Recurrent'] = 'Y'

        result = TBankService._make_request('Init', request_data)
        if result.get('Success'):
            from .models import Payment

            Payment.objects.create(
                subscription=subscription,
                amount=TBankService.ZOOM_ADDON_PRICE,
                currency='RUB',
                status=Payment.STATUS_PENDING,
                payment_system='tbank',
                payment_id=result['PaymentId'],
                payment_url=result['PaymentURL'],
                metadata={
                    'zoom_addon': True,
                    'order_id': order_id,
                    'terminal_key': settings.TBANK_TERMINAL_KEY,
                    'zoom_addon_auto_renew': bool(enable_recurrent),
                }
            )

            logger.info(f"T-Bank zoom add-on payment created: {result['PaymentId']} for subscription {subscription.id}")
            return {
                'payment_url': result['PaymentURL'],
                'payment_id': result['PaymentId']
            }

        logger.error(f"Failed to create T-Bank zoom add-on payment: {result.get('Message')}")
        return None
    
    @staticmethod
    def is_available():
        """Check if T-Bank is configured"""
        return bool(getattr(settings, 'TBANK_TERMINAL_KEY', ''))
    
    @staticmethod
    def is_test_mode():
        """Check if using test/demo terminal"""
        terminal = getattr(settings, 'TBANK_TERMINAL_KEY', '')
        return 'DEMO' in terminal.upper() or 'TEST' in terminal.upper()
    
    @staticmethod
    def _get_api_url():
        """Get API URL - DEMO terminals use production API"""
        return TBANK_API_URL
    
    @staticmethod
    def _generate_token(params: dict) -> str:
        """
        Generate Token (signature) for T-Bank API request
        
        Algorithm:
        1. Collect all root-level params (exclude nested objects/arrays)
        2. Add Password to params
        3. Sort alphabetically by key
        4. Concatenate values only
        5. SHA-256 hash the result
        
        Docs: https://developer.tbank.ru/eacq/intro/developer/token
        """
        # Clone params and add password
        sign_params = {k: v for k, v in params.items() 
                       if not isinstance(v, (dict, list)) and k != 'Token'}
        sign_params['Password'] = settings.TBANK_PASSWORD
        
        # Sort by key and concatenate values
        sorted_keys = sorted(sign_params.keys())
        concat_string = ''.join(str(sign_params[k]) for k in sorted_keys)
        
        # SHA-256 hash
        token = hashlib.sha256(concat_string.encode('utf-8')).hexdigest()
        return token
    
    @staticmethod
    def _verify_notification_token(notification_data: dict) -> bool:
        """
        Verify Token from T-Bank notification/webhook
        
        Same algorithm as _generate_token but applied to notification params
        """
        received_token = notification_data.get('Token', '')
        if not received_token:
            return False
        
        # Generate expected token from notification params
        expected_token = TBankService._generate_token(notification_data)
        
        # Secure comparison
        return received_token.lower() == expected_token.lower()
    
    @staticmethod
    def _make_request(method: str, data: dict) -> dict:
        """Make HTTP request to T-Bank API"""
        url = f"{TBankService._get_api_url()}/{method}"
        
        # Add terminal key and generate token
        data['TerminalKey'] = settings.TBANK_TERMINAL_KEY
        data['Token'] = TBankService._generate_token(data)
        
        try:
            response = requests.post(url, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            if not result.get('Success', False):
                error_code = result.get('ErrorCode', 'unknown')
                error_msg = result.get('Message', 'Unknown error')
                logger.error(f"T-Bank API error: {error_code} - {error_msg}")
            
            return result
            
        except requests.RequestException as e:
            logger.exception(f"T-Bank API request failed: {e}")
            return {'Success': False, 'ErrorCode': 'network', 'Message': str(e)}
    
    @staticmethod
    def create_subscription_payment(subscription, plan: str, enable_recurrent: bool = True):
        """
        Create payment for subscription plan
        
        Args:
            subscription: Subscription instance
            plan: 'monthly' or 'yearly'
            enable_recurrent: If True, enables card binding for future auto-renewals
            
        Returns:
            dict: {'payment_url': str, 'payment_id': str} or None on error
        """
        if not TBankService.is_available():
            logger.warning("T-Bank not configured, using mock payment")
            return TBankService._create_mock_payment(subscription, plan)
        
        price = TBankService.PLAN_PRICES.get(plan)
        if not price:
            logger.error(f"Invalid plan: {plan}")
            return None
        
        # Amount in kopecks (копейки)
        amount_kopecks = int(price * 100)
        
        # Generate unique order ID
        order_id = f"sub-{subscription.id}-{plan}-{int(timezone.now().timestamp())}"
        
        # Prepare request data
        request_data = {
            'Amount': amount_kopecks,
            'OrderId': order_id,
            'Description': f'Подписка Lectio Space ({plan})',
            'CustomerKey': str(subscription.user.id),  # For card binding
            'SuccessURL': f"{settings.FRONTEND_URL}/teacher/subscription?status=success",
            'FailURL': f"{settings.FRONTEND_URL}/teacher/subscription?status=fail",
            'NotificationURL': f"{settings.SITE_URL}/api/payments/tbank/webhook/",
            'PayType': 'O',  # One-stage payment (одностадийная оплата)
            'Language': 'ru',
            'DATA': {
                'subscription_id': str(subscription.id),
                'user_id': str(subscription.user.id),
                'plan': plan,
                'Email': subscription.user.email,
            }
        }
        
        # Enable recurring payments (card binding)
        if enable_recurrent:
            request_data['Recurrent'] = 'Y'
        
        result = TBankService._make_request('Init', request_data)
        
        if result.get('Success'):
            from .models import Payment
            
            # Save payment to database
            Payment.objects.create(
                subscription=subscription,
                amount=price,
                currency='RUB',
                status=Payment.STATUS_PENDING,
                payment_system='tbank',
                payment_id=result['PaymentId'],
                payment_url=result['PaymentURL'],
                metadata={
                    'plan': plan,
                    'order_id': order_id,
                    'terminal_key': settings.TBANK_TERMINAL_KEY,
                    'recurrent': enable_recurrent,
                }
            )
            
            logger.info(f"T-Bank payment created: {result['PaymentId']} for subscription {subscription.id}")
            
            return {
                'payment_url': result['PaymentURL'],
                'payment_id': result['PaymentId']
            }
        else:
            logger.error(f"Failed to create T-Bank payment: {result.get('Message')}")
            return None
    
    @staticmethod
    def create_storage_payment(subscription, gb: int):
        """
        Create payment for additional storage
        
        Args:
            subscription: Subscription instance
            gb: Number of gigabytes to purchase
            
        Returns:
            dict: {'payment_url': str, 'payment_id': str} or None
        """
        if not TBankService.is_available():
            logger.warning("T-Bank not configured, using mock payment")
            return TBankService._create_mock_storage_payment(subscription, gb)
        
        if gb <= 0:
            logger.error(f"Invalid storage amount: {gb}")
            return None
        
        price = TBankService.STORAGE_PRICE_PER_GB * gb
        amount_kopecks = int(price * 100)
        
        order_id = f"storage-{subscription.id}-{gb}gb-{int(timezone.now().timestamp())}"
        
        request_data = {
            'Amount': amount_kopecks,
            'OrderId': order_id,
            'Description': f'Дополнительное хранилище {gb} ГБ',
            'CustomerKey': str(subscription.user.id),
            'SuccessURL': f"{settings.FRONTEND_URL}/teacher/subscription?status=success",
            'FailURL': f"{settings.FRONTEND_URL}/teacher/subscription?status=fail",
            'NotificationURL': f"{settings.SITE_URL}/api/payments/tbank/webhook/",
            'PayType': 'O',
            'Language': 'ru',
            'DATA': {
                'subscription_id': str(subscription.id),
                'user_id': str(subscription.user.id),
                'storage_gb': str(gb),
                'Email': subscription.user.email,
            }
        }
        
        result = TBankService._make_request('Init', request_data)
        
        if result.get('Success'):
            from .models import Payment
            
            Payment.objects.create(
                subscription=subscription,
                amount=price,
                currency='RUB',
                status=Payment.STATUS_PENDING,
                payment_system='tbank',
                payment_id=result['PaymentId'],
                payment_url=result['PaymentURL'],
                metadata={
                    'storage_gb': gb,
                    'order_id': order_id,
                }
            )
            
            logger.info(f"T-Bank storage payment created: {result['PaymentId']} for {gb} GB")
            
            return {
                'payment_url': result['PaymentURL'],
                'payment_id': result['PaymentId']
            }
        else:
            logger.error(f"Failed to create T-Bank storage payment: {result.get('Message')}")
            return None
    
    @staticmethod
    def charge_recurring(subscription, plan: str, rebill_id: str):
        """
        Charge recurring payment using saved card (RebillId)
        
        Args:
            subscription: Subscription instance
            plan: 'monthly' or 'yearly'
            rebill_id: RebillId from previous payment
            
        Returns:
            dict: {'payment_id': str, 'success': bool} or None
        """
        if not TBankService.is_available():
            logger.error("T-Bank not configured for recurring payment")
            return None
        
        price = TBankService.PLAN_PRICES.get(plan)
        if not price:
            logger.error(f"Invalid plan for recurring: {plan}")
            return None
        
        amount_kopecks = int(price * 100)
        order_id = f"recur-{subscription.id}-{plan}-{int(timezone.now().timestamp())}"
        
        # First, init the payment
        init_data = {
            'Amount': amount_kopecks,
            'OrderId': order_id,
            'Description': f'Автопродление подписки Lectio Space ({plan})',
            'CustomerKey': str(subscription.user.id),
            'NotificationURL': f"{settings.SITE_URL}/api/payments/tbank/webhook/",
            'PayType': 'O',
            'Recurrent': 'Y',
            'DATA': {
                'subscription_id': str(subscription.id),
                'user_id': str(subscription.user.id),
                'plan': plan,
                'is_recurring': 'true',
            }
        }
        
        init_result = TBankService._make_request('Init', init_data)
        
        if not init_result.get('Success'):
            logger.error(f"Failed to init recurring payment: {init_result.get('Message')}")
            return None
        
        payment_id = init_result['PaymentId']
        
        # Now charge using RebillId
        charge_data = {
            'PaymentId': payment_id,
            'RebillId': rebill_id,
        }
        
        charge_result = TBankService._make_request('Charge', charge_data)
        
        if charge_result.get('Success'):
            from .models import Payment
            
            Payment.objects.create(
                subscription=subscription,
                amount=price,
                currency='RUB',
                status=Payment.STATUS_PENDING,  # Will be updated by webhook
                payment_system='tbank',
                payment_id=payment_id,
                payment_url='',  # No URL for recurring
                metadata={
                    'plan': plan,
                    'order_id': order_id,
                    'is_recurring': True,
                    'rebill_id': rebill_id,
                }
            )
            
            logger.info(f"T-Bank recurring charge initiated: {payment_id}")
            
            return {
                'payment_id': payment_id,
                'success': True,
                'status': charge_result.get('Status')
            }
        else:
            logger.error(f"Failed to charge recurring: {charge_result.get('Message')}")
            return {
                'payment_id': payment_id,
                'success': False,
                'error': charge_result.get('Message')
            }
    
    @staticmethod
    def charge_zoom_addon_recurring(subscription, rebill_id: str):
        """
        Charge recurring payment for Zoom add-on using saved card (RebillId)
        
        Args:
            subscription: Subscription instance
            rebill_id: RebillId from previous zoom add-on payment
            
        Returns:
            dict: {'payment_id': str, 'success': bool} or None
        """
        if not TBankService.is_available():
            logger.error("T-Bank not configured for Zoom add-on recurring payment")
            return None
        
        price = TBankService.ZOOM_ADDON_PRICE
        amount_kopecks = int(price * 100)
        order_id = f"zoom-addon-recur-{subscription.id}-{int(timezone.now().timestamp())}"
        
        # Init the payment
        init_data = {
            'Amount': amount_kopecks,
            'OrderId': order_id,
            'Description': 'Автопродление Zoom Add-on Lectio Space',
            'CustomerKey': str(subscription.user.id),
            'NotificationURL': f"{settings.SITE_URL}/api/payments/tbank/webhook/",
            'PayType': 'O',
            'Recurrent': 'Y',
            'DATA': {
                'subscription_id': str(subscription.id),
                'user_id': str(subscription.user.id),
                'zoom_addon': 'true',
                'is_recurring': 'true',
            }
        }
        
        init_result = TBankService._make_request('Init', init_data)
        
        if not init_result.get('Success'):
            logger.error(f"Failed to init Zoom add-on recurring payment: {init_result.get('Message')}")
            return None
        
        payment_id = init_result['PaymentId']
        
        # Charge using RebillId
        charge_data = {
            'PaymentId': payment_id,
            'RebillId': rebill_id,
        }
        
        charge_result = TBankService._make_request('Charge', charge_data)
        
        if charge_result.get('Success'):
            from .models import Payment
            
            Payment.objects.create(
                subscription=subscription,
                amount=price,
                currency='RUB',
                status=Payment.STATUS_PENDING,
                payment_system='tbank',
                payment_id=payment_id,
                payment_url='',
                metadata={
                    'zoom_addon': True,
                    'order_id': order_id,
                    'is_recurring': True,
                    'rebill_id': rebill_id,
                }
            )
            
            logger.info(f"T-Bank Zoom add-on recurring charge initiated: {payment_id}")
            
            return {
                'payment_id': payment_id,
                'success': True,
                'status': charge_result.get('Status')
            }
        else:
            logger.error(f"Failed to charge Zoom add-on recurring: {charge_result.get('Message')}")
            return {
                'payment_id': payment_id,
                'success': False,
                'error': charge_result.get('Message')
            }
    
    @staticmethod
    def process_notification(notification_data: dict) -> bool:
        """
        Process webhook notification from T-Bank
        
        Args:
            notification_data: Notification payload from T-Bank
            
        Returns:
            bool: True if processed successfully
        """
        try:
            # Verify token
            if not TBankService._verify_notification_token(notification_data):
                logger.warning("Invalid T-Bank notification token")
                return False
            
            from .models import Payment, Subscription
            
            payment_id = str(notification_data.get('PaymentId', ''))
            status = notification_data.get('Status', '')
            
            logger.info(f"T-Bank notification: PaymentId={payment_id}, Status={status}")
            
            # Find payment in DB
            try:
                payment = Payment.objects.select_related('subscription', 'subscription__user').get(
                    payment_id=payment_id
                )
            except Payment.DoesNotExist:
                logger.error(f"Payment not found: {payment_id}")
                return False
            
            sub = payment.subscription
            metadata = payment.metadata or {}
            
            if status == 'CONFIRMED':
                # Payment successful
                payment.status = Payment.STATUS_SUCCEEDED
                payment.paid_at = timezone.now()
                
                # Save RebillId for recurring payments
                rebill_id = notification_data.get('RebillId')
                if rebill_id:
                    metadata['rebill_id'] = rebill_id
                    # Сохраняем RebillId отдельно: основная подписка и Zoom add-on имеют разные циклы.
                    if metadata.get('plan'):
                        sub.tbank_rebill_id = rebill_id
                    elif metadata.get('zoom_addon'):
                        sub.zoom_addon_tbank_rebill_id = rebill_id
                
                payment.metadata = metadata
                payment.save()
                
                message = None
                
                # Activate subscription
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
                    sub.payment_method = 'tbank'
                    sub.save()
                    
                    # Create GDrive folder on first payment
                    if not sub.gdrive_folder_id:
                        try:
                            from .gdrive_folder_service import create_teacher_folder_on_subscription
                            create_teacher_folder_on_subscription(sub)
                            logger.info(f"Created GDrive folder for subscription {sub.id}")
                        except Exception as e:
                            logger.error(f"Failed to create GDrive folder: {e}")
                    
                    logger.info(f"Subscription {sub.id} activated via T-Bank, plan={plan}")
                    
                    message = (
                        "💳 Оплата подписки прошла успешно!\n"
                        f"План: {sub.get_plan_display()}.\n"
                        f"Подписка активна до {sub.expires_at.strftime('%d.%m.%Y')}"
                    )
                
                # Add storage
                elif 'storage_gb' in metadata:
                    gb = int(metadata['storage_gb'])
                    sub.extra_storage_gb += gb
                    sub.total_paid += payment.amount
                    sub.last_payment_date = timezone.now()
                    sub.save()
                    
                    logger.info(f"Added {gb} GB storage via T-Bank to subscription {sub.id}")
                    
                    message = (
                        "☁️ Дополнительное хранилище оплачено!\n"
                        f"Добавлено: {gb} ГБ. Общий объём: {sub.total_storage_gb} ГБ"
                    )

                # Zoom add-on
                elif metadata.get('zoom_addon'):
                    now = timezone.now()
                    base_dt = sub.zoom_addon_expires_at if sub.zoom_addon_expires_at and sub.zoom_addon_expires_at > now else now
                    sub.zoom_addon_expires_at = base_dt + relativedelta(months=1)

                    auto_renew_raw = metadata.get('zoom_addon_auto_renew', False)
                    auto_renew = str(auto_renew_raw).strip().lower() in ('1', 'true', 'yes', 'y', 'on')
                    if auto_renew and sub.zoom_addon_tbank_rebill_id:
                        sub.zoom_addon_auto_renew = True
                    sub.total_paid += payment.amount
                    sub.last_payment_date = timezone.now()
                    update_fields = ['zoom_addon_expires_at', 'total_paid', 'last_payment_date', 'updated_at', 'zoom_addon_tbank_rebill_id']
                    if auto_renew:
                        update_fields.append('zoom_addon_auto_renew')
                    sub.save(update_fields=update_fields)

                    logger.info(f"Zoom add-on activated via T-Bank for subscription {sub.id}")

                    message = (
                        "Оплата Zoom-подписки прошла успешно!\n"
                        f"Действует до {sub.zoom_addon_expires_at.strftime('%d.%m.%Y')}"
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
                
                # Уведомление об успешном автопродлении (если это рекуррентный платёж)
                if metadata.get('is_recurring'):
                    renewal_type = 'zoom_addon' if metadata.get('zoom_addon') else 'subscription'
                    notify_auto_renewal_success(sub, sub.user, renewal_type)
                
                # Handle referral commission
                TBankService._process_referral_commission(payment)
                
                return True
            
            elif status in ['REJECTED', 'CANCELED', 'DEADLINE_EXPIRED', 'AUTH_FAIL']:
                # Payment failed
                payment.status = Payment.STATUS_FAILED
                payment.metadata = {**metadata, 'failure_status': status}
                payment.save()
                
                logger.info(f"T-Bank payment {payment_id} failed with status: {status}")
                
                # Уведомление о неудачном платеже
                notify_payment_failed(payment, sub, reason=status)
                
                return True
            
            elif status == 'REFUNDED':
                payment.status = Payment.STATUS_REFUNDED
                payment.save()
                logger.info(f"T-Bank payment {payment_id} refunded")
                
                # Уведомление о возврате
                notify_payment_refunded(payment, sub)
                
                return True
            
            else:
                # Other statuses (AUTHORIZED, NEW, etc.) - just log
                logger.info(f"T-Bank payment {payment_id} status: {status}")
                return True
                
        except Exception as e:
            logger.exception(f"T-Bank notification processing error: {e}")
            return False
    
    @staticmethod
    def _process_referral_commission(payment):
        """Process referral commission for successful payment"""
        try:
            from .models import ReferralCommission, ReferralAttribution, ReferralLink
            
            user = payment.subscription.user
            
            # Check if commission already exists
            if ReferralCommission.objects.filter(payment=payment).exists():
                return
            
            # Check ReferralAttribution
            attribution = ReferralAttribution.objects.filter(user=user).first()
            if attribution and attribution.referral_code:
                ref_link = ReferralLink.objects.filter(
                    code__iexact=attribution.referral_code, 
                    is_active=True
                ).first()
                if ref_link:
                    ref_link.record_payment(ref_link.commission_amount)
                    logger.info(f"ReferralLink {ref_link.code} payment recorded")
            
            # Check referred_by
            if user.referred_by:
                ReferralCommission.objects.create(
                    referrer=user.referred_by,
                    referred_user=user,
                    payment=payment,
                    amount=Decimal('750.00'),
                    status=ReferralCommission.STATUS_PENDING,
                    notes=f"T-Bank комиссия за оплату {user.email}"
                )
                logger.info(f"Referral commission created for {user.referred_by.email}")
                
        except Exception as e:
            logger.warning(f"Failed to process referral commission: {e}")
    
    @staticmethod
    def _create_mock_payment(subscription, plan: str):
        """Create mock payment for development without T-Bank credentials"""
        from .models import Payment
        
        price = TBankService.PLAN_PRICES.get(plan, Decimal('0'))
        mock_id = f"mock-tbank-{plan}-{subscription.id}-{int(timezone.now().timestamp())}"
        
        Payment.objects.create(
            subscription=subscription,
            amount=price,
            currency='RUB',
            status=Payment.STATUS_PENDING,
            payment_system='mock-tbank',
            payment_id=mock_id,
            payment_url=f'{settings.FRONTEND_URL}/mock-payment?payment_id={mock_id}',
            metadata={'plan': plan, 'mock': True}
        )
        
        return {
            'payment_url': f'{settings.FRONTEND_URL}/mock-payment?payment_id={mock_id}',
            'payment_id': mock_id
        }
    
    @staticmethod
    def _create_mock_storage_payment(subscription, gb: int):
        """Create mock storage payment for development"""
        from .models import Payment
        
        price = TBankService.STORAGE_PRICE_PER_GB * gb
        mock_id = f"mock-tbank-storage-{subscription.id}-{gb}-{int(timezone.now().timestamp())}"
        
        Payment.objects.create(
            subscription=subscription,
            amount=price,
            currency='RUB',
            status=Payment.STATUS_PENDING,
            payment_system='mock-tbank',
            payment_id=mock_id,
            payment_url=f'{settings.FRONTEND_URL}/mock-payment?payment_id={mock_id}',
            metadata={'storage_gb': gb, 'mock': True}
        )
        
        return {
            'payment_url': f'{settings.FRONTEND_URL}/mock-payment?payment_id={mock_id}',
            'payment_id': mock_id
        }

    @staticmethod
    def check_payment_status(payment_id: str) -> dict:
        """
        Check payment status via T-Bank API (GetState)
        
        Args:
            payment_id: T-Bank PaymentId
            
        Returns:
            dict: {'status': str, 'success': bool, ...}
        """
        if not TBankService.is_available():
            return {'success': False, 'error': 'T-Bank not configured'}
        
        request_data = {
            'PaymentId': payment_id,
        }
        
        result = TBankService._make_request('GetState', request_data)
        
        if result.get('Success'):
            return {
                'success': True,
                'status': result.get('Status'),
                'amount': result.get('Amount', 0),
                'order_id': result.get('OrderId'),
            }
        else:
            return {
                'success': False,
                'error': result.get('Message', 'Unknown error'),
            }

    @staticmethod
    def sync_pending_payments():
        """
        Check status of all pending T-Bank payments and process confirmed ones.
        Should be called periodically (e.g., every 5 minutes via cron/celery).
        
        Returns:
            dict: {'processed': int, 'failed': int, 'errors': list}
        """
        from .models import Payment, Subscription
        
        if not TBankService.is_available():
            logger.warning("T-Bank not configured, skipping sync")
            return {'processed': 0, 'failed': 0, 'errors': ['T-Bank not configured']}
        
        pending = Payment.objects.filter(
            status=Payment.STATUS_PENDING,
            payment_system='tbank'
        ).select_related('subscription', 'subscription__user').order_by('-id')[:50]
        
        processed = 0
        failed = 0
        errors = []
        
        for payment in pending:
            try:
                status_result = TBankService.check_payment_status(payment.payment_id)
                
                if not status_result.get('success'):
                    continue
                
                tbank_status = status_result.get('status')
                
                if tbank_status == 'CONFIRMED':
                    # Simulate webhook processing
                    fake_notification = {
                        'PaymentId': payment.payment_id,
                        'Status': 'CONFIRMED',
                    }
                    
                    # Process the payment
                    sub = payment.subscription
                    metadata = payment.metadata or {}
                    
                    payment.status = Payment.STATUS_SUCCEEDED
                    payment.paid_at = timezone.now()
                    payment.save()
                    
                    message = None
                    
                    # Activate subscription
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
                        sub.payment_method = 'tbank'
                        sub.save()
                        
                        # Create GDrive folder on first payment
                        if not sub.gdrive_folder_id:
                            try:
                                from .gdrive_folder_service import create_teacher_folder_on_subscription
                                create_teacher_folder_on_subscription(sub)
                            except Exception as e:
                                logger.error(f"Failed to create GDrive folder: {e}")
                        
                        logger.info(f"Sync: Subscription {sub.id} activated, plan={plan}")
                        message = f"Подписка активирована до {sub.expires_at.strftime('%d.%m.%Y')}"
                    
                    # Add storage
                    elif 'storage_gb' in metadata:
                        gb = int(metadata['storage_gb'])
                        sub.extra_storage_gb += gb
                        sub.total_paid += payment.amount
                        sub.last_payment_date = timezone.now()
                        sub.save()
                        
                        logger.info(f"Sync: Added {gb} GB to subscription {sub.id}")
                        message = f"Добавлено {gb} ГБ хранилища"
                    
                    if message:
                        try:
                            from .telegram_utils import send_telegram_notification
                            send_telegram_notification(
                                sub.user,
                                'payment_success',
                                f"💳 Оплата подтверждена!\n{message}\nСумма: {payment.amount} RUB"
                            )
                        except Exception as e:
                            logger.error(f"Failed to send telegram notification: {e}")
                    
                    processed += 1
                    
                elif tbank_status in ('REJECTED', 'CANCELED', 'REFUNDED', 'DEADLINE_EXPIRED'):
                    payment.status = Payment.STATUS_FAILED
                    payment.save()
                    logger.info(f"Sync: Payment {payment.payment_id} marked as failed: {tbank_status}")
                    failed += 1
                    
            except Exception as e:
                logger.exception(f"Error syncing payment {payment.payment_id}: {e}")
                errors.append(str(e))
        
        logger.info(f"T-Bank sync complete: processed={processed}, failed={failed}")
        return {'processed': processed, 'failed': failed, 'errors': errors}


# Convenience alias
tbank_service = TBankService()
