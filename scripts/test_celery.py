#!/usr/bin/env python
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')

import django
django.setup()

from teaching_panel.celery import app

# Test Redis connection
try:
    result = app.control.ping(timeout=3)
    print(f"Celery workers online: {result}")
except Exception as e:
    print(f"Error pinging workers: {e}")
    sys.exit(1)

# Test task sending
try:
    task = app.send_task('teaching_panel.debug_task')
    print(f"Debug task sent: {task.id}")
except Exception as e:
    print(f"Error sending task: {e}")
    sys.exit(1)

print("All Celery tests passed!")
