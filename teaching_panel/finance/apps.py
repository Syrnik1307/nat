from django.apps import AppConfig


class FinanceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'finance'
    verbose_name = 'Финансы учеников'
    
    def ready(self):
        """Подключаем signals при старте приложения."""
        from django.db.models.signals import m2m_changed
        import finance.signals  # noqa: F401
        
        # Подключаем m2m_changed для Group.students динамически
        # (нельзя использовать строку в @receiver для through-модели)
        from schedule.models import Group
        m2m_changed.connect(
            finance.signals.create_wallet_on_group_join,
            sender=Group.students.through
        )
