"""
API views для SMS верификации
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .models import PhoneVerification
from .sms_service import sms_service
import re
import logging

logger = logging.getLogger(__name__)


def validate_phone_number(phone):
    """
    Валидация номера телефона
    Формат: +7XXXXXXXXXX (Россия) или +380XXXXXXXXX (Украина)
    """
    # Убираем все символы кроме цифр и +
    cleaned = re.sub(r'[^\d+]', '', phone)
    
    # Проверяем формат
    if not cleaned.startswith('+'):
        return None
    
    # Российский формат: +7 + 10 цифр
    if cleaned.startswith('+7') and len(cleaned) == 12:
        return cleaned
    
    # Украинский формат: +380 + 9 цифр
    if cleaned.startswith('+380') and len(cleaned) == 13:
        return cleaned
    
    # Другие страны (общий формат)
    if len(cleaned) >= 11 and len(cleaned) <= 15:
        return cleaned
    
    return None


@api_view(['POST'])
@permission_classes([AllowAny])
def send_verification_code(request):
    """
    Отправка кода верификации на телефон
    
    POST: {
        "phone_number": "+79991234567"
    }
    """
    phone_number = request.data.get('phone_number')
    
    if not phone_number:
        return Response(
            {'error': 'Номер телефона обязателен'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Валидация номера
    validated_phone = validate_phone_number(phone_number)
    if not validated_phone:
        return Response(
            {'error': 'Некорректный формат номера телефона. Используйте международный формат: +7XXXXXXXXXX'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Проверяем, не было ли недавней отправки (защита от спама)
    recent_verification = PhoneVerification.objects.filter(
        phone_number=validated_phone,
        created_at__gte=timezone.now() - timezone.timedelta(minutes=1)
    ).first()
    
    if recent_verification:
        return Response(
            {'error': 'Код уже был отправлен. Подождите 1 минуту перед повторной отправкой.'},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    
    # Создаем новую верификацию
    verification = PhoneVerification.objects.create(
        phone_number=validated_phone
    )
    
    # Отправляем SMS
    result = sms_service.send_verification_code(validated_phone, verification.code)
    
    if result['success']:
        logger.info(f'Verification code sent to {validated_phone}')
        return Response({
            'message': 'Код верификации отправлен на указанный номер',
            'phone_number': validated_phone,
            'expires_in': 600  # 10 минут в секундах
        })
    else:
        # Удаляем верификацию если SMS не отправлена
        verification.delete()
        logger.error(f'Failed to send SMS to {validated_phone}: {result["message"]}')
        return Response(
            {'error': f'Ошибка отправки SMS: {result["message"]}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_code(request):
    """
    Проверка кода верификации
    
    POST: {
        "phone_number": "+79991234567",
        "code": "123456"
    }
    """
    phone_number = request.data.get('phone_number')
    code = request.data.get('code')
    
    if not phone_number or not code:
        return Response(
            {'error': 'Номер телефона и код обязательны'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Валидация номера
    validated_phone = validate_phone_number(phone_number)
    if not validated_phone:
        return Response(
            {'error': 'Некорректный формат номера телефона'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Ищем последнюю неверифицированную запись
    verification = PhoneVerification.objects.filter(
        phone_number=validated_phone,
        is_verified=False
    ).order_by('-created_at').first()
    
    if not verification:
        return Response(
            {'error': 'Код верификации не найден. Запросите новый код.'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Проверяем истечение
    if verification.is_expired():
        return Response(
            {'error': 'Код верификации истёк. Запросите новый код.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Проверяем количество попыток
    if not verification.can_retry():
        return Response(
            {'error': 'Превышено количество попыток. Запросите новый код.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Увеличиваем счетчик попыток
    verification.attempts += 1
    
    # Проверяем код
    if verification.code == code:
        verification.is_verified = True
        verification.save()
        
        logger.info(f'Phone {validated_phone} verified successfully')
        
        return Response({
            'message': 'Номер телефона успешно верифицирован',
            'verified': True,
            'phone_number': validated_phone
        })
    else:
        verification.save()
        
        attempts_left = 3 - verification.attempts
        logger.warning(f'Invalid verification code for {validated_phone}. Attempts left: {attempts_left}')
        
        return Response(
            {
                'error': 'Неверный код верификации',
                'attempts_left': attempts_left
            },
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def resend_verification_code(request):
    """
    Повторная отправка кода верификации
    
    POST: {
        "phone_number": "+79991234567"
    }
    """
    phone_number = request.data.get('phone_number')
    
    if not phone_number:
        return Response(
            {'error': 'Номер телефона обязателен'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Валидация номера
    validated_phone = validate_phone_number(phone_number)
    if not validated_phone:
        return Response(
            {'error': 'Некорректный формат номера телефона'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Помечаем старые коды как истёкшие (обнуляем expires_at)
    PhoneVerification.objects.filter(
        phone_number=validated_phone,
        is_verified=False
    ).update(expires_at=timezone.now())
    
    # Создаем новую верификацию
    verification = PhoneVerification.objects.create(
        phone_number=validated_phone
    )
    
    # Отправляем SMS
    result = sms_service.send_verification_code(validated_phone, verification.code)
    
    if result['success']:
        logger.info(f'Verification code resent to {validated_phone}')
        return Response({
            'message': 'Новый код верификации отправлен',
            'phone_number': validated_phone,
            'expires_in': 600
        })
    else:
        verification.delete()
        logger.error(f'Failed to resend SMS to {validated_phone}: {result["message"]}')
        return Response(
            {'error': f'Ошибка отправки SMS: {result["message"]}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
