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

Solution: We now explicitly import task modules after Django setup, ensuring
all @shared_task decorators are executed and tasks are registered with Celery.
This is more reliable than relying on autodiscover_tasks() timing.
"""
import os
import logging

from celery import Celery
from celery.signals import worker_ready, beat_init, celeryd_init

logger = logging.getLogger(__name__)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "teaching_panel.settings")

app = Celery("teaching_panel")
app.config_from_object("django.conf:settings", namespace="CELERY")

# List of task modules to import explicitly
TASK_MODULES = [
    'accounts.tasks',
    'schedule.tasks', 
    'homework.tasks',
    'bot.tasks',
]


@celeryd_init.connect
def setup_django_and_tasks(sender, conf, **kwargs):
    """
    Called when Celery worker initializes.
    Ensures Django is set up and all task modules are imported.
    """
    import django
    django.setup()
    
    # Explicitly import task modules to register all tasks
    for module_name in TASK_MODULES:
        try:
            __import__(module_name)
            logger.info(f"Imported task module: {module_name}")
        except ImportError as e:
            logger.error(f"Failed to import task module {module_name}: {e}")


# Also configure imports in conf for beat scheduler
app.conf.imports = TASK_MODULES

# Try autodiscover as a fallback
app.autodiscover_tasks()


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
    import django
    django.setup()
    
    # Import task modules for beat scheduler
    for module_name in TASK_MODULES:
        try:
            __import__(module_name)
        except ImportError as e:
            logger.error(f"Beat: Failed to import {module_name}: {e}")
    
    logger.info("Celery beat scheduler initialized")


@app.task(bind=True, name='teaching_panel.debug_task')
def debug_task(self):
    """Simple debug task that logs request information."""
    print(f"Request: {self.request!r}")
    return "Debug task executed"
    return "Debug task executed"
