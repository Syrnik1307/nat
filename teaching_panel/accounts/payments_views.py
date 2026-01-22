"""
Payment webhook views for YooKassa and T-Bank integration
"""
import json
import hmac
import hashlib
import logging
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from .payments_service import PaymentService
from .tbank_service import TBankService

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
        from accounts.error_tracker import track_error, track_critical
        
        # БЕЗОПАСНОСТЬ: ОБЯЗАТЕЛЬНАЯ проверка подписи webhook
        webhook_secret = getattr(settings, 'YOOKASSA_WEBHOOK_SECRET', None)
        
        if not webhook_secret:
            # В production БЕЗ секрета webhooks отключены
            logger.error("YOOKASSA_WEBHOOK_SECRET not configured - webhooks disabled for security")
            track_critical(
                code='YOOKASSA_WEBHOOK_SECRET_MISSING',
                message='YooKassa webhook secret не настроен, webhook отключен',
                details={'remote_addr': request.META.get('REMOTE_ADDR')},
            )
            return JsonResponse({'error': 'Webhooks disabled - secret not configured'}, status=503)
        
        signature = request.headers.get('X-Yookassa-Signature', '')
        body = request.body.decode('utf-8')
        
        expected_signature = hmac.new(
            webhook_secret.encode('utf-8'),
            body.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            logger.warning(f"Invalid webhook signature from {request.META.get('REMOTE_ADDR')}")
            track_error(
                code='YOOKASSA_INVALID_SIGNATURE',
                message='Невалидная подпись webhook от YooKassa',
                severity='warning',
                details={'remote_addr': request.META.get('REMOTE_ADDR')},
            )
            return JsonResponse({'error': 'Invalid signature'}, status=403)
        
        # Парсим данные
        payload = json.loads(body)
        event = payload.get('event')
        
        logger.info(f"Received YooKassa webhook: {event}")
        
        # Обрабатываем событие
        if event in ['payment.succeeded', 'payment.canceled']:
            success = PaymentService.process_payment_webhook(payload)
            if success:
                return JsonResponse({'status': 'ok'})
            else:
                track_error(
                    code='YOOKASSA_PROCESSING_FAILED',
                    message=f'Ошибка обработки webhook {event}',
                    severity='critical',
                    details={'event': event, 'payment_id': payload.get('object', {}).get('id')},
                )
                return JsonResponse({'error': 'Processing failed'}, status=500)
        
        # Другие события просто логируем
        logger.info(f"Unhandled webhook event: {event}")
        return JsonResponse({'status': 'ok'})
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON in webhook")
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    except Exception as e:
        logger.exception(f"Webhook error: {e}")
        track_critical(
            code='YOOKASSA_WEBHOOK_EXCEPTION',
            message=f'Критическая ошибка webhook: {str(e)[:200]}',
            details={'exception': str(e)},
        )
        return JsonResponse({'error': 'Internal error'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def tbank_webhook(request):
    """
    Webhook endpoint для получения уведомлений от T-Bank (Тинькофф)
    
    POST /api/payments/tbank/webhook/
    
    T-Bank отправляет уведомления о статусах:
    - CONFIRMED - платёж подтверждён (успех)
    - AUTHORIZED - платёж авторизован (для двухстадийных)
    - REJECTED - платёж отклонён
    - REFUNDED - возврат выполнен
    - CANCELED - платёж отменён
    
    Ответ: HTTP 200 с телом "OK" (без кавычек)
    Docs: https://developer.tbank.ru/eacq/intro/developer/notification
    """
    try:
        body = request.body.decode('utf-8')
        
        # T-Bank sends form-urlencoded or JSON
        content_type = request.content_type or ''
        
        if 'application/json' in content_type:
            notification_data = json.loads(body)
        else:
            # Form-urlencoded - parse manually
            from urllib.parse import parse_qs
            parsed = parse_qs(body)
            notification_data = {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}
        
        logger.info(f"Received T-Bank webhook: {notification_data.get('Status', 'unknown')}")
        
        # Process notification (includes token verification)
        success = TBankService.process_notification(notification_data)
        
        if success:
            # T-Bank требует ответ "OK" (plain text)
            return HttpResponse("OK", content_type="text/plain", status=200)
        else:
            logger.warning("T-Bank notification processing returned False")
            return HttpResponse("OK", content_type="text/plain", status=200)
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON in T-Bank webhook")
        return HttpResponse("INVALID_JSON", content_type="text/plain", status=400)
    
    except Exception as e:
        logger.exception(f"T-Bank webhook error: {e}")
        # Still return OK to prevent retry flood, but log the error
        return HttpResponse("OK", content_type="text/plain", status=200)
