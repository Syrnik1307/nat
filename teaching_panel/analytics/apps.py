from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'analytics'
    
    def ready(self):
        """Подключаем сигналы при запуске приложения."""
        import analytics.signals  # noqa: F401 - Student activity signals
        import analytics.teacher_signals  # noqa: F401 - Teacher activity signals