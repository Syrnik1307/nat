from django.apps import AppConfig
import threading
import logging
import sys
import os

logger = logging.getLogger(__name__)

class ScheduleConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'schedule'

    def ready(self):
        # Prevent running in management commands (e.g. migrate)
        if any(arg in sys.argv for arg in ['makemigrations', 'migrate', 'collectstatic']):
            return

        # Pre-initialize GDrive manager to avoid first-request timeout
        try:
            from .gdrive_utils import get_gdrive_manager
            
            def warmup_gdrive():
                try:
                    logger.info("ScheduleConfig: Warming up GDrive manager...")
                    get_gdrive_manager()
                    logger.info("ScheduleConfig: GDrive manager warmed up.")
                except Exception as e:
                    logger.error(f"ScheduleConfig: GDrive warmup failed: {e}")

            # Run in thread to not block Django startup
            t = threading.Thread(target=warmup_gdrive)
            t.daemon = True
            t.start()
            
        except ImportError:
            pass
