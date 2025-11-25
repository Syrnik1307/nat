"""
Утилиты для работы с Google reCAPTCHA v3
"""
import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def verify_recaptcha(token, action=None, remote_ip=None):
    """
    Проверка reCAPTCHA токена на стороне сервера
    
    Args:
        token (str): reCAPTCHA токен с фронтенда
        action (str): Название действия (например 'register', 'login')
        remote_ip (str): IP адрес пользователя
        
    Returns:
        dict: {
            'success': bool,
            'score': float (0.0-1.0),
            'action': str,
            'message': str
        }
    """
    
    # Если reCAPTCHA отключена в настройках, пропускаем проверку
    if not settings.RECAPTCHA_ENABLED:
        logger.info('reCAPTCHA disabled in settings, skipping verification')
        return {
            'success': True,
            'score': 1.0,
            'action': action,
            'message': 'reCAPTCHA disabled'
        }
    
    if not token:
        return {
            'success': False,
            'score': 0.0,
            'action': action,
            'message': 'reCAPTCHA token is required'
        }
    
    try:
        # Отправляем запрос к Google reCAPTCHA API
        response = requests.post(
            'https://www.google.com/recaptcha/api/siteverify',
            data={
                'secret': settings.RECAPTCHA_PRIVATE_KEY,
                'response': token,
                'remoteip': remote_ip
            },
            timeout=5
        )
        
        result = response.json()
        
        # Проверяем успешность верификации
        if not result.get('success'):
            error_codes = result.get('error-codes', [])
            logger.warning(f'reCAPTCHA verification failed: {error_codes}')
            
            error_messages = {
                'missing-input-secret': 'Secret key is missing',
                'invalid-input-secret': 'Secret key is invalid',
                'missing-input-response': 'Token is missing',
                'invalid-input-response': 'Token is invalid or expired',
                'bad-request': 'Bad request',
                'timeout-or-duplicate': 'Token timeout or duplicate'
            }
            
            message = error_messages.get(error_codes[0] if error_codes else '', 'Verification failed')
            
            return {
                'success': False,
                'score': 0.0,
                'action': result.get('action', action),
                'message': message
            }
        
        # Получаем score (для v3)
        score = result.get('score', 0.0)
        result_action = result.get('action', '')
        
        # Проверяем action (если указан)
        if action and result_action != action:
            logger.warning(f'reCAPTCHA action mismatch: expected={action}, got={result_action}')
            return {
                'success': False,
                'score': score,
                'action': result_action,
                'message': f'Action mismatch: expected {action}, got {result_action}'
            }
        
        # Проверяем минимальный требуемый score
        required_score = settings.RECAPTCHA_REQUIRED_SCORE
        if score < required_score:
            logger.warning(f'reCAPTCHA score too low: {score} < {required_score}')
            return {
                'success': False,
                'score': score,
                'action': result_action,
                'message': f'Score too low: {score} (required: {required_score})'
            }
        
        # Все проверки пройдены
        logger.info(f'reCAPTCHA verification successful: score={score}, action={result_action}')
        return {
            'success': True,
            'score': score,
            'action': result_action,
            'message': 'Verification successful'
        }
        
    except requests.exceptions.RequestException as e:
        logger.error(f'reCAPTCHA API request failed: {str(e)}')
        return {
            'success': False,
            'score': 0.0,
            'action': action,
            'message': f'API request failed: {str(e)}'
        }
    except Exception as e:
        logger.error(f'reCAPTCHA verification error: {str(e)}')
        return {
            'success': False,
            'score': 0.0,
            'action': action,
            'message': f'Verification error: {str(e)}'
        }


def get_client_ip(request):
    """
    Получение IP адреса клиента из request
    
    Args:
        request: Django request object
        
    Returns:
        str: IP адрес клиента
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
