"""
Tenant resource limit enforcement.
"""
from rest_framework.exceptions import PermissionDenied


class TenantLimitError(PermissionDenied):
    """Превышен лимит ресурсов tenant'а."""
    pass


def check_tenant_limit(tenant, resource_name, current_count=None):
    """
    Проверить, не превышен ли лимит ресурса для tenant'а.

    Args:
        tenant: Tenant instance
        resource_name: Имя лимита (соответствует полю в TenantResourceLimits,
                       например 'max_teachers', 'max_groups')
        current_count: Текущее кол-во (если None — подсчитаем из usage_stats)

    Raises:
        TenantLimitError если лимит превышен
    """
    if tenant is None:
        return  # Нет tenant — нет лимитов

    try:
        limits = tenant.resource_limits
    except Exception:
        return  # Нет записи лимитов — нет ограничений

    max_value = getattr(limits, resource_name, None)
    if max_value is None:
        return

    if current_count is None:
        # Попробуем взять из usage_stats
        try:
            stats = tenant.usage_stats
            # Преобразуем max_teachers → current_teachers
            usage_field = resource_name.replace('max_', 'current_')
            current_count = getattr(stats, usage_field, 0)
        except Exception:
            return

    if current_count >= max_value:
        resource_label = resource_name.replace('max_', '').replace('_', ' ')
        raise TenantLimitError(
            f'Достигнут лимит "{resource_label}": {current_count}/{max_value}. '
            f'Обратитесь к администратору для расширения.'
        )
