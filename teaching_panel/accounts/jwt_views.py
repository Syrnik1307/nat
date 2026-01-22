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
from .bot_protection import (
    get_client_fingerprint, 
    get_client_ip,
    calculate_bot_score,
    is_fingerprint_banned,
    ban_fingerprint,
    check_registration_limit,
    record_registration,
    check_failed_login_limit,
    record_failed_login,
    reset_failed_logins,
    BOT_DETECTION_CONFIG,
)
from .requests_notifications import notify_new_registration
import logging
import json
import os

logger = logging.getLogger(__name__)
User = get_user_model()


class CaseInsensitiveTokenObtainPairSerializer(CustomTokenObtainPairSerializer):
    """Сериализатор выдачи JWT с строгой проверкой пароля и case-insensitive email.
    
    Поддерживает remember_me: при True выдаёт refresh token на 365 дней.
    """

    def validate(self, attrs):
        # Явная ручная проверка: исключаем любые сторонние сбои authenticate()
        email_field = self.username_field  # 'email'
        raw_email = (attrs.get(email_field) or '').strip()
        password = attrs.get('password') or ''

        auth_debug = os.environ.get('AUTH_DEBUG', '0') == '1'
        if auth_debug:
            logger.info("[AuthDebug] incoming login: email=%s password_len=%s", raw_email, len(password))

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
            if auth_debug:
                logger.warning("[AuthDebug] user not found: %s", raw_email)
            register_failure(raw_email)
            from rest_framework import exceptions
            raise exceptions.AuthenticationFailed('Неверный email или пароль')

        # Проверка активности
        if not user.is_active:
            if auth_debug:
                logger.warning("[AuthDebug] user inactive: %s", raw_email)
            from rest_framework import exceptions
            raise exceptions.AuthenticationFailed('Аккаунт деактивирован')

        # Строгая проверка пароля
        if not user.check_password(password):
            if auth_debug:
                logger.warning("[AuthDebug] bad password for: %s", raw_email)
            register_failure(raw_email)
            from rest_framework import exceptions
            raise exceptions.AuthenticationFailed('Неверный email или пароль')

        # Генерация токенов (используем кастомные claims в get_token)
        # Успешная авторизация: сбрасываем счётчик
        reset_failures(raw_email)
        refresh = self.get_token(user)
        
        # Поддержка remember_me: продлеваем refresh token до 365 дней
        remember_me_raw = self.context.get('request') and self.context['request'].data.get('remember_me')
        remember_me = bool(remember_me_raw)
        if remember_me:
            from datetime import timedelta
            refresh.set_exp(lifetime=timedelta(days=365))
        
        data = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
        return data


class CaseInsensitiveTokenObtainPairView(TokenObtainPairView):
    """View that uses the case-insensitive serializer with login-specific throttling.
    
    Защита от ботов:
    - Device Fingerprinting для бана по железу
    - Rate Limiting по fingerprint для неудачных попыток
    - Сброс счётчика при успешном входе
    """
    serializer_class = CaseInsensitiveTokenObtainPairSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

    def post(self, request, *args, **kwargs):
        client_ip = get_client_ip(request)
        fingerprint, fp_data = get_client_fingerprint(request)
        
        # Проверяем бан устройства
        is_banned, ban_reason = is_fingerprint_banned(fingerprint)
        if is_banned:
            logger.warning(f"[Login] Banned device: {fingerprint[:8]}..., ip={client_ip}")

            try:
                from teaching_panel.observability.process_events import emit_process_event

                email = (request.data.get('email') or request.data.get('username') or '').strip()
                emit_process_event(
                    event_type='login_device_banned',
                    severity='warning',
                    context={
                        'email': email,
                        'ip': client_ip,
                        'fingerprint_prefix': f"{fingerprint[:8]}..." if fingerprint else None,
                        'ban_reason': ban_reason,
                    },
                    dedupe_seconds=1800,
                )
            except Exception:
                pass

            return Response(
                {'detail': 'Доступ с этого устройства заблокирован', 'error': 'device_banned'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Проверяем лимит неудачных попыток
        if not check_failed_login_limit(fingerprint):
            logger.warning(f"[Login] Too many failed attempts: {fingerprint[:8]}...")
            ban_fingerprint(fingerprint, 'too_many_failed_logins', duration_hours=1)

            try:
                from teaching_panel.observability.process_events import emit_process_event

                email = (request.data.get('email') or request.data.get('username') or '').strip()
                emit_process_event(
                    event_type='login_device_rate_limited',
                    severity='warning',
                    context={
                        'email': email,
                        'ip': client_ip,
                        'fingerprint_prefix': f"{fingerprint[:8]}..." if fingerprint else None,
                        'reason': 'too_many_failed_logins',
                        'ban_hours': 1,
                    },
                    dedupe_seconds=1800,
                )
            except Exception:
                pass

            return Response(
                {'detail': 'Слишком много неудачных попыток. Устройство временно заблокировано.', 'error': 'rate_limit'},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        email = (request.data.get('email') or request.data.get('username') or '').strip()
        logger.info(f"[Login] Attempt: email={email}, ip={client_ip}")
        
        # Вызываем оригинальный метод
        response = super().post(request, *args, **kwargs)
        
        # Если успешный вход - сбрасываем счётчик неудачных попыток
        if response.status_code == 200:
            reset_failed_logins(fingerprint)
            logger.info(f"[Login] Success: email={email}")
        else:
            # Неудачный вход - записываем
            record_failed_login(fingerprint)
            logger.warning(f"[Login] Failed: email={email}, status={response.status_code}")
        
        return response


class DirectTokenView(APIView):
    """Прямой endpoint для диагностики: минует authenticate() и SimpleJWT view.
    Принимает email+password, кейс-инсенситив email, строгая проверка пароля,
    возвращает access/refresh с теми же кастомными claims.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email = (request.data.get('email') or '').strip()
        password = request.data.get('password') or ''
        if os.environ.get('AUTH_DEBUG', '0') == '1':
            logger.info("[AuthDebug] DirectTokenView payload: email=%s len(password)=%s ct=%s", email, len(password), request.content_type)
        if not email or not password:
            return Response({'detail': 'Некорректные учетные данные'}, status=status.HTTP_400_BAD_REQUEST)

        if is_locked(email):
            return Response({'detail': 'Слишком много попыток. Аккаунт временно заблокирован'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            register_failure(email)
            return Response({'detail': 'Неверный email или пароль'}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({'detail': 'Аккаунт деактивирован'}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.check_password(password):
            register_failure(email)
            return Response({'detail': 'Неверный email или пароль'}, status=status.HTTP_401_UNAUTHORIZED)

        reset_failures(email)
        refresh = CustomTokenObtainPairSerializer.get_token(CustomTokenObtainPairSerializer, user)
        data = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
        return Response(data, status=status.HTTP_200_OK)

User = get_user_model()


class RegisterView(APIView):
    """API endpoint для регистрации новых пользователей
    
    Защита от ботов:
    - Device Fingerprinting для бана по железу
    - Behavioral Analysis для определения ботов
    - Rate Limiting по fingerprint
    - Honeypot detection
    """
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'  # Используем login rate для регистрации тоже

    def post(self, request):
        client_ip = get_client_ip(request)
        
        # === BOT PROTECTION ===
        fingerprint, fp_data = get_client_fingerprint(request)
        
        # Проверяем бан устройства
        is_banned, ban_reason = is_fingerprint_banned(fingerprint)
        if is_banned:
            logger.warning(f"[RegisterView] Banned device: {fingerprint[:8]}..., ip={client_ip}")
            return Response(
                {'detail': 'Доступ с этого устройства заблокирован', 'error': 'device_banned'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Извлекаем поведенческие данные
        behavioral_data = request.data.get('behavioralData', {})
        
        # Проверяем honeypot
        honeypot_value = request.data.get('website', '') or request.data.get('honeypot', '')
        if honeypot_value:
            logger.warning(f"[RegisterView] Honeypot triggered: ip={client_ip}")
            ban_fingerprint(fingerprint, 'honeypot_triggered')
            return Response(
                {'detail': 'Подозрительная активность обнаружена'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Вычисляем bot score
        bot_score = calculate_bot_score(request, fp_data, behavioral_data)
        
        if bot_score >= BOT_DETECTION_CONFIG['bot_score_threshold']:
            logger.warning(f"[RegisterView] Bot detected: score={bot_score}, ip={client_ip}")
            ban_fingerprint(fingerprint, f'bot_score_{bot_score}')
            return Response(
                {'detail': 'Подозрительная активность обнаружена', 'error': 'bot_detected'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Проверяем лимит регистраций с этого устройства
        if not check_registration_limit(fingerprint):
            logger.warning(f"[RegisterView] Registration limit exceeded: {fingerprint[:8]}...")
            return Response(
                {'detail': 'Превышен лимит регистраций с этого устройства. Попробуйте позже.', 'error': 'rate_limit'},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        # === ORIGINAL REGISTRATION LOGIC ===
        logger.info(f"[RegisterView] Request from ip={client_ip}, bot_score={bot_score}")
        
        email = request.data.get('email')
        password = request.data.get('password')
        role = request.data.get('role', 'student')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        middle_name = request.data.get('middle_name', '')
        birth_date = request.data.get('birth_date')
        # Реферальные и UTM поля
        referral_code = (request.data.get('referral_code') or '').strip()[:32]
        utm_source = (request.data.get('utm_source') or '').strip()[:64]
        utm_medium = (request.data.get('utm_medium') or '').strip()[:64]
        utm_campaign = (request.data.get('utm_campaign') or '').strip()[:64]
        channel = (request.data.get('channel') or '').strip()[:64]
        ref_url = (request.data.get('ref_url') or '').strip()[:500]
        cookie_id = (request.data.get('cookie_id') or '').strip()[:64]

        # Debug log for registration data
        logger.info(f"[RegisterView] Data: email={email}, has_password={bool(password)}, role={role}, first_name={first_name}, last_name={last_name}")

        if not email or not password:
            logger.warning(f"[RegisterView] Missing email or password: email={email}, has_password={bool(password)}")
            return Response(
                {'detail': 'Email и пароль обязательны'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Нормализуем email (нижний регистр + trim)
        email = email.strip().lower()

        # Валидация пароля
        if len(password) < 6:
            logger.warning(f"[RegisterView] Password too short: len={len(password)}")
            return Response(
                {'detail': 'Пароль должен содержать минимум 6 символов'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not any(c.isupper() for c in password):
            logger.warning(f"[RegisterView] Password missing uppercase")
            return Response(
                {'detail': 'Пароль должен содержать хотя бы одну заглавную букву'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not any(c.islower() for c in password):
            logger.warning(f"[RegisterView] Password missing lowercase")
            return Response(
                {'detail': 'Пароль должен содержать хотя бы одну строчную букву'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not any(c.isdigit() for c in password):
            logger.warning(f"[RegisterView] Password missing digit")
            return Response(
                {'detail': 'Пароль должен содержать хотя бы одну цифру'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(email__iexact=email).exists():
            logger.warning(f"[RegisterView] Email already exists: {email}")
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
            
            # Если задан referral_code — привязываем пригласившего
            # Сначала проверяем ReferralLink (admin-созданные ссылки), потом referral_code пользователя
            try:
                if referral_code:
                    from .models import ReferralLink
                    # Проверяем, есть ли такой код в ReferralLink
                    ref_link = ReferralLink.objects.filter(code__iexact=referral_code, is_active=True).first()
                    if ref_link:
                        # Увеличиваем счётчик регистраций для этой ссылки
                        ref_link.increment_registrations()
                        logger.info(f"[RegisterView] ReferralLink {ref_link.code} registration count incremented for {email}")
                    else:
                        # Если нет такой ссылки, пробуем найти пользователя с этим referral_code
                        inviter = User.objects.filter(referral_code__iexact=referral_code).first()
                        if inviter and inviter.id != user.id:
                            user.referred_by = inviter
                            user.save(update_fields=['referred_by'])
            except Exception as ref_err:
                logger.warning(f"[RegisterView] referral assign error: {ref_err}")

            # Сохраним атрибуцию для аналитики
            try:
                from .models import ReferralAttribution
                ReferralAttribution.objects.create(
                    user=user,
                    referrer=user.referred_by if hasattr(user, 'referred_by') else None,
                    referral_code=referral_code or '',
                    utm_source=utm_source or '',
                    utm_medium=utm_medium or '',
                    utm_campaign=utm_campaign or '',
                    channel=channel or '',
                    ref_url=ref_url or '',
                    cookie_id=cookie_id or ''
                )
            except Exception as attr_err:
                logger.warning(f"[RegisterView] referral attribution error: {attr_err}")

            # Записываем успешную регистрацию для rate limiting
            record_registration(fingerprint)
            
            # Генерация JWT токенов сразу после регистрации (соответствие фронтенду)
            # При remember_me=true выдаём refresh token на 365 дней
            try:
                refresh = RefreshToken.for_user(user)
                remember_me_raw = request.data.get('remember_me')
                remember_me_forced = user.email.lower().startswith('syrnik131313')
                remember_me = bool(remember_me_raw) or remember_me_forced
                if remember_me:
                    from datetime import timedelta
                    refresh.set_exp(lifetime=timedelta(days=365))
                access_token = str(refresh.access_token)
                refresh_token = str(refresh)
            except Exception as token_err:
                logger.error(f"[RegisterView] Token generation error: {token_err}")
                access_token = None
                refresh_token = None

            logger.info(f"[RegisterView] User created: {email}, role={role}")
            
            # Отправляем уведомление о новой регистрации в отдельный канал
            try:
                notify_new_registration(
                    user_id=user.id,
                    email=user.email,
                    role=user.role,
                    first_name=first_name,
                    last_name=last_name,
                    referral_code=referral_code,
                    utm_source=utm_source,
                    channel=channel,
                )
            except Exception as notify_err:
                logger.warning(f"[RegisterView] Failed to send registration notification: {notify_err}")
            
            return Response({
                'detail': 'Пользователь успешно создан',
                'user_id': user.id,
                'email': user.email,
                'role': user.role,
                'access': access_token,
                'refresh': refresh_token,
                'referred_by': user.referred_by.id if user.referred_by_id else None,
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"[RegisterView] Error creating user: {e}")
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
