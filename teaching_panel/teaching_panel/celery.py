"""
Celery application instance for Teaching Panel.

This module configures Celery for the Django project.
Tasks are discovered from the following apps:
- accounts: Subscription management, notifications
- schedule: Zoom account release, lesson reminders
- homework: Grading notifications
- bot: Telegram scheduled messages, cleanup

ARCHITECTURE FIX (2026-02-01):
Previous issue: autodiscover_tasks() was not finding tasks because it was
called before Django apps were fully loaded.

Solution: 
1. Add CELERY_IMPORTS to settings.py (Django settings namespace)
2. Use on_after_finalize signal to import tasks after Django is ready
3. All tasks now have explicit name= parameter for reliable lookup
"""
import os
import logging

from celery import Celery
from celery.signals import worker_ready, beat_init

logger = logging.getLogger(__name__)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "teaching_panel.settings")

app = Celery("teaching_panel")
app.config_from_object("django.conf:settings", namespace="CELERY")

# List of task modules - imported via CELERY_IMPORTS in settings.py
TASK_MODULES = [
    'accounts.tasks',
    'schedule.tasks', 
    'homework.tasks',
    'bot.tasks',
]

# Try autodiscover as a fallback
app.autodiscover_tasks()


def _import_task_modules():
    """Import all task modules to ensure tasks are registered."""
    import django
    from django.apps import apps
    
    if not apps.ready:
        django.setup()
    
    for module_name in TASK_MODULES:
        try:
            __import__(module_name)
        except ImportError as e:
            logger.error(f"Failed to import task module {module_name}: {e}")


@app.on_after_finalize.connect
def setup_tasks(sender, **kwargs):
    """Called after Celery app is finalized. Import task modules."""
    _import_task_modules()
    task_count = len([t for t in app.tasks if not t.startswith('celery.')])
    logger.info(f"Celery finalized. {task_count} custom tasks registered.")


@worker_ready.connect
def log_worker_ready(sender, **kwargs):
    """Log all registered tasks when worker is ready."""
    task_names = [
        name for name in sorted(app.tasks) 
        if not name.startswith('celery.')
    ]
    logger.info(f"Celery worker ready. Registered {len(task_names)} custom tasks:")
    for name in task_names:
        logger.info(f"  - {name}")


@beat_init.connect
def log_beat_ready(sender, **kwargs):
    """
    Called when Celery beat scheduler initializes.
    Ensures Django is set up and tasks are available.
    """
    _import_task_modules()
    logger.info("Celery beat scheduler initialized with tasks")


@app.task(bind=True, name='teaching_panel.debug_task')
def debug_task(self):
    """Simple debug task that logs request information."""
    print(f"Request: {self.request!r}")
    return "Debug task executed"
    return "Debug task executed"
