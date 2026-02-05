from django.apps import AppConfig


class ConciergeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'concierge'
    verbose_name = 'Lectio Concierge (AI Support)'
    
    def ready(self):
        # Импортируем сигналы при старте приложения
        pass  # TODO: import concierge.signals
