#!/usr/bin/env python
"""Check periodic tasks in django-celery-beat."""
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')

import django
django.setup()

from django_celery_beat.models import PeriodicTask

print("=" * 60)
print("PERIODIC TASKS FROM DJANGO-CELERY-BEAT DATABASE")
print("=" * 60)

for t in PeriodicTask.objects.all():
    status = "ENABLED" if t.enabled else "DISABLED"
    print(f"[{status}] {t.name}")
    print(f"    Task: {t.task}")
    if t.interval:
        print(f"    Interval: every {t.interval}")
    if t.crontab:
        print(f"    Crontab: {t.crontab}")
    print()

print("=" * 60)
print(f"Total: {PeriodicTask.objects.count()} tasks")
