"""
Market API views.
"""
import logging
import uuid
from decimal import Decimal

from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Product, MarketOrder
from .serializers import ProductSerializer, MarketOrderSerializer, CreateZoomOrderSerializer
from accounts.tbank_service import TBankService

logger = logging.getLogger(__name__)


class ProductListView(APIView):
    """
    GET /api/market/products/
    List active products available for purchase.
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        products = Product.objects.filter(is_active=True).order_by('sort_order', 'title')
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)


class MyOrdersView(APIView):
    """
    GET /api/market/my-orders/
    List user's market orders.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        orders = MarketOrder.objects.filter(user=request.user).order_by('-created_at')[:20]
        serializer = MarketOrderSerializer(orders, many=True)
        return Response(serializer.data)


class CreateOrderView(APIView):
    """
    POST /api/market/buy/
    Create a new order and initiate T-Bank payment.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = CreateZoomOrderSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        product_id = data['product_id']
        
        # Get product
        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            return Response(
                {'detail': 'Товар не найден или недоступен'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Validate product type
        if product.product_type != Product.TYPE_ZOOM:
            return Response(
                {'detail': 'Этот API поддерживает только Zoom товары'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Prepare order details
        zoom_email = data.get('zoom_email', '')
        if data.get('random_email') and data.get('is_new_account'):
            # Generate random email for new account
            random_part = uuid.uuid4().hex[:8]
            zoom_email = f"lectio-{random_part}@proton.me"
        
        order_details = {
            'zoom_email': zoom_email,
            'zoom_password': data['zoom_password'],
            'contact_info': data['contact_info'].strip(),
            'is_new_account': data['is_new_account'],
            'auto_connect': data.get('auto_connect', False),
        }
        
        # Create order
        order = MarketOrder.objects.create(
            user=request.user,
            product=product,
            status=MarketOrder.STATUS_PENDING,
            total_amount=product.price,
            order_details=order_details,
        )
        
        # Create T-Bank payment
        payment_result = self._create_tbank_payment(order, request.user)
        
        if payment_result:
            order.payment_id = payment_result.get('payment_id')
            order.payment_url = payment_result.get('payment_url')
            order.save(update_fields=['payment_id', 'payment_url'])
            
            logger.info(f"Market order #{order.id} created for user {request.user.email}")
            
            return Response({
                'order_id': order.id,
                'payment_url': order.payment_url,
                'status': 'pending',
            })
        else:
            # Payment creation failed, but order is saved
            order.admin_notes = 'Ошибка создания платежа T-Bank'
            order.save(update_fields=['admin_notes'])
            
            return Response(
                {'detail': 'Не удалось создать платеж. Попробуйте позже.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _create_tbank_payment(self, order: MarketOrder, user):
        """Create T-Bank payment for market order."""
        
        if not TBankService.is_available():
            # Mock payment for development
            logger.warning("T-Bank not configured, using mock payment for market order")
            mock_id = f'mock-market-{order.id}-{int(timezone.now().timestamp())}'
            return {
                'payment_url': f'{settings.FRONTEND_URL}/profile?tab=market&mock_payment={mock_id}',
                'payment_id': mock_id,
            }
        
        # Amount in kopecks
        amount_kopecks = int(order.total_amount * 100)
        order_id = f"market-{order.id}-{int(timezone.now().timestamp())}"
        
        # Determine description
        account_type = 'Новый аккаунт' if order.is_new_account else 'Существующий аккаунт'
        description = f'Zoom ({account_type}) - Lectio Space'
        
        request_data = {
            'Amount': amount_kopecks,
            'OrderId': order_id,
            'Description': description,
            'CustomerKey': str(user.id),
            'SuccessURL': f"{settings.FRONTEND_URL}/profile?tab=market&status=success&order_id={order.id}",
            'FailURL': f"{settings.FRONTEND_URL}/profile?tab=market&status=fail&order_id={order.id}",
            'NotificationURL': f"{settings.SITE_URL}/api/market/webhook/",
            'PayType': 'O',  # One-stage payment
            'Language': 'ru',
            'DATA': {
                'market_order_id': str(order.id),
                'user_id': str(user.id),
                'product_type': order.product.product_type,
                'Email': user.email,
            }
        }
        
        result = TBankService._make_request('Init', request_data)
        
        if result.get('Success'):
            logger.info(f"T-Bank payment created for market order #{order.id}: {result['PaymentId']}")
            return {
                'payment_url': result['PaymentURL'],
                'payment_id': str(result['PaymentId']),
            }
        else:
            logger.error(f"Failed to create T-Bank payment for market order #{order.id}: {result.get('Message')}")
            return None


class MarketWebhookView(APIView):
    """
    POST /api/market/webhook/
    Handle T-Bank payment webhooks for market orders.
    IDEMPOTENT: Duplicate webhooks are safe - we check order status before processing.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        data = request.data
        logger.info(f"Market webhook received: {data}")
        
        # Verify token
        if not TBankService._verify_notification_token(data):
            logger.warning("Market webhook: Invalid token")
            return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)
        
        payment_status = data.get('Status')
        payment_id = str(data.get('PaymentId', ''))
        
        # Find order by payment_id
        try:
            order = MarketOrder.objects.get(payment_id=payment_id)
        except MarketOrder.DoesNotExist:
            logger.warning(f"Market webhook: Order not found for payment_id={payment_id}")
            return Response({'status': 'OK'})  # T-Bank expects OK even if order not found
        
        if payment_status == 'CONFIRMED':
            self._handle_payment_confirmed(order)
        elif payment_status in ['REJECTED', 'CANCELED']:
            order.status = MarketOrder.STATUS_CANCELLED
            order.save(update_fields=['status', 'updated_at'])
            logger.info(f"Market order #{order.id} cancelled (payment {payment_status})")
        elif payment_status == 'REFUNDED':
            order.status = MarketOrder.STATUS_REFUNDED
            order.save(update_fields=['status', 'updated_at'])
            logger.info(f"Market order #{order.id} refunded")
        
        return Response({'status': 'OK'})
    
    def _handle_payment_confirmed(self, order: MarketOrder):
        """
        Handle confirmed payment: update status and notify admin.
        IDEMPOTENT: If order is already PAID or beyond, skip processing.
        """
        # IDEMPOTENCY CHECK: Already processed?
        if order.status in [MarketOrder.STATUS_PAID, MarketOrder.STATUS_COMPLETED]:
            logger.info(f"Market order #{order.id} already {order.status}, skipping (idempotent)")
            return
        
        order.status = MarketOrder.STATUS_PAID
        order.paid_at = timezone.now()
        order.save(update_fields=['status', 'paid_at', 'updated_at'])
        
        logger.info(f"Market order #{order.id} PAID")
        
        # Send admin notification via Telegram
        self._send_admin_notification(order)
    
    def _send_admin_notification(self, order: MarketOrder):
        """Send Telegram notification to admin about new paid order."""
        from accounts.notifications import send_telegram_admin_alert
        
        account_type = 'Новый' if order.is_new_account else 'Существующий'
        auto_connect = 'ДА' if order.auto_connect else 'НЕТ'
        
        message = f"""💰 МАРКЕТ: НОВАЯ ОПЛАТА

Юзер: {order.user.email}
Товар: {order.product.title}
Сумма: {order.total_amount} ₽

Тип: {account_type}
Логин: {order.zoom_email or '-'}
Пароль: {order.zoom_password or '-'}
Контакты: {order.contact_info or '-'}
Авто-подключение к платформе: {auto_connect}

Заказ #{order.id}"""
        
        try:
            send_telegram_admin_alert(message)
        except Exception as e:
            logger.error(f"Failed to send admin notification for market order #{order.id}: {e}")
