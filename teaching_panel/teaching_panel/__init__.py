"""
Инициализация Django приложения с Celery
"""
# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
from .celery import app as celery_app

# Expose as both 'celery_app' and 'celery' for compatibility
celery = celery_app

__all__ = ('celery_app', 'celery')
