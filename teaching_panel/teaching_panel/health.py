"""
Health Check Endpoint for Monitoring
=====================================
Используется системой мониторинга для проверки состояния приложения.
"""
from django.http import JsonResponse
from django.db import connection
from django.conf import settings
import time
import os


def health_check(request):
    """
    Health check endpoint для мониторинга.
    
    Возвращает:
    - 200 если всё работает
    - 500 если есть критические проблемы
    
    Проверяет:
    - Соединение с базой данных
    - Наличие критических файлов
    - Доступность settings
    """
    status = {
        'status': 'healthy',
        'timestamp': time.time(),
        'version': getattr(settings, 'VERSION', '1.0.0'),
        'checks': {}
    }
    
    # 1. Проверка базы данных
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
        status['checks']['database'] = 'ok'
    except Exception as e:
        status['status'] = 'unhealthy'
        status['checks']['database'] = f'error: {str(e)[:100]}'
    
    # 2. Проверка критических настроек
    try:
        required_settings = ['SECRET_KEY', 'DEBUG', 'ALLOWED_HOSTS']
        for setting in required_settings:
            if not hasattr(settings, setting):
                raise ValueError(f'Missing {setting}')
        status['checks']['settings'] = 'ok'
    except Exception as e:
        status['status'] = 'unhealthy'
        status['checks']['settings'] = str(e)
    
    # 3. Проверка записываемости лог-директории
    try:
        log_dir = os.path.join(settings.BASE_DIR, 'logs')
        if os.path.exists(log_dir) and os.access(log_dir, os.W_OK):
            status['checks']['logs'] = 'ok'
        elif not os.path.exists(log_dir):
            status['checks']['logs'] = 'directory missing (non-critical)'
        else:
            status['checks']['logs'] = 'not writable'
    except Exception as e:
        status['checks']['logs'] = f'check failed: {str(e)[:50]}'
    
    # Определяем HTTP статус
    http_status = 200 if status['status'] == 'healthy' else 500
    
    return JsonResponse(status, status=http_status)


def ready_check(request):
    """
    Readiness probe - проверяет готовность приложения обслуживать запросы.
    Используется для Kubernetes/orchestration систем.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        return JsonResponse({'ready': True})
    except Exception:
        return JsonResponse({'ready': False}, status=503)


def live_check(request):
    """
    Liveness probe - проверяет что приложение живо.
    Минимальная проверка для определения необходимости перезапуска.
    """
    return JsonResponse({'alive': True, 'timestamp': time.time()})
