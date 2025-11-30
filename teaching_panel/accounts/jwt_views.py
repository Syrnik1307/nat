from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import authenticate
from rest_framework.throttling import ScopedRateThrottle
from .serializers import CustomTokenObtainPairSerializer
from .security import register_failure, reset_failures, is_locked, lockout_remaining_seconds
import logging

User = get_user_model()


class CaseInsensitiveTokenObtainPairSerializer(CustomTokenObtainPairSerializer):
    """Сериализатор выдачи JWT с строгой проверкой пароля и case-insensitive email."""

    def validate(self, attrs):
        # Явная ручная проверка: исключаем любые сторонние сбои authenticate()
        email_field = self.username_field  # 'email'
        raw_email = (attrs.get(email_field) or '').strip()
        password = attrs.get('password') or ''

        # DEBUG LOGGING (temporary): helps diagnose prod login issues
        try:
            import logging
            logging.getLogger(__name__).info(
                "[AuthDebug] incoming login: email=%s len(password)=%s", raw_email, len(password)
            )
        except Exception:
            pass

        if not raw_email or not password:
            from rest_framework import exceptions
            raise exceptions.AuthenticationFailed('Некорректные учетные данные')

        # Case-insensitive поиск пользователя
        if is_locked(raw_email):
            from rest_framework import exceptions
            raise exceptions.AuthenticationFailed('Слишком много попыток. Аккаунт временно заблокирован')

        try:
            user = User.objects.get(**{f'{email_field}__iexact': raw_email})
        except User.DoesNotExist:
            try:
                import logging
                logging.getLogger(__name__).warning("[AuthDebug] user not found: %s", raw_email)
            except Exception:
                pass
            register_failure(raw_email)
            from rest_framework import exceptions
            raise exceptions.AuthenticationFailed('Неверный email или пароль')

        # Проверка активности
        if not user.is_active:
            try:
                import logging
                logging.getLogger(__name__).warning("[AuthDebug] user inactive: %s", raw_email)
            except Exception:
                pass
            from rest_framework import exceptions
            raise exceptions.AuthenticationFailed('Аккаунт деактивирован')

        # Строгая проверка пароля
        if not user.check_password(password):
            try:
                import logging
                logging.getLogger(__name__).warning("[AuthDebug] bad password for: %s", raw_email)
            except Exception:
                pass
            register_failure(raw_email)
            from rest_framework import exceptions
            raise exceptions.AuthenticationFailed('Неверный email или пароль')

        # Генерация токенов (используем кастомные claims в get_token)
        # Успешная авторизация: сбрасываем счётчик
        reset_failures(raw_email)
        refresh = self.get_token(user)
        data = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
        return data


class CaseInsensitiveTokenObtainPairView(TokenObtainPairView):
    """View that uses the case-insensitive serializer with login-specific throttling."""
    serializer_class = CaseInsensitiveTokenObtainPairSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

User = get_user_model()


class RegisterView(APIView):
    """API endpoint для регистрации новых пользователей"""
    permission_classes = [AllowAny]

    def post(self, request):
        print(f"[RegisterView] Получен запрос: {request.data}")
        print(f"[RegisterView] Headers: {request.headers}")
        print(f"[RegisterView] User-Agent: {request.headers.get('User-Agent', 'N/A')}")
        
        email = request.data.get('email')
        password = request.data.get('password')
        role = request.data.get('role', 'student')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        middle_name = request.data.get('middle_name', '')
        birth_date = request.data.get('birth_date')

        if not email or not password:
            return Response(
                {'detail': 'Email и пароль обязательны'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Нормализуем email (нижний регистр + trim)
        email = email.strip().lower()

        # Валидация пароля
        if len(password) < 6:
            return Response(
                {'detail': 'Пароль должен содержать минимум 6 символов'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not any(c.isupper() for c in password):
            return Response(
                {'detail': 'Пароль должен содержать хотя бы одну заглавную букву'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not any(c.islower() for c in password):
            return Response(
                {'detail': 'Пароль должен содержать хотя бы одну строчную букву'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not any(c.isdigit() for c in password):
            return Response(
                {'detail': 'Пароль должен содержать хотя бы одну цифру'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(email__iexact=email).exists():
            return Response(
                {'detail': 'Пользователь с таким email уже существует'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.create_user(
                email=email,
                password=password,
                role=role,
                first_name=first_name,
                last_name=last_name,
                middle_name=middle_name
            )
            
            # Добавить дату рождения если указана
            if birth_date:
                user.birth_date = birth_date
                user.save()
            
            # Генерация JWT токенов сразу после регистрации (соответствие фронтенду)
            try:
                refresh = RefreshToken.for_user(user)
                access_token = str(refresh.access_token)
                refresh_token = str(refresh)
            except Exception as token_err:
                print(f"[RegisterView] Ошибка генерации токенов: {token_err}")
                access_token = None
                refresh_token = None

            return Response({
                'detail': 'Пользователь успешно создан',
                'user_id': user.id,
                'email': user.email,
                'role': user.role,
                'access': access_token,
                'refresh': refresh_token,
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(
                {'detail': f'Ошибка создания пользователя: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'detail': 'refresh token required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception as e:
            return Response({'detail': f'Invalid token: {e}'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'detail': 'Logged out (refresh token blacklisted)'}, status=status.HTTP_200_OK)
