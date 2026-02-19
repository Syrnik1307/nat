import logging
import traceback

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import authenticate
from .serializers import CustomTokenObtainPairSerializer

logger = logging.getLogger(__name__)

User = get_user_model()


class CaseInsensitiveTokenObtainPairSerializer(CustomTokenObtainPairSerializer):
    """Token serializer that allows case-insensitive email lookup."""

    def validate(self, attrs):
        # attrs will contain the username field (email because USERNAME_FIELD = 'email')
        username_field = self.username_field
        identifier = attrs.get(username_field)
        if identifier:
            # Try to find a user by case-insensitive match and replace the identifier
            try:
                found = User.objects.filter(**{f"{username_field}__iexact": identifier}).first()
                if found:
                    attrs[username_field] = getattr(found, username_field)
            except Exception:
                pass
        return super().validate(attrs)


class CaseInsensitiveTokenObtainPairView(TokenObtainPairView):
    """View that uses the case-insensitive serializer."""
    serializer_class = CaseInsensitiveTokenObtainPairSerializer

User = get_user_model()


class RegisterView(APIView):
    """API endpoint для регистрации новых пользователей"""
    permission_classes = [AllowAny]
    # Отключаем SessionAuthentication (CSRF) для регистрации — эндпоинт публичный
    authentication_classes = []
    # Отключаем дефолтный anon throttle (50/час слишком строг для регистрации)
    throttle_classes = []

    def post(self, request):
        logger.info(f"[RegisterView] Получен запрос: {request.data}")
        logger.info(f"[RegisterView] Host: {request.get_host()}")
        
        email = request.data.get('email')
        password = request.data.get('password')
        # FIX: request.data.get('role', 'student') возвращает None если ключ есть со значением null
        role = request.data.get('role') or 'student'
        first_name = request.data.get('first_name') or ''
        last_name = request.data.get('last_name') or ''
        middle_name = request.data.get('middle_name') or ''
        birth_date = request.data.get('birth_date')

        if not email or not password:
            logger.warning(f"[RegisterView] Пустой email или пароль: email={email!r}")
            return Response(
                {'detail': 'Email и пароль обязательны'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Нормализуем email
        email = email.strip().lower()

        # Валидация роли
        if role not in ('student', 'teacher', 'admin'):
            logger.warning(f"[RegisterView] Невалидная роль: {role!r}, ставим student")
            role = 'student'

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
            
            # FIX: Поле в модели — date_of_birth, а не birth_date
            if birth_date:
                try:
                    user.date_of_birth = birth_date
                    user.save(update_fields=['date_of_birth'])
                except Exception as e:
                    logger.warning(f"[RegisterView] Не удалось сохранить дату рождения: {e}")
            
            # Создаём TenantMembership для нового пользователя
            self._create_tenant_membership(request, user)

            # Генерируем JWT-токены сразу при регистрации
            refresh = RefreshToken.for_user(user)
            # Добавляем роль в токен (как CustomTokenObtainPairSerializer)
            refresh['role'] = user.role
            refresh['email'] = user.email
            
            logger.info(f"[RegisterView] Пользователь создан: id={user.id}, email={user.email}, role={user.role}")
            
            return Response({
                'detail': 'Пользователь успешно создан',
                'user_id': user.id,
                'email': user.email,
                'role': user.role,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }, status=status.HTTP_201_CREATED)
        except IntegrityError as e:
            logger.error(f"[RegisterView] IntegrityError: {e}\n{traceback.format_exc()}")
            return Response(
                {'detail': 'Пользователь с таким email уже существует'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"[RegisterView] Unexpected error: {e}\n{traceback.format_exc()}")
            return Response(
                {'detail': f'Ошибка создания пользователя: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _create_tenant_membership(self, request, user):
        """Создаёт TenantMembership для нового пользователя."""
        try:
            from tenants.models import TenantMembership
            tenant = getattr(request, 'tenant', None)
            if not tenant:
                # Fallback: default tenant
                from tenants.models import Tenant
                tenant = Tenant.objects.filter(
                    slug='lectiospace', status='active'
                ).first() or Tenant.objects.filter(status='active').first()
            
            if tenant:
                membership, created = TenantMembership.objects.get_or_create(
                    tenant=tenant,
                    user=user,
                    defaults={
                        'role': user.role,
                        'is_active': True,
                    }
                )
                if created:
                    logger.info(f"[RegisterView] TenantMembership создан: user={user.id}, tenant={tenant.slug}")
                else:
                    logger.info(f"[RegisterView] TenantMembership уже существовал: user={user.id}, tenant={tenant.slug}")
            else:
                logger.warning(f"[RegisterView] Не найден tenant для создания membership, user={user.id}")
        except Exception as e:
            logger.error(f"[RegisterView] Ошибка создания TenantMembership: {e}\n{traceback.format_exc()}")


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
