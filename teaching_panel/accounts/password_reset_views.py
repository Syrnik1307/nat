from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string
from django.core.cache import cache
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
import logging
from typing import Tuple

User = get_user_model()
logger = logging.getLogger(__name__)

# Rate limiting configuration
PASSWORD_RESET_MAX_ATTEMPTS = 3  # Max requests per email per window
PASSWORD_RESET_WINDOW_SECONDS = 15 * 60  # 15 minutes


def _get_rate_limit_key(email: str) -> str:
    """Generate cache key for rate limiting password reset requests."""
    return f'password_reset_attempts:{email.lower()}'


def _check_rate_limit(email: str) -> Tuple[bool, int]:
    """
    Check if password reset is rate limited for this email.
    
    Returns:
        tuple: (is_allowed, remaining_attempts)
    """
    key = _get_rate_limit_key(email)
    attempts = cache.get(key, 0)
    
    if attempts >= PASSWORD_RESET_MAX_ATTEMPTS:
        return False, 0
    
    return True, PASSWORD_RESET_MAX_ATTEMPTS - attempts - 1


def _record_attempt(email: str) -> None:
    """Record a password reset attempt for rate limiting."""
    key = _get_rate_limit_key(email)
    attempts = cache.get(key, 0)
    cache.set(key, attempts + 1, PASSWORD_RESET_WINDOW_SECONDS)


@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_request(request):
    """
    Запрос на сброс пароля
    Отправляет письмо с ссылкой для сброса пароля
    
    SECURITY: Rate limited to 3 requests per email per 15 minutes
    """
    email = request.data.get('email', '').strip().lower()
    
    if not email:
        return Response(
            {'error': 'Email обязателен'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # SECURITY: Rate limiting check
    is_allowed, remaining = _check_rate_limit(email)
    if not is_allowed:
        logger.warning(f"Password reset rate limited for: {email}")
        return Response(
            {'error': 'Слишком много попыток. Попробуйте через 15 минут.'},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    
    # Record the attempt before processing
    _record_attempt(email)
    
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        logger.info(f"Password reset requested for non-existent email: {email}")
        return Response({
            'message': 'Если email существует, на него отправлен новый пароль'
        })

    # Генерируем новый временный пароль
    temp_password = get_random_string(length=12)
    user.set_password(temp_password)
    user.save(update_fields=['password'])

    # Отправляем новый пароль на email
    try:
        subject = 'Новый пароль для вашего аккаунта - Teaching Panel'
        message = f"""
Здравствуйте, {user.first_name or user.email}!

Вы запросили восстановление доступа на платформе Teaching Panel.
Мы сгенерировали новый временный пароль:

Новый пароль: {temp_password}

Сразу после входа рекомендуем изменить пароль в настройках профиля.
Если вы не запрашивали смену пароля, немедленно обратитесь в поддержку.

---
С уважением,
Команда Teaching Panel
        """

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        logger.info(f"Temporary password sent to {user.email}")

    except Exception as e:
        logger.error(f"Failed to send new password to {user.email}: {e}")
        return Response(
            {'error': 'Не удалось отправить письмо. Попробуйте позже.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return Response({
        'message': 'Новый пароль отправлен на указанный email'
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_confirm(request):
    """
    Подтверждение сброса пароля с новым паролем
    """
    uid = request.data.get('uid')
    token = request.data.get('token')
    new_password = request.data.get('password')
    
    if not all([uid, token, new_password]):
        return Response(
            {'error': 'Все поля обязательны'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Валидация пароля
    if len(new_password) < 6:
        return Response(
            {'error': 'Пароль должен содержать минимум 6 символов'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Декодируем uid
        user_id = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=user_id)
        
        # Проверяем токен
        if not default_token_generator.check_token(user, token):
            return Response(
                {'error': 'Ссылка недействительна или истекла. Запросите сброс пароля заново.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Устанавливаем новый пароль
        user.set_password(new_password)
        user.save()
        
        logger.info(f"Password reset successful for {user.email}")
        
        return Response({
            'message': 'Пароль успешно изменен. Теперь вы можете войти с новым паролем.'
        })
        
    except (TypeError, ValueError, OverflowError, User.DoesNotExist) as e:
        logger.error(f"Password reset confirmation failed: {e}")
        return Response(
            {'error': 'Недействительная ссылка для сброса пароля'},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def password_reset_validate_token(request, uid, token):
    """
    Проверка валидности токена сброса пароля
    """
    try:
        user_id = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=user_id)
        
        if default_token_generator.check_token(user, token):
            return Response({
                'valid': True,
                'email': user.email
            })
        else:
            return Response({
                'valid': False,
                'error': 'Ссылка недействительна или истекла'
            })
            
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return Response({
            'valid': False,
            'error': 'Недействительная ссылка'
        })


# ============ НОВЫЕ API ДЛЯ ВОССТАНОВЛЕНИЯ ПАРОЛЯ ЧЕРЕЗ TELEGRAM/WHATSAPP ============

from .password_reset_sender import send_password_reset_code, verify_reset_code
from .models import PasswordResetToken
from django.utils import timezone


@api_view(['POST'])
@permission_classes([AllowAny])
def request_reset_code(request):
    """
    Запрос кода для восстановления пароля через Telegram/WhatsApp
    
    POST /accounts/api/password-reset/request-code/
    {
        "email": "user@example.com",
        "phone": "+79991234567",
        "method": "telegram"  // или "whatsapp"
    }
    """
    email = request.data.get('email', '').strip().lower()
    phone = request.data.get('phone', '').strip()
    method = request.data.get('method', 'telegram')
    
    if not email or not phone:
        return Response({
            'success': False,
            'error': 'Email и телефон обязательны'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if method not in ['telegram', 'whatsapp']:
        return Response({
            'success': False,
            'error': 'Метод должен быть telegram или whatsapp'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Отправляем код
    result = send_password_reset_code(email, phone, method)
    
    if result['success']:
        return Response({
            'success': True,
            'method': result['method'],
            'message': f'Код отправлен через {result["method"]}',
            'code': result.get('code')  # Только для тестирования
        })
    else:
        return Response({
            'success': False,
            'error': result.get('error', 'Не удалось отправить код')
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_code(request):
    """
    Проверка кода восстановления пароля
    
    POST /accounts/api/password-reset/verify-code/
    {
        "email": "user@example.com",
        "code": "123456"
    }
    """
    email = request.data.get('email', '').strip().lower()
    code = request.data.get('code', '').strip()
    
    if not email or not code:
        return Response({
            'success': False,
            'error': 'Email и код обязательны'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Проверяем код
    result = verify_reset_code(email, code)
    
    if result['success']:
        return Response({
            'success': True,
            'token': result['token'],
            'message': result['message']
        })
    else:
        return Response({
            'success': False,
            'error': result.get('error')
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def set_new_password(request):
    """
    Установка нового пароля по токену
    
    POST /accounts/api/password-reset/set-password/
    {
        "token": "abc123...",
        "new_password": "NewPassword123"
    }
    """
    token_value = request.data.get('token', '').strip()
    new_password = request.data.get('new_password', '').strip()
    
    if not token_value or not new_password:
        return Response({
            'success': False,
            'error': 'Токен и новый пароль обязательны'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Проверяем длину пароля
    if len(new_password) < 6:
        return Response({
            'success': False,
            'error': 'Пароль должен содержать минимум 6 символов'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Проверяем наличие заглавной буквы
    if not any(c.isupper() for c in new_password):
        return Response({
            'success': False,
            'error': 'Пароль должен содержать хотя бы одну заглавную букву'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Проверяем наличие строчной буквы
    if not any(c.islower() for c in new_password):
        return Response({
            'success': False,
            'error': 'Пароль должен содержать хотя бы одну строчную букву'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Проверяем наличие цифры
    if not any(c.isdigit() for c in new_password):
        return Response({
            'success': False,
            'error': 'Пароль должен содержать хотя бы одну цифру'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Находим токен
    try:
        token = PasswordResetToken.objects.get(token=token_value)
    except PasswordResetToken.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Неверный токен'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Проверяем валидность токена
    if not token.is_valid():
        return Response({
            'success': False,
            'error': 'Токен истёк или уже использован'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Устанавливаем новый пароль
    user = token.user
    user.set_password(new_password)
    user.save()
    
    # Отмечаем токен как использованный
    token.used = True
    token.used_at = timezone.now()
    token.save()
    
    return Response({
        'success': True,
        'message': 'Пароль успешно изменён'
    })
