"""
Payment webhook views for YooKassa integration
"""
import json
import hmac
import hashlib
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from .payments_service import PaymentService

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def yookassa_webhook(request):
    """
    Webhook endpoint для получения уведомлений от YooKassa
    
    POST /api/payments/yookassa/webhook/
    
    YooKassa отправляет уведомления о:
    - payment.succeeded - платёж успешен
    - payment.canceled - платёж отменён
    - refund.succeeded - возврат выполнен
    """
    try:
        # Проверка подписи (если настроен webhook secret)
        if hasattr(settings, 'YOOKASSA_WEBHOOK_SECRET') and settings.YOOKASSA_WEBHOOK_SECRET:
            signature = request.headers.get('X-Yookassa-Signature', '')
            body = request.body.decode('utf-8')
            
            expected_signature = hmac.new(
                settings.YOOKASSA_WEBHOOK_SECRET.encode('utf-8'),
                body.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                logger.warning("Invalid webhook signature")
                return JsonResponse({'error': 'Invalid signature'}, status=403)
        
        # Парсим данные
        payload = json.loads(request.body.decode('utf-8'))
        event = payload.get('event')
        
        logger.info(f"Received YooKassa webhook: {event}")
        
        # Обрабатываем событие
        if event in ['payment.succeeded', 'payment.canceled']:
            success = PaymentService.process_payment_webhook(payload)
            if success:
                return JsonResponse({'status': 'ok'})
            else:
                return JsonResponse({'error': 'Processing failed'}, status=500)
        
        # Другие события просто логируем
        logger.info(f"Unhandled webhook event: {event}")
        return JsonResponse({'status': 'ok'})
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON in webhook")
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    except Exception as e:
        logger.exception(f"Webhook error: {e}")
        return JsonResponse({'error': 'Internal error'}, status=500)
