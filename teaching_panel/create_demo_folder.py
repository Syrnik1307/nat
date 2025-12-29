#!/usr/bin/env python
"""Создать тестовую папку учителя БЕЗ удаления для проверки"""

import os
import uuid
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
import django
django.setup()

from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from accounts.models import CustomUser, Subscription
from accounts.gdrive_folder_service import create_teacher_folder_on_subscription

print("=" * 60)
print("  СОЗДАНИЕ ТЕСТОВОЙ ПАПКИ (БЕЗ УДАЛЕНИЯ)")
print("=" * 60)
print()

# Корневая папка
print(f"📁 Корневая папка TeachingPanel:")
print(f"   https://drive.google.com/drive/folders/{settings.GDRIVE_ROOT_FOLDER_ID}")
print()

# Создаём учителя
unique_id = uuid.uuid4().hex[:6]
teacher = CustomUser.objects.create_user(
    email=f'demo_teacher_{unique_id}@demo.local',
    password='demo123',
    first_name='Демо',
    last_name='Учитель',
    role='teacher',
)
print(f"👤 Создан учитель: {teacher.email} (ID: {teacher.id})")

# Создаём подписку
subscription = Subscription.objects.create(
    user=teacher,
    plan=Subscription.PLAN_MONTHLY,
    status=Subscription.STATUS_ACTIVE,
    expires_at=timezone.now() + timedelta(days=30),
    base_storage_gb=10,
    total_paid=Decimal('990.00'),
)
print(f"💳 Подписка активирована")

# Создаём папку
folder_id = create_teacher_folder_on_subscription(subscription)

print()
print("=" * 60)
print("  ✅ ГОТОВО! Папка создана и НЕ удалена!")
print("=" * 60)
print()
print(f"📁 Папка учителя: Teacher_{teacher.id}_Демо_Учитель")
print(f"🔗 Ссылка: https://drive.google.com/drive/folders/{folder_id}")
print()
print("Открой эту ссылку в браузере или посмотри в папке TeachingPanel!")
print()
print(f"⚠️  Чтобы удалить тестового учителя потом, выполни:")
print(f"   python manage.py shell -c \"from accounts.models import CustomUser; CustomUser.objects.filter(email__startswith='demo_teacher_').delete()\"")
