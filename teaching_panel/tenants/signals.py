"""
Tenant signals — автоматическая инвалидация кеша middleware при изменении Tenant.

Подключается через TenantsConfig.ready() в apps.py.
"""
import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='tenants.Tenant')
def tenant_post_save(sender, instance, **kwargs):
    """При сохранении Tenant — сбросить весь кеш middleware."""
    from .middleware import TenantMiddleware
    TenantMiddleware.clear_cache()
    logger.info('Tenant cache cleared after save: %s (slug=%s)', instance.name, instance.slug)


@receiver(post_delete, sender='tenants.Tenant')
def tenant_post_delete(sender, instance, **kwargs):
    """При удалении Tenant — сбросить кеш."""
    from .middleware import TenantMiddleware
    TenantMiddleware.clear_cache()
    logger.info('Tenant cache cleared after delete: %s (slug=%s)', instance.name, instance.slug)
