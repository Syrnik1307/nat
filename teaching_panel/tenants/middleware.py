"""
Tenant Middleware — определяет тенант из URL и кладёт в request.tenant.

Логика:
  1. anna.lectiospace.ru → Tenant(slug='anna')      — субдомен
  2. lectiospace.ru       → Default Tenant (платформа)
  3. localhost:3000       → X-Tenant-ID header (только DEV!) или Default Tenant

БЕЗОПАСНОСТЬ:
  - В production X-Tenant-ID header ИГНОРИРУЕТСЯ для remote-хостов.
    Только hostname (subdomain) определяет tenant — нельзя подделать.
  - X-Tenant-ID принимается ТОЛЬКО с localhost / 127.0.0.1 (разработка).

Также сохраняет tenant в thread-local для доступа из Celery tasks
и Django signals (где нет request).
"""

import logging
import time
from django.conf import settings as django_settings

from .context import set_current_tenant, clear_current_tenant

logger = logging.getLogger(__name__)

# Время жизни кеша (секунды). После истечения — обновляем из БД.
_CACHE_TTL = getattr(django_settings, 'TENANT_CACHE_TTL', 300)  # 5 минут


class TenantMiddleware:
    """
    Определяет Tenant по hostname запроса.

    Ставить в MIDDLEWARE ПОСЛЕ AuthenticationMiddleware,
    чтобы request.user уже был доступен.

    Ставит:
      - request.tenant       = Tenant instance (или None)
      - request.tenant_membership = TenantMembership (или None)
    """

    # Кэш тенантов: key → (tenant, timestamp)
    _tenant_cache = {}
    _default_tenant = None
    _default_tenant_ts = 0

    # Домены разработки — X-Tenant-ID header принимается ТОЛЬКО отсюда
    DEV_HOSTS = {'localhost', '127.0.0.1', '0.0.0.0'}

    # Пути, которые всегда обрабатываются без тенанта
    SKIP_PATHS = {'/admin/', '/api/health/', '/metrics/'}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant = self._resolve_tenant(request)
        request.tenant = tenant
        # Также ставим request.school для обратной совместимости
        request.school = tenant
        set_current_tenant(tenant)

        # Определяем membership пользователя
        request.tenant_membership = None
        if tenant and hasattr(request, 'user') and request.user.is_authenticated:
            try:
                from .models import TenantMembership
                request.tenant_membership = TenantMembership.objects.get(
                    tenant=tenant, user=request.user, is_active=True
                )
            except Exception:
                # Таблица может не существовать, модель не мигрирована и т.п.
                pass

        try:
            response = self.get_response(request)
        finally:
            clear_current_tenant()

        return response

    def _resolve_tenant(self, request):
        """Определяет тенант по hostname. X-Tenant-ID только для localhost."""
        path = request.path
        if any(path.startswith(p) for p in self.SKIP_PATHS):
            return self._get_default_tenant()

        host = request.get_host().split(':')[0].lower()

        # Localhost / разработка → проверяем X-Tenant-ID header (фронт шлёт slug)
        if host in self.DEV_HOSTS:
            header_slug = request.META.get('HTTP_X_TENANT_ID', '').strip()
            if header_slug:
                return self._get_tenant_by_slug(header_slug)
            return self._get_default_tenant()

        # ============================================================
        # PRODUCTION: X-Tenant-ID header ИГНОРИРУЕТСЯ для безопасности.
        # Tenant определяется ТОЛЬКО по hostname (subdomain).
        # ============================================================
        header_slug = request.META.get('HTTP_X_TENANT_ID', '')
        if header_slug:
            logger.warning(
                'X-Tenant-ID header "%s" ignored for non-local host "%s" '
                '(security: tenant is determined by hostname only)',
                header_slug, host,
            )

        # Проверяем кэш по hostname (с TTL)
        cached = self._tenant_cache.get(host)
        if cached is not None:
            tenant, ts = cached
            if (time.monotonic() - ts) < _CACHE_TTL:
                return tenant
            # TTL истёк — удаляем из кеша, ниже перезапросим
            del self._tenant_cache[host]

        tenant = self._lookup_tenant(host)
        self._tenant_cache[host] = (tenant, time.monotonic())
        return tenant

    def _get_tenant_by_slug(self, slug):
        """Ищет тенант по slug. Безопасен при отсутствии таблицы. С TTL-кешем."""
        cache_key = f'slug:{slug}'
        cached = self._tenant_cache.get(cache_key)
        if cached is not None:
            tenant, ts = cached
            if (time.monotonic() - ts) < _CACHE_TTL:
                return tenant
            del self._tenant_cache[cache_key]
        try:
            from .models import Tenant
            tenant = Tenant.objects.filter(slug=slug, status='active').first()
            self._tenant_cache[cache_key] = (tenant, time.monotonic())
            return tenant
        except Exception as e:
            logger.warning(f'Cannot lookup tenant by slug {slug}: {e}')
            return None

    def _lookup_tenant(self, host):
        """Ищет тенант по hostname в БД. Безопасен при отсутствии таблицы."""
        try:
            from .models import Tenant

            # Платформенные домены
            platform_domains = getattr(django_settings, 'PLATFORM_DOMAINS', [
                'lectiospace.ru',
                'www.lectiospace.ru',
                'stage.lectiospace.ru',
                'lectiospace.online',
            ])

            if host in platform_domains:
                return self._get_default_tenant()

            # Субдомен: anna.lectiospace.ru → slug='anna'
            for domain in platform_domains:
                if host.endswith(f'.{domain}'):
                    slug = host.replace(f'.{domain}', '')
                    try:
                        return Tenant.objects.get(slug=slug, status='active')
                    except Tenant.DoesNotExist:
                        logger.warning(f'Tenant not found for subdomain: {slug}')
                        return self._get_default_tenant()

            # Fallback — default
            logger.info(f'Unknown host {host}, using default tenant')
            return self._get_default_tenant()
        except Exception as e:
            # Таблица tenants_tenant может не существовать (миграции не прошли)
            logger.error(f'TenantMiddleware._lookup_tenant failed for {host}: {e}')
            return None

    def _get_default_tenant(self):
        """Default tenant (Lectio Space — платформа). С TTL-кешем."""
        now = time.monotonic()
        if self._default_tenant is not None and (now - self._default_tenant_ts) < _CACHE_TTL:
            return self._default_tenant
        from .models import Tenant
        try:
            tenant = Tenant.objects.filter(
                slug='lectiospace', status='active'
            ).first() or Tenant.objects.filter(status='active').first()
            TenantMiddleware._default_tenant = tenant
            TenantMiddleware._default_tenant_ts = now
            return tenant
        except Exception:
            return None

    @classmethod
    def clear_cache(cls):
        """Очистить кэш (при изменении Tenant через admin)."""
        cls._tenant_cache.clear()
        cls._default_tenant = None
