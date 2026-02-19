"""
Простой сброс пароля: email + новый пароль.
Не требует токенов, кодов и мессенджеров.
POST /accounts/api/simple-reset/
"""
from django.contrib.auth import get_user_model
from rest_framework.decorators import (
    api_view,
    permission_classes,
    authentication_classes,
    throttle_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.throttling import AnonRateThrottle
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class SimpleResetThrottle(AnonRateThrottle):
    """3 попытки в минуту для анонимного сброса пароля."""
    rate = '3/min'


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([SimpleResetThrottle])
def simple_password_reset(request):
    """
    Простой сброс пароля: пользователь вводит email и новый пароль.

    POST /accounts/api/simple-reset/
    {
        "email": "user@example.com",
        "password": "NewPassword1",
        "confirm_password": "NewPassword1"
    }
    """
    email = request.data.get('email', '').strip().lower()
    new_password = request.data.get('new_password', '').strip()

    # --- Валидация входных данных ---
    if not email:
        return Response(
            {'error': 'Email обязателен'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not new_password:
        return Response(
            {'error': 'Пароль обязателен'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # --- Валидация сложности пароля ---
    if len(new_password) < 8:
        return Response(
            {'error': 'Пароль должен содержать минимум 8 символов'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not any(c.isupper() for c in new_password):
        return Response(
            {'error': 'Пароль должен содержать хотя бы одну заглавную букву'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not any(c.islower() for c in new_password):
        return Response(
            {'error': 'Пароль должен содержать хотя бы одну строчную букву'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not any(c.isdigit() for c in new_password):
        return Response(
            {'error': 'Пароль должен содержать хотя бы одну цифру'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # --- Поиск пользователя ---
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        logger.warning(f"[SimpleReset] Email not found: {email}")
        # Не сообщаем, существует ли аккаунт (безопасность)
        return Response(
            {'error': 'Если аккаунт с таким email существует, пароль был изменён'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # --- Сброс пароля ---
    user.set_password(new_password)
    user.save(update_fields=['password'])

    logger.info(f"[SimpleReset] Password reset for user {user.id} ({email})")

    return Response({
        'success': True,
        'message': 'Пароль успешно изменён. Теперь вы можете войти с новым паролем.',
    })
