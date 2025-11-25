from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_request(request):
    """
    Запрос на сброс пароля
    Отправляет письмо с ссылкой для сброса пароля
    """
    email = request.data.get('email', '').strip().lower()
    
    if not email:
        return Response(
            {'error': 'Email обязателен'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
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
