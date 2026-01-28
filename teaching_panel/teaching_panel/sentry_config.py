"""
Sentry Integration для Django.
Отправляет ошибки в Sentry для профессионального error tracking.

Настройка:
1. Создать проект на https://sentry.io (есть бесплатный план)
2. Получить DSN (Data Source Name)
3. Установить: pip install sentry-sdk
4. Добавить в .env: SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
5. Импортировать в settings.py: from .sentry_config import init_sentry; init_sentry()

Возможности:
- Автоматический сбор всех exceptions
- Группировка похожих ошибок
- Stack traces с контекстом
- Performance monitoring (опционально)
- Release tracking
- User context
"""
import os
import logging

logger = logging.getLogger(__name__)


def init_sentry():
    """
    Инициализирует Sentry SDK.
    Вызывать в конце settings.py.
    """
    sentry_dsn = os.environ.get('SENTRY_DSN', '')
    
    if not sentry_dsn:
        logger.info("Sentry: DSN not configured, skipping initialization")
        return False
    
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.redis import RedisIntegration
    except ImportError:
        logger.warning("Sentry: sentry-sdk not installed. Run: pip install sentry-sdk")
        return False
    
    # Определяем environment
    environment = os.environ.get('DJANGO_ENV', 'production')
    if os.environ.get('DEBUG', 'False').lower() in ('true', '1', 'yes'):
        environment = 'development'
    
    # Версия приложения (можно брать из git)
    release = os.environ.get('APP_VERSION', 'unknown')
    
    # Настройки логирования
    logging_integration = LoggingIntegration(
        level=logging.INFO,        # Capture info and above as breadcrumbs
        event_level=logging.ERROR  # Send errors to Sentry
    )
    
    # Инициализация
    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[
            DjangoIntegration(
                transaction_style='url',
                middleware_spans=True,
            ),
            logging_integration,
            RedisIntegration(),
        ],
        environment=environment,
        release=release,
        
        # Performance monitoring (опционально, можно отключить для экономии)
        traces_sample_rate=float(os.environ.get('SENTRY_TRACES_SAMPLE_RATE', '0.1')),
        
        # Profiling (требует sentry_sdk[profiling])
        profiles_sample_rate=float(os.environ.get('SENTRY_PROFILES_SAMPLE_RATE', '0.0')),
        
        # Фильтрация PII (персональных данных)
        send_default_pii=False,
        
        # Игнорировать некоторые ошибки
        ignore_errors=[
            'django.security.DisallowedHost',
            'django.http.request.RawPostDataException',
        ],
        
        # Callback для обогащения событий
        before_send=before_send_callback,
    )
    
    logger.info(f"Sentry: initialized for {environment} environment")
    return True


def before_send_callback(event, hint):
    """
    Callback для модификации/фильтрации событий перед отправкой в Sentry.
    """
    # Фильтруем некоторые ошибки
    if 'exc_info' in hint:
        exc_type, exc_value, _ = hint['exc_info']
        
        # Игнорируем 404 ошибки
        if exc_type.__name__ == 'Http404':
            return None
        
        # Игнорируем отмену запроса клиентом
        if 'ConnectionResetError' in str(exc_type):
            return None
    
    # Убираем чувствительные данные из request
    if 'request' in event:
        request_data = event['request']
        
        # Маскируем пароли
        if 'data' in request_data:
            data = request_data['data']
            if isinstance(data, dict):
                for key in ['password', 'token', 'secret', 'api_key']:
                    if key in data:
                        data[key] = '[FILTERED]'
        
        # Маскируем Authorization header
        if 'headers' in request_data:
            headers = request_data['headers']
            if isinstance(headers, dict):
                if 'Authorization' in headers:
                    headers['Authorization'] = '[FILTERED]'
    
    return event


def capture_message(message, level='info', extra=None):
    """
    Отправляет произвольное сообщение в Sentry.
    
    Использование:
        from teaching_panel.sentry_config import capture_message
        capture_message("Payment failed", level='error', extra={'user_id': 123})
    """
    try:
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            if extra:
                for key, value in extra.items():
                    scope.set_extra(key, value)
            sentry_sdk.capture_message(message, level=level)
    except Exception:
        pass


def capture_exception(exception, extra=None):
    """
    Отправляет exception в Sentry вручную.
    
    Использование:
        from teaching_panel.sentry_config import capture_exception
        try:
            risky_operation()
        except Exception as e:
            capture_exception(e, extra={'context': 'payment processing'})
    """
    try:
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            if extra:
                for key, value in extra.items():
                    scope.set_extra(key, value)
            sentry_sdk.capture_exception(exception)
    except Exception:
        pass


def set_user_context(user):
    """
    Устанавливает контекст пользователя для всех последующих событий.
    Вызывается в middleware или signal.
    
    Использование:
        from teaching_panel.sentry_config import set_user_context
        set_user_context(request.user)
    """
    try:
        import sentry_sdk
        if user and user.is_authenticated:
            sentry_sdk.set_user({
                'id': user.id,
                'email': user.email,
                'username': getattr(user, 'username', user.email),
                'role': getattr(user, 'role', 'unknown'),
            })
        else:
            sentry_sdk.set_user(None)
    except Exception:
        pass
