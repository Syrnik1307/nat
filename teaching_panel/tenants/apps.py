from django.apps import AppConfig


class TenantsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tenants'
    verbose_name = 'Школы (Multi-Tenant)'

    def ready(self):
        # Подключаем signals для автоинвалидации кеша middleware
        import tenants.signals  # noqa: F401
        # Подключаем Django system checks для tenant isolation
        import tenants.checks  # noqa: F401
