"""Celery application instance for Teaching Panel."""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "teaching_panel.settings")

app = Celery("teaching_panel")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    """Simple debug task that logs request information."""
    print(f"Request: {self.request!r}")
