"""
Django System Checks для tenant isolation.

Эти проверки запускаются при:
  - python manage.py check
  - python manage.py runserver (каждый рестарт)
  - Деплое

Выдают WARNINGS если ViewSets не используют TenantViewSetMixin.
"""
from django.core.checks import Warning, register, Tags


@register(Tags.security)
def check_viewsets_have_tenant_mixin(app_configs, **kwargs):
    """
    Проверяет что все ModelViewSets в проекте используют TenantViewSetMixin.
    Исключения: ViewSets которые намеренно не привязаны к tenant (Tenant CRUD, auth).
    """
    errors = []

    try:
        from tenants.mixins import TenantViewSetMixin
        from rest_framework.viewsets import ModelViewSet, ViewSet

        # Поддержка обоих путей импорта TenantViewSetMixin
        _mixin_classes = [TenantViewSetMixin]
        try:
            from core.tenant_mixins import TenantViewSetMixin as CoreMixin
            _mixin_classes.append(CoreMixin)
        except ImportError:
            pass

        def _has_tenant_mixin(cls):
            return any(issubclass(cls, m) for m in _mixin_classes)

        # Список ViewSets, которым НЕ нужен TenantViewSetMixin
        EXEMPT_VIEWSETS = {
            'TenantViewSet',           # Управление самими тенантами
            'UserViewSet',             # Управление пользователями
            'TenantMembershipViewSet', # Управление членством
        }

        import importlib
        view_modules = [
            'core.views',
            'core.content_protection_views',
            'schedule.views',
            'homework.views',
            'finance.views',
            'support.views',
            'analytics.views',
            'zoom_pool.views',
        ]

        for module_path in view_modules:
            try:
                module = importlib.import_module(module_path)
            except ImportError:
                continue

            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, ModelViewSet)
                    and attr is not ModelViewSet
                    and attr.__name__ not in EXEMPT_VIEWSETS
                    and not _has_tenant_mixin(attr)
                    and attr.__module__ == module.__name__
                ):
                    errors.append(
                        Warning(
                            f'{attr.__name__} ({module_path}) does not use TenantViewSetMixin.',
                            hint=(
                                f'Add TenantViewSetMixin to {attr.__name__} to ensure '
                                f'automatic tenant isolation. If this ViewSet intentionally '
                                f'operates across tenants, add it to EXEMPT_VIEWSETS in '
                                f'tenants/checks.py.'
                            ),
                            id='tenants.W001',
                        )
                    )
    except ImportError:
        pass  # DRF or tenants not installed

    return errors


@register(Tags.security)
def check_tenant_model_nullable(app_configs, **kwargs):
    """
    Предупреждает о моделях где tenant FK nullable — потенциальная утечка данных.
    """
    errors = []
    try:
        from django.apps import apps

        EXEMPT_MODELS = {
            'Tenant', 'TenantMembership', 'TenantResourceLimits',
            'TenantUsageStats', 'TenantInvite', 'TenantVideoSettings',
        }

        for model in apps.get_models():
            if model.__name__ in EXEMPT_MODELS:
                continue
            if hasattr(model, 'tenant') and hasattr(model.tenant, 'field'):
                field = model.tenant.field
                if field.null:
                    errors.append(
                        Warning(
                            f'{model.__name__}.tenant is nullable (null=True).',
                            hint=(
                                f'Records without tenant can leak across organizations. '
                                f'After migrating existing data, set null=False.'
                            ),
                            id='tenants.W002',
                        )
                    )
    except Exception:
        pass

    return errors
