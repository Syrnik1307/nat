"""
Конфигурация Celery для фоновых задач
"""
import os
from celery import Celery

# Устанавливаем переменную окружения Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')

app = Celery('teaching_panel')

# Загружаем конфигурацию из settings.py с префиксом CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматически находим задачи в приложениях
app.autodiscover_tasks()

# Настройка периодических задач (beat schedule)
app.conf.beat_schedule = {
    'release-stuck-zoom-accounts-every-10-minutes': {
        'task': 'schedule.tasks.release_stuck_zoom_accounts',
        'schedule': 600.0,  # 10 минут
    },
    'release-finished-zoom-accounts-every-5-minutes': {
        'task': 'schedule.tasks.release_finished_zoom_accounts',
        'schedule': 300.0,  # 5 минут
    },
    'schedule-upcoming-lesson-reminders-every-2-minutes': {
        'task': 'schedule.tasks.schedule_upcoming_lesson_reminders',
        'schedule': 120.0,  # 2 минуты
    },
}
app.conf.timezone = 'UTC'


@app.task(bind=True)
def debug_task(self):
    """Тестовая задача для проверки Celery"""
    print(f'Request: {self.request!r}')
