#!/usr/bin/env python
"""Проверка подписки"""
import os
import sys
import django

sys.path.insert(0, '/var/www/teaching_panel/teaching_panel')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from accounts.models import CustomUser, Subscription
from django.utils import timezone

teacher = CustomUser.objects.get(email='syrnik131313@gmail.com')
print(f"Teacher: {teacher.email}")

subs = Subscription.objects.filter(user=teacher)
print(f"\nSubscriptions found: {subs.count()}")

for sub in subs:
    print(f"\n=== Subscription ID {sub.id} ===")
    print(f"Status: {sub.status}")
    print(f"Expires at: {sub.expires_at}")
    print(f"Created at: {sub.created_at}")
    print(f"Plan: {sub.plan}")
    print(f"Is active: {sub.is_active()}")
    print(f"Current time: {timezone.now()}")
    
    if sub.expires_at:
        print(f"Time until expiry: {sub.expires_at - timezone.now()}")
