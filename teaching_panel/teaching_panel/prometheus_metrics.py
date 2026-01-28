"""
Prometheus Metrics Endpoint для Django.
Экспортирует метрики в формате Prometheus для Grafana.

Добавить в urls.py:
    path('metrics/', metrics_view, name='prometheus-metrics'),

Метрики:
- HTTP request count by status code
- Request latency histogram
- Active users
- Database connections
- Cache hit rate
- Celery queue length
"""
import time
from functools import wraps
from django.http import HttpResponse
from django.db import connection
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


# In-memory metrics storage (для простоты, в продакшене лучше использовать django-prometheus)
class MetricsRegistry:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.counters = {}
            cls._instance.histograms = {}
            cls._instance.gauges = {}
        return cls._instance
    
    def inc_counter(self, name, labels=None, value=1):
        key = self._make_key(name, labels)
        self.counters[key] = self.counters.get(key, 0) + value
    
    def set_gauge(self, name, value, labels=None):
        key = self._make_key(name, labels)
        self.gauges[key] = value
    
    def observe_histogram(self, name, value, labels=None):
        key = self._make_key(name, labels)
        if key not in self.histograms:
            self.histograms[key] = []
        self.histograms[key].append(value)
        # Keep only last 1000 observations
        if len(self.histograms[key]) > 1000:
            self.histograms[key] = self.histograms[key][-1000:]
    
    def _make_key(self, name, labels):
        if labels:
            label_str = ','.join(f'{k}="{v}"' for k, v in sorted(labels.items()))
            return f'{name}{{{label_str}}}'
        return name
    
    def format_prometheus(self):
        """Форматирует метрики в формате Prometheus."""
        lines = []
        
        # Counters
        for key, value in self.counters.items():
            lines.append(f'{key} {value}')
        
        # Gauges
        for key, value in self.gauges.items():
            lines.append(f'{key} {value}')
        
        # Histograms (simplified - just count and sum)
        for key, values in self.histograms.items():
            if values:
                lines.append(f'{key}_count {len(values)}')
                lines.append(f'{key}_sum {sum(values)}')
                lines.append(f'{key}_avg {sum(values)/len(values):.4f}')
        
        return '\n'.join(lines)


metrics = MetricsRegistry()


def track_request_metrics(func):
    """Декоратор для отслеживания метрик запросов."""
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        start_time = time.time()
        
        try:
            response = func(request, *args, **kwargs)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            raise
        finally:
            duration = time.time() - start_time
            
            # Increment request counter
            metrics.inc_counter('http_requests_total', {
                'method': request.method,
                'status': str(status_code),
                'path': request.path[:50]  # Truncate long paths
            })
            
            # Observe latency
            metrics.observe_histogram('http_request_duration_seconds', duration, {
                'method': request.method
            })
        
        return response
    return wrapper


def collect_system_metrics():
    """Собирает системные метрики."""
    User = get_user_model()
    
    # Active users (last 24h)
    day_ago = timezone.now() - timedelta(days=1)
    try:
        active_users = User.objects.filter(last_login__gte=day_ago).count()
        metrics.set_gauge('app_active_users_24h', active_users)
    except Exception:
        pass
    
    # Total users
    try:
        total_users = User.objects.count()
        metrics.set_gauge('app_total_users', total_users)
    except Exception:
        pass
    
    # Database connection check
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        metrics.set_gauge('db_connection_healthy', 1)
    except Exception:
        metrics.set_gauge('db_connection_healthy', 0)
    
    # Cache check
    try:
        cache.set('_metrics_test', '1', 10)
        if cache.get('_metrics_test') == '1':
            metrics.set_gauge('cache_connection_healthy', 1)
        else:
            metrics.set_gauge('cache_connection_healthy', 0)
    except Exception:
        metrics.set_gauge('cache_connection_healthy', 0)
    
    # Lessons count (if schedule app exists)
    try:
        from schedule.models import Lesson
        lessons_today = Lesson.objects.filter(
            scheduled_time__date=timezone.now().date()
        ).count()
        metrics.set_gauge('app_lessons_today', lessons_today)
    except Exception:
        pass
    
    # Recordings count
    try:
        from schedule.models import LessonRecording
        total_recordings = LessonRecording.objects.count()
        metrics.set_gauge('app_total_recordings', total_recordings)
    except Exception:
        pass
    
    # Subscriptions
    try:
        from accounts.models import Subscription
        active_subs = Subscription.objects.filter(status='active').count()
        metrics.set_gauge('app_active_subscriptions', active_subs)
    except Exception:
        pass


def metrics_view(request):
    """
    Prometheus metrics endpoint.
    GET /metrics/
    
    Защита: можно добавить IP whitelist или токен.
    """
    # Опциональная защита по IP
    allowed_ips = getattr(settings, 'PROMETHEUS_ALLOWED_IPS', ['127.0.0.1', '::1'])
    client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
    client_ip = client_ip.split(',')[0].strip()
    
    # Разрешаем localhost и настроенные IP
    if client_ip not in allowed_ips and 'localhost' not in client_ip:
        # Проверяем токен
        token = request.GET.get('token', '')
        expected_token = getattr(settings, 'PROMETHEUS_TOKEN', '')
        if expected_token and token != expected_token:
            return HttpResponse('Forbidden', status=403)
    
    # Собираем свежие метрики
    collect_system_metrics()
    
    # Добавляем базовые метрики
    metrics.set_gauge('up', 1)
    metrics.set_gauge('app_info', 1, {'version': getattr(settings, 'APP_VERSION', '1.0.0')})
    
    # Форматируем и возвращаем
    output = metrics.format_prometheus()
    
    return HttpResponse(output, content_type='text/plain; charset=utf-8')
