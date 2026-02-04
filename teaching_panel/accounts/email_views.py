"""
API views для email верификации
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
from .models import EmailVerification, CustomUser
from .recaptcha_utils import verify_recaptcha, get_client_ip
import logging

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
def send_verification_email(request):
    """
    Отправка email с кодом верификации
    
    POST /accounts/api/email/send-verification/
    Body: {
        "email": "user@example.com",
        "recaptcha_token": "..."  # optional
    }
    """
    email = request.data.get('email')
    recaptcha_token = request.data.get('recaptcha_token')
    
    if not email:
        return Response({
            'success': False,
            'message': 'Email обязателен'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Проверяем reCAPTCHA токен (если предоставлен)
    if recaptcha_token:
        client_ip = get_client_ip(request)
        recaptcha_result = verify_recaptcha(recaptcha_token, action='send_verification', remote_ip=client_ip)
        
        if not recaptcha_result['success']:
            return Response({
                'success': False,
                'message': 'Защита от роботов: ' + recaptcha_result['message'],
                'recaptcha_error': True
            }, status=status.HTTP_400_BAD_REQUEST)
    
    # Проверяем, существует ли пользователь с таким email
    user_exists = CustomUser.objects.filter(email=email).exists()
    
    # Если пользователь существует и уже верифицирован - возвращаем ошибку
    if user_exists:
        user = CustomUser.objects.get(email=email)
        if user.email_verified:
            return Response({
                'success': False,
                'message': 'Email уже верифицирован'
            }, status=status.HTTP_400_BAD_REQUEST)
        # Если пользователь есть, но не верифицирован - продолжаем отправку кода
    
    # Удаляем старые неподтвержденные верификации для этого email
    EmailVerification.objects.filter(
        email=email,
        is_verified=False
    ).delete()
    
    # Создаем новую верификацию
    verification = EmailVerification.objects.create(email=email)
    
    # Отправляем email асинхронно через Celery
    from .tasks import send_verification_email_task
    
    send_verification_email_task.delay(
        email=email,
        code=verification.code,
        token=str(verification.token)
    )
    
    logger.info(f'Verification email task queued for {email}')
    
    # Сразу возвращаем успех - email отправится в фоне
    return Response({
        'success': True,
        'message': 'Email отправлен успешно',
        'expires_at': verification.expires_at.isoformat()
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def resend_verification_email(request):
    """
    Повторная отправка email верификации
    
    POST /accounts/api/email/resend-verification/
    Body: {
        "email": "user@example.com"
    }
    """
    email = request.data.get('email')
    
    if not email:
        return Response({
            'success': False,
            'message': 'Email обязателен'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Проверяем последнюю верификацию
    try:
        verification = EmailVerification.objects.filter(
            email=email,
            is_verified=False
        ).latest('created_at')
        
        # Проверяем, прошла ли минута с последней отправки
        time_since_last = timezone.now() - verification.created_at
        if time_since_last < timedelta(seconds=60):
            wait_seconds = 60 - int(time_since_last.total_seconds())
            return Response({
                'success': False,
                'message': f'Подождите {wait_seconds} секунд перед повторной отправкой'
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
    except EmailVerification.DoesNotExist:
        pass
    
    # Удаляем старые верификации
    EmailVerification.objects.filter(
        email=email,
        is_verified=False
    ).delete()
    
    # Создаем новую
    verification = EmailVerification.objects.create(email=email)
    
    # Отправляем email асинхронно через Celery
    from .tasks import send_verification_email_task
    
    send_verification_email_task.delay(
        email=email,
        code=verification.code,
        token=str(verification.token)
    )
    
    logger.info(f'Verification email task queued (resend) for {email}')
    
    # Сразу возвращаем успех - email отправится в фоне
    return Response({
        'success': True,
        'message': 'Email отправлен повторно',
        'expires_at': verification.expires_at.isoformat()
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_email_code(request):
    """
    Проверка 6-значного кода верификации
    
    POST /accounts/api/email/verify-code/
    Body: {
        "email": "user@example.com",
        "code": "123456"
    }
    """
    email = request.data.get('email')
    code = request.data.get('code')
    
    if not email or not code:
        return Response({
            'success': False,
            'message': 'Email и код обязательны'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        verification = EmailVerification.objects.get(
            email=email,
            code=code,
            is_verified=False
        )
        
        # Проверяем истечение
        if verification.is_expired():
            return Response({
                'success': False,
                'message': 'Код истек. Запросите новый'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Проверяем количество попыток
        if not verification.can_retry():
            return Response({
                'success': False,
                'message': 'Превышено количество попыток. Запросите новый код'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Отмечаем как верифицированный
        verification.is_verified = True
        verification.save()
        
        logger.info(f'Email {email} verified successfully with code')
        
        return Response({
            'success': True,
            'message': 'Email успешно подтвержден',
            'token': str(verification.token)
        }, status=status.HTTP_200_OK)
        
    except EmailVerification.DoesNotExist:
        # Инкрементируем попытки, если верификация существует
        try:
            verification = EmailVerification.objects.get(
                email=email,
                is_verified=False
            )
            verification.attempts += 1
            verification.save()
        except EmailVerification.DoesNotExist:
            pass
        
        return Response({
            'success': False,
            'message': 'Неверный код или email'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def verify_email_token(request, token):
    """
    Проверка UUID токена (для ссылки в письме)
    
    GET /accounts/api/email/verify-token/<uuid:token>/
    """
    try:
        verification = EmailVerification.objects.get(
            token=token,
            is_verified=False
        )
        
        # Проверяем истечение
        if verification.is_expired():
            return Response({
                'success': False,
                'message': 'Ссылка истекла. Запросите новую'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Отмечаем как верифицированный
        verification.is_verified = True
        verification.save()
        
        logger.info(f'Email {verification.email} verified successfully with token')
        
        return Response({
            'success': True,
            'message': 'Email успешно подтвержден',
            'email': verification.email
        }, status=status.HTTP_200_OK)
        
    except EmailVerification.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Недействительная ссылка верификации'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def check_verification_status(request):
    """
    Проверка статуса верификации email
    
    POST /accounts/api/email/check-status/
    Body: {
        "email": "user@example.com"
    }
    """
    email = request.data.get('email')
    
    if not email:
        return Response({
            'success': False,
            'message': 'Email обязателен'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        verification = EmailVerification.objects.filter(
            email=email
        ).latest('created_at')
        
        return Response({
            'success': True,
            'is_verified': verification.is_verified,
            'is_expired': verification.is_expired(),
            'attempts': verification.attempts,
            'can_retry': verification.can_retry(),
            'expires_at': verification.expires_at.isoformat()
        }, status=status.HTTP_200_OK)
        
    except EmailVerification.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Верификация не найдена'
        }, status=status.HTTP_404_NOT_FOUND)
