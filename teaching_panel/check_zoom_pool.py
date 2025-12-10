#!/usr/bin/env python
"""Проверка статуса Zoom pool"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from zoom_pool.models import ZoomAccount

total = ZoomAccount.objects.count()
active = ZoomAccount.objects.filter(is_active=True).count()
free = ZoomAccount.objects.filter(is_active=True, current_meetings=0).count()
busy = ZoomAccount.objects.filter(is_active=True, current_meetings__gt=0).count()

print(f"=== ZOOM POOL STATUS ===")
print(f"Total accounts: {total}")
print(f"Active accounts: {active}")
print(f"Free accounts: {free}")
print(f"Busy accounts: {busy}")

if total == 0:
    print("\n⚠️  WARNING: No Zoom accounts in pool!")
    print("Create at least one ZoomAccount to enable quick lessons.")
elif free == 0:
    print("\n⚠️  WARNING: All Zoom accounts are busy!")
    print("Wait for meetings to end or add more accounts.")
else:
    print(f"\n✓ {free} accounts ready for new meetings")
