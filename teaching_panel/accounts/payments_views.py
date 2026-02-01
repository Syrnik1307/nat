"""
Payment webhook views for YooKassa and T-Bank integration

Security features:
- HMAC signature verification
- IP whitelist validation
- Rate limiting via nginx
"""
import json
import hmac
import hashlib
import logging
from ipaddress import ip_address, ip_network
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from .payments_service import PaymentService
from .tbank_service import TBankService

logger = logging.getLogger(__name__)


# =============================================================================
# IP WHITELIST FOR PAYMENT WEBHOOKS
# =============================================================================
# YooKassa IP ranges: https://yookassa.ru/developers/using-api/webhooks#ip
YOOKASSA_ALLOWED_IPS = [
    '185.71.76.0/27',
    '185.71.77.0/27',
    '77.75.153.0/25',
    '77.75.154.128/25',
    '77.75.156.11/32',
    '77.75.156.35/32',
    '77.75.154.128/25',
    '2a02:5180::/32',  # IPv6
]

# T-Bank IP ranges: https://developer.tbank.ru/eacq/intro/developer/notification
# T-Bank uses different IPs for test and production
TBANK_ALLOWED_IPS = [
    '91.194.226.0/23',
    '91.194.224.0/23',
    '193.124.60.0/23',
    '193.124.62.0/23',
    '194.226.30.0/23',
    '194.226.28.0/23',
    # Sandbox/test IPs
    '91.194.226.181/32',
    '91.194.226.182/32',
    '91.194.227.181/32',
]


def _get_client_ip(request) -> str:
    """Extract real client IP from request, handling proxies."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # Take the first IP in the chain (original client)
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '')
    return ip


def _is_ip_in_whitelist(ip_str: str, allowed_ranges: list) -> bool:
    """Check if IP is in any of the allowed CIDR ranges."""
    if not ip_str:
        return False
    
    # Skip IP check in DEBUG mode for local testing
    if getattr(settings, 'DEBUG', False):
        logger.debug(f"IP whitelist check skipped in DEBUG mode for {ip_str}")
        return True
    
    try:
        client_ip = ip_address(ip_str)
        for cidr in allowed_ranges:
            try:
                if client_ip in ip_network(cidr, strict=False):
                    return True
            except ValueError:
                continue
        return False
    except ValueError as e:
        logger.warning(f"Invalid IP address format: {ip_str} - {e}")
        return False


def _verify_webhook_ip(request, allowed_ranges: list, service_name: str) -> tuple:
    """
    Verify that webhook request comes from trusted IP.
    Returns (is_valid, client_ip, error_response or None)
    """
    client_ip = _get_client_ip(request)
    
    if not _is_ip_in_whitelist(client_ip, allowed_ranges):
        logger.warning(f"{service_name} webhook from untrusted IP: {client_ip}")
        try:
            from accounts.error_tracker import track_error
            track_error(
                code=f'{service_name.upper()}_UNTRUSTED_IP',
                message=f'Webhook от недоверенного IP: {client_ip}',
                severity='warning',
                details={
                    'client_ip': client_ip,
                    'service': service_name,
                    'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200],
                },
            )
        except Exception:
            pass
        return False, client_ip, JsonResponse(
            {'error': 'Forbidden - IP not in whitelist'},
            status=403
        )
    
    return True, client_ip, None


@csrf_exempt
@require_http_methods(["POST"])
def yookassa_webhook(request):
    """
    Webhook endpoint для получения уведомлений от YooKassa
    
    POST /api/payments/yookassa/webhook/
    
    Security layers:
    1. IP whitelist verification
    2. HMAC signature verification
    3. Webhook secret required
    
    YooKassa отправляет уведомления о:
    - payment.succeeded - платёж успешен
    - payment.canceled - платёж отменён
    - refund.succeeded - возврат выполнен
    """
    try:
        from accounts.error_tracker import track_error, track_critical
        
        # SECURITY LAYER 1: IP whitelist check
        ip_valid, client_ip, ip_error = _verify_webhook_ip(
            request, YOOKASSA_ALLOWED_IPS, 'YooKassa'
        )
        if not ip_valid:
            return ip_error
        
        # SECURITY LAYER 2: Webhook secret must be configured
        webhook_secret = getattr(settings, 'YOOKASSA_WEBHOOK_SECRET', None)
        
        if not webhook_secret:
            # В production БЕЗ секрета webhooks отключены
            logger.error("YOOKASSA_WEBHOOK_SECRET not configured - webhooks disabled for security")
            track_critical(
                code='YOOKASSA_WEBHOOK_SECRET_MISSING',
                message='YooKassa webhook secret не настроен, webhook отключен',
                details={'remote_addr': client_ip},
            )
            return JsonResponse({'error': 'Webhooks disabled - secret not configured'}, status=503)
        
        # SECURITY LAYER 3: HMAC signature verification
        signature = request.headers.get('X-Yookassa-Signature', '')
        body = request.body.decode('utf-8')
        
        expected_signature = hmac.new(
            webhook_secret.encode('utf-8'),
            body.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            logger.warning(f"Invalid webhook signature from {client_ip}")
            track_error(
                code='YOOKASSA_INVALID_SIGNATURE',
                message='Невалидная подпись webhook от YooKassa',
                severity='warning',
                details={'remote_addr': client_ip},
            )
            return JsonResponse({'error': 'Invalid signature'}, status=403)
        
        # Парсим данные
        payload = json.loads(body)
        event = payload.get('event')
        
        logger.info(f"Received YooKassa webhook: {event} from {client_ip}")
        
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
    
    Security layers:
    1. IP whitelist verification
    2. Token (signature) verification in TBankService
    
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
        # SECURITY LAYER 1: IP whitelist check
        ip_valid, client_ip, ip_error = _verify_webhook_ip(
            request, TBANK_ALLOWED_IPS, 'TBank'
        )
        if not ip_valid:
            # T-Bank expects "OK" even on errors to prevent retries
            # But for security violations we return proper error
            return HttpResponse("FORBIDDEN", content_type="text/plain", status=403)
        
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
        
        logger.info(f"Received T-Bank webhook: {notification_data.get('Status', 'unknown')} from {client_ip}")
        
        # SECURITY LAYER 2: Token verification inside TBankService.process_notification
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
