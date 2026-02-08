"""
Tenant Middleware — определяет школу из URL и кладёт в request.school.

Логика:
  1. anna.lectiospace.ru → School(slug='anna')
  2. english-anna.com    → School(custom_domain='english-anna.com')
  3. lectiospace.ru       → Default School (платформа)
  4. localhost:3000       → Default School (разработка)

Также сохраняет school в thread-local для доступа из Celery tasks
и Django signals (где нет request).
"""

import threading
import logging
from django.conf import settings as django_settings
from django.http import Http404

logger = logging.getLogger(__name__)

# Thread-local storage для текущей школы
_thread_local = threading.local()


def get_current_school():
    """Получить текущую школу из thread-local (для signals, tasks)."""
    return getattr(_thread_local, 'school', None)


def set_current_school(school):
    """Установить текущую школу (вызывается middleware или task)."""
    _thread_local.school = school


def clear_current_school():
    """Очистить (после request или task)."""
    _thread_local.school = None


class TenantMiddleware:
    """
    Определяет School по hostname запроса.
    
    Ставить в MIDDLEWARE ПОСЛЕ AuthenticationMiddleware,
    чтобы request.user уже был доступен.
    
    Важно: НЕ блокирует запросы если школа не найдена —
    просто ставит request.school = None (для API docs, admin, health checks).
    """
    
    # Кэш школ чтобы не ходить в БД каждый запрос
    _school_cache = {}
    _default_school = None
    
    # Домены разработки — всегда default school
    DEV_HOSTS = {'localhost', '127.0.0.1', '0.0.0.0'}
    
    # Пути, которые всегда обрабатываются без школы (admin, health)
    SKIP_PATHS = {'/admin/', '/api/health/', '/metrics/'}
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        school = self._resolve_school(request)
        request.school = school
        set_current_school(school)
        
        try:
            response = self.get_response(request)
        finally:
            clear_current_school()
        
        return response
    
    def _resolve_school(self, request):
        """Определяет школу по hostname."""
        # Пропускаем admin/health
        path = request.path
        if any(path.startswith(p) for p in self.SKIP_PATHS):
            return self._get_default_school()
        
        host = request.get_host().split(':')[0].lower()  # убираем порт
        
        # Localhost / разработка → default school
        if host in self.DEV_HOSTS:
            return self._get_default_school()
        
        # Проверяем кэш
        if host in self._school_cache:
            return self._school_cache[host]
        
        school = self._lookup_school(host)
        self._school_cache[host] = school
        return school
    
    def _lookup_school(self, host):
        """Ищет школу по hostname в БД."""
        from tenants.models import School
        
        # Платформенный домен (lectiospace.ru без поддомена)
        platform_domains = getattr(django_settings, 'PLATFORM_DOMAINS', [
            'lectiospace.ru',
            'www.lectiospace.ru',
            'stage.lectiospace.ru',
            'lectiospace.online',
        ])
        
        if host in platform_domains:
            return self._get_default_school()
        
        # Поддомен: anna.lectiospace.ru → slug='anna'
        for domain in platform_domains:
            if host.endswith(f'.{domain}'):
                slug = host.replace(f'.{domain}', '')
                try:
                    return School.objects.get(slug=slug, is_active=True)
                except School.DoesNotExist:
                    logger.warning(f'School not found for subdomain: {slug}')
                    return self._get_default_school()
        
        # Кастомный домен: english-anna.com
        try:
            return School.objects.get(custom_domain=host, is_active=True)
        except School.DoesNotExist:
            logger.warning(f'School not found for custom domain: {host}')
            return self._get_default_school()
    
    def _get_default_school(self):
        """Default school (Lectio Space — платформа)."""
        if self._default_school is None:
            from tenants.models import School
            try:
                TenantMiddleware._default_school = School.objects.get(is_default=True)
            except School.DoesNotExist:
                # Первый запуск — школа ещё не создана (до миграции)
                return None
        return self._default_school
    
    @classmethod
    def clear_cache(cls):
        """Очистить кэш (при изменении School через admin)."""
        cls._school_cache.clear()
        cls._default_school = None
