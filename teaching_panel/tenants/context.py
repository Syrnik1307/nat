"""
Tenant context — хранение текущего tenant'а.
Используется middleware для установки и mixins для чтения.

Использует contextvars (async-safe) вместо threading.local.
Безопасно работает как в sync Django views, так и в async views,
Celery tasks и Django signals.
"""
import contextvars
import sys

_current_tenant: contextvars.ContextVar = contextvars.ContextVar(
    'current_tenant', default=None
)


def set_current_tenant(tenant):
    """Установить текущий tenant в context."""
    _current_tenant.set(tenant)


def get_current_tenant():
    """Получить текущий tenant из context. Возвращает None если не установлен."""
    return _current_tenant.get()


def clear_current_tenant():
    """Очистить текущий tenant из context."""
    _current_tenant.set(None)


# ═══════════════════════════════════════════════════════════════
# Backward-compatible aliases: school → tenant
# Нужны для старых тестов, которые используют *_school() функции.
# ═══════════════════════════════════════════════════════════════
set_current_school = set_current_tenant
get_current_school = get_current_tenant
clear_current_school = clear_current_tenant
