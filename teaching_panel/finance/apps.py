from django.apps import AppConfig


class FinanceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'finance'
    verbose_name = 'Финансы'

    def ready(self):
        from . import signals  # noqa: F401 — подключаем post_save сигналы
        from django.db.models.signals import m2m_changed
        from schedule.models import Group
        # Подключаем auto-create wallet при добавлении ученика в группу
        m2m_changed.connect(
            signals.create_wallet_on_group_join,
            sender=Group.students.through,
        )
