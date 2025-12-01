from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework import status
from django.utils import timezone
from django.conf import settings

from .serializers import UserProfileSerializer, NotificationSettingsSerializer
from .models import CustomUser, PasswordResetToken, NotificationSettings
from .telegram_utils import (
    generate_link_code_for_user,
    link_account_with_code,
    TelegramVerificationError,
    unlink_user_telegram,
)


class MeView(APIView):
    """Возвращает и обновляет профиль текущего пользователя"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def users_list(request):
    """Возвращает список всех пользователей для создания чатов"""
    users = CustomUser.objects.filter(is_active=True).order_by('first_name', 'last_name')
    serializer = UserProfileSerializer(users, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """Смена пароля текущего пользователя"""
    user = request.user
    old_password = request.data.get('old_password')
    new_password = request.data.get('new_password')
    
    if not old_password or not new_password:
        return Response(
            {'detail': 'Требуются оба поля: old_password и new_password'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Проверяем старый пароль
    if not user.check_password(old_password):
        return Response(
            {'detail': 'Неверный текущий пароль'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Валидация нового пароля
    if len(new_password) < 8:
        return Response(
            {'detail': 'Пароль должен содержать минимум 8 символов'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not any(c.isupper() for c in new_password):
        return Response(
            {'detail': 'Пароль должен содержать хотя бы одну заглавную букву'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not any(c.islower() for c in new_password):
        return Response(
            {'detail': 'Пароль должен содержать хотя бы одну строчную букву'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not any(c.isdigit() for c in new_password):
        return Response(
            {'detail': 'Пароль должен содержать хотя бы одну цифру'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Устанавливаем новый пароль
    user.set_password(new_password)
    user.save()
    
    return Response(
        {'detail': 'Пароль успешно изменён'},
        status=status.HTTP_200_OK
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def link_telegram(request):
    """Deprecated endpoint kept for backward compatibility."""
    return Response(
        {'detail': 'Используйте новый процесс привязки через Telegram бота и одноразовый код.'},
        status=status.HTTP_410_GONE
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def unlink_telegram(request):
    """Отвязка Telegram от аккаунта"""
    user = request.user

    if not user.telegram_id:
        return Response(
            {'detail': 'Telegram не привязан'},
            status=status.HTTP_400_BAD_REQUEST
        )

    unlink_user_telegram(user)

    return Response(
        {'detail': 'Telegram успешно отвязан'},
        status=status.HTTP_200_OK
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_telegram_code(request):
    """Создаёт новый одноразовый код для привязки Telegram."""
    code_obj = generate_link_code_for_user(request.user)
    bot_username = getattr(settings, 'TELEGRAM_BOT_USERNAME', '')
    deep_link = f"https://t.me/{bot_username}?start={code_obj.code}" if bot_username else ''

    return Response(
        {
            'code': code_obj.code,
            'expires_at': code_obj.expires_at.isoformat(),
            'bot_username': bot_username,
            'deep_link': deep_link,
        },
        status=status.HTTP_201_CREATED
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_telegram(request):
    """Подтверждает код привязки. Используется Telegram-ботом."""
    secret = getattr(settings, 'TELEGRAM_BOT_WEBHOOK_SECRET', '')
    if secret:
        header = request.headers.get('X-Bot-Secret')
        if header != secret:
            return Response({'detail': 'Недостаточно прав'}, status=status.HTTP_403_FORBIDDEN)

    data = request.data
    code = data.get('code')
    telegram_id = data.get('telegram_id')
    telegram_username = data.get('telegram_username', '')
    telegram_chat_id = data.get('telegram_chat_id', '')

    try:
        result = link_account_with_code(
            code=code,
            telegram_id=telegram_id,
            telegram_username=telegram_username,
            telegram_chat_id=telegram_chat_id,
        )
    except TelegramVerificationError as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(
        {
            'detail': 'Telegram успешно привязан',
            'email': result.user.email,
            'telegram_username': result.user.telegram_username,
        },
        status=status.HTTP_200_OK
    )


@api_view(['POST'])
def request_password_reset(request):
    """Запрос на восстановление пароля (публичный endpoint)"""
    email = request.data.get('email', '').strip().lower()
    
    if not email:
        return Response(
            {'detail': 'Требуется email'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        user = CustomUser.objects.get(email=email)
    except CustomUser.DoesNotExist:
        # Не сообщаем, что пользователь не найден (безопасность)
        return Response(
            {'detail': 'Если аккаунт существует, инструкции отправлены'},
            status=status.HTTP_200_OK
        )
    
    # Проверяем, привязан ли подтвержденный Telegram
    if not user.telegram_id or not user.telegram_verified:
        return Response(
            {
                'detail': 'Telegram не привязан или не подтверждён. Привяжите чат через профиль.',
                'telegram_required': True
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Генерируем токен (будет отправлен через Telegram бота)
    reset_token = PasswordResetToken.generate_token(user, expires_in_minutes=15)
    
    # В реальности здесь должна быть отправка уведомления в Telegram
    # Но это делает сам бот при команде /reset
    
    return Response(
        {
            'detail': 'Откройте Telegram и отправьте команду /reset нашему боту',
            'telegram_linked': True
        },
        status=status.HTTP_200_OK
    )


@api_view(['POST'])
def reset_password_with_token(request):
    """Сброс пароля по токену из Telegram"""
    token = request.data.get('token', '').strip()
    new_password = request.data.get('new_password', '').strip()
    
    if not token or not new_password:
        return Response(
            {'detail': 'Требуются поля: token и new_password'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        reset_token = PasswordResetToken.objects.get(token=token)
    except PasswordResetToken.DoesNotExist:
        return Response(
            {'detail': 'Неверный или истекший токен'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not reset_token.is_valid():
        return Response(
            {'detail': 'Токен истёк или уже использован'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Валидация пароля
    if len(new_password) < 8:
        return Response(
            {'detail': 'Пароль должен содержать минимум 8 символов'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Сбрасываем пароль
    user = reset_token.user
    user.set_password(new_password)
    user.save()
    
    # Помечаем токен как использованный
    reset_token.used = True
    reset_token.used_at = timezone.now()
    reset_token.save()
    
    return Response(
        {
            'detail': 'Пароль успешно изменён',
            'email': user.email
        },
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_telegram_status(request):
    """Проверка статуса привязки Telegram"""
    user = request.user

    return Response(
        {
            'telegram_linked': bool(user.telegram_id),
            'telegram_id': user.telegram_id or None,
            'telegram_username': user.telegram_username or None,
            'telegram_verified': user.telegram_verified,
        },
        status=status.HTTP_200_OK
    )


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def notification_settings_view(request):
    settings_obj, _ = NotificationSettings.objects.get_or_create(user=request.user)

    if request.method == 'GET':
        serializer = NotificationSettingsSerializer(settings_obj)
        return Response(serializer.data)

    serializer = NotificationSettingsSerializer(settings_obj, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)
