"""
Middleware для сбора метрик запросов и производительности
"""
import time
import logging
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('request_metrics')


class RequestMetricsMiddleware(MiddlewareMixin):
    """
    Middleware для логирования метрик каждого запроса:
    - Время обработки
    - Статус код
    - Путь и метод
    - User ID (если аутентифицирован)
    """
    
    def process_request(self, request):
        request._start_time = time.time()
        return None
    
    def process_response(self, request, response):
        if hasattr(request, '_start_time'):
            duration = time.time() - request._start_time
            
            user_id = 'anonymous'
            if hasattr(request, 'user') and request.user.is_authenticated:
                user_id = request.user.id
            
            # Логируем в структурированном формате
            logger.info(
                f"method={request.method} "
                f"path={request.path} "
                f"status={response.status_code} "
                f"duration={duration:.3f}s "
                f"user={user_id} "
                f"ip={self.get_client_ip(request)}"
            )
            
            # Добавляем заголовок с временем обработки
            response['X-Request-Duration'] = f"{duration:.3f}"
            
            # Предупреждение о медленных запросах (>2 секунды)
            if duration > 2.0:
                logger.warning(
                    f"SLOW_REQUEST: {request.method} {request.path} "
                    f"took {duration:.3f}s (user={user_id})"
                )
        
        return response
    
    @staticmethod
    def get_client_ip(request):
        """Получить реальный IP клиента (с учетом прокси)"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        return ip
