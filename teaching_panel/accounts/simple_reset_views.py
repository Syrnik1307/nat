"""
Simplified Password Reset - ОТДЕЛЬНЫЙ МОДУЛЬ
============================================
Простейший сброс пароля без email-подтверждения.
Изолирован от существующей auth системы.

SECURITY TRADE-OFF: Принимаем риск ради простоты.
Этот endpoint предназначен для случаев когда:
1. Пользователь заблокирован (lockout)
2. Пользователь забыл пароль
3. Telegram-восстановление не работает

Добавлен: 2026-02-01
"""
from __future__ import annotations
from typing import Tuple
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from django.core.cache import cache
import logging
import re

logger = logging.getLogger(__name__)
User = get_user_model()


class SimpleResetThrottle(AnonRateThrottle):
    """
    Строгий rate limit: 5 запросов в минуту на IP.
    Защита от brute-force подбора email'ов.
    """
    rate = '5/min'  # DRF поддерживает: 's' (sec), 'm' (min), 'h' (hour), 'd' (day)
    scope = 'simple_password_reset'


def _validate_password(password: str) -> Tuple[bool, str]:
    """Проверка минимальных требований к паролю."""
    if not password:
        return False, 'Пароль обязателен'
    if len(password) < 8:
        return False, 'Минимум 8 символов'
    if not re.search(r'[A-ZА-Я]', password):
        return False, 'Нужна хотя бы одна заглавная буква'
    if not re.search(r'[a-zа-я]', password):
        return False, 'Нужна хотя бы одна строчная буква'
    if not re.search(r'[0-9]', password):
        return False, 'Нужна хотя бы одна цифра'
    return True, ''


def _clear_lockout(email: str) -> None:
    """Сброс блокировки для email."""
    email_lower = email.lower()
    fail_key = f'login_fail:{email_lower}'
    lock_key = f'login_lock:{email_lower}'
    cache.delete_many([fail_key, lock_key])


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([SimpleResetThrottle])
def simple_password_reset(request):
    """
    Простой сброс пароля без email-подтверждения.
    
    POST /api/accounts/simple-reset/
    Body: {"email": "user@example.com", "new_password": "NewPassword123"}
    
    Ответы:
    - 200: Пароль успешно изменён
    - 400: Некорректные данные
    - 404: Пользователь не найден
    - 429: Слишком много запросов
    """
    email = (request.data.get('email') or '').strip().lower()
    new_password = request.data.get('new_password') or ''
    
    # Валидация email
    if not email:
        return Response(
            {'error': 'Email обязателен'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Валидация пароля
    is_valid, error_msg = _validate_password(new_password)
    if not is_valid:
        return Response(
            {'error': error_msg},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Поиск пользователя (case-insensitive)
    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        # НЕ говорим что email не найден (защита от enum)
        # Но для UX всё-таки скажем (trade-off принят)
        logger.warning(f"[SimpleReset] Email not found: {email}")
        return Response(
            {'error': 'Пользователь с таким email не найден'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Проверка что пользователь активен
    if not user.is_active:
        return Response(
            {'error': 'Аккаунт деактивирован. Обратитесь в поддержку.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Сброс пароля
    user.set_password(new_password)
    user.save(update_fields=['password'])
    
    # КРИТИЧНО: Сброс блокировки
    _clear_lockout(email)
    
    logger.info(f"[SimpleReset] Password reset for user {user.id} ({email})")
    
    return Response({
        'message': 'Пароль успешно изменён. Теперь вы можете войти.',
        'email': email
    })
