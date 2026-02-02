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
from celery.signals import worker_ready, beat_init, task_prerun, task_postrun, worker_shutdown, task_failure

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


# =============================================================================
# DATABASE CONNECTION MANAGEMENT FOR CELERY
# Critical for preventing "server closed the connection unexpectedly" errors
# =============================================================================

@task_prerun.connect
def close_stale_db_connections_before_task(sender=None, task_id=None, task=None, **kwargs):
    """
    Close stale database connections BEFORE each task runs.
    
    This prevents "server closed the connection unexpectedly" errors that occur
    when a long-lived Celery worker tries to use a database connection that
    PostgreSQL has already terminated (due to timeout or restart).
    
    Django's persistent connections (CONN_MAX_AGE) can become stale in Celery
    workers because workers live much longer than typical web requests.
    """
    from django import db
    
    # Close connections that are unusable
    for conn in db.connections.all():
        if conn.connection is not None:
            try:
                # Ping the connection to check if it's still valid
                conn.ensure_connection()
            except Exception:
                # Connection is dead, close it so Django creates a new one
                conn.close()


@task_postrun.connect
def close_db_connections_after_task(sender=None, task_id=None, task=None, retval=None, state=None, **kwargs):
    """
    Close all database connections AFTER each task completes.
    
    This ensures that:
    1. Connections don't pile up and exhaust the PostgreSQL connection pool
    2. No stale connections are left for the next task
    3. Memory associated with connections is freed
    
    This is the recommended pattern for Celery + Django:
    https://docs.celeryq.dev/en/stable/django/first-steps-with-django.html
    """
    from django import db
    db.connections.close_all()


@worker_shutdown.connect
def cleanup_on_worker_shutdown(sender=None, **kwargs):
    """
    Clean up all database connections when Celery worker is shutting down.
    
    This ensures graceful termination and prevents connection leaks.
    """
    from django import db
    db.connections.close_all()
    logger.info("Celery worker shutting down - all DB connections closed")


# =============================================================================
# MONITORING: Alert on task failures and time limit exceeded
# =============================================================================

@task_failure.connect
def alert_on_task_failure(sender=None, task_id=None, exception=None, args=None, kwargs=None, traceback=None, einfo=None, **kw):
    """
    Send Telegram alert when a Celery task fails or exceeds time limit.
    
    This catches:
    - SoftTimeLimitExceeded (task ran too long)
    - TimeLimitExceeded (task killed by hard limit)
    - Any other unhandled exceptions
    """
    from celery.exceptions import SoftTimeLimitExceeded, TimeLimitExceeded
    
    task_name = sender.name if sender else 'unknown'
    exc_type = type(exception).__name__ if exception else 'Unknown'
    exc_msg = str(exception)[:500] if exception else 'No message'
    
    # Determine severity
    if isinstance(exception, (SoftTimeLimitExceeded, TimeLimitExceeded)):
        severity = 'warning'
        emoji = '⏱️'
        title = 'TASK TIME LIMIT EXCEEDED'
    else:
        severity = 'error'
        emoji = '🚨'
        title = 'CELERY TASK FAILED'
    
    # Log locally
    logger.error(f"[CELERY_FAILURE] {task_name}: {exc_type} - {exc_msg}")
    
    # Send Telegram alert (non-blocking)
    try:
        from teaching_panel.telegram_logging import send_telegram_alert
        
        message = (
            f"{emoji} <b>{title}</b>\n\n"
            f"<b>Task:</b> <code>{task_name}</code>\n"
            f"<b>Exception:</b> {exc_type}\n"
            f"<b>Message:</b> {exc_msg}\n"
            f"<b>Task ID:</b> <code>{task_id}</code>"
        )
        
        # Fire and forget - don't block on alert sending
        send_telegram_alert.delay(message, severity=severity)
        
    except Exception as alert_err:
        logger.warning(f"[CELERY_FAILURE] Failed to send alert: {alert_err}")


