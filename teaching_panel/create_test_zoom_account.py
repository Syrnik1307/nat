#!/usr/bin/env python
"""Создаём тестовый Zoom аккаунт в пуле для быстрых уроков"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from zoom_pool.models import ZoomAccount

# Создаём тестовый аккаунт
account, created = ZoomAccount.objects.get_or_create(
    email='test@zoom.local',
    defaults={
        'api_key': 'test_api_key',
        'api_secret': 'test_api_secret',
        'zoom_user_id': 'test_zoom_user_id',
        'max_concurrent_meetings': 5,
        'current_meetings': 0,
        'is_active': True,
    }
)

if created:
    print(f"✓ Создан новый Zoom аккаунт: {account.email}")
else:
    print(f"✓ Аккаунт уже существует: {account.email}")
    # Сбрасываем занятость
    account.current_meetings = 0
    account.is_active = True
    account.save()
    print(f"✓ Сброшен счётчик встреч")

# Проверяем статус пула
total = ZoomAccount.objects.count()
active = ZoomAccount.objects.filter(is_active=True).count()
free = ZoomAccount.objects.filter(is_active=True, current_meetings=0).count()

print(f"\n=== ZOOM POOL STATUS ===")
print(f"Total: {total}")
print(f"Active: {active}")
print(f"Free: {free}")
print(f"\n✓ Готово! Теперь можно создавать быстрые уроки.")
