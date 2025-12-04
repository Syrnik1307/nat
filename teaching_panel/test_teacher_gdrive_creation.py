#!/usr/bin/env python
"""Тест автоматического создания папки Google Drive при регистрации учителя"""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
import django
django.setup()

from accounts.models import CustomUser
from django.conf import settings

print("=" * 60)
print("Тест создания папки Google Drive при регистрации")
print("=" * 60)
print()

# Создаём тестового учителя
test_email = f"test_teacher_{os.urandom(4).hex()}@test.com"
test_teacher = CustomUser.objects.create_user(
    email=test_email,
    password='testpass123',
    first_name='Тест',
    last_name='Учитель',
    role='teacher'
)

print(f"✅ Создан учитель: {test_teacher.email}")
print(f"   ID: {test_teacher.id}")
print(f"   Google Drive Folder ID: {test_teacher.gdrive_folder_id}")
print()

if test_teacher.gdrive_folder_id:
    print("✅ Папка Google Drive создана автоматически!")
    print(f"   Ссылка: https://drive.google.com/drive/folders/{test_teacher.gdrive_folder_id}")
else:
    print("❌ Папка Google Drive НЕ была создана")
    print("   Проверь логи для ошибок")

print()
print("Удаляю тестового учителя...")
test_teacher.delete()
print("✅ Тестовый учитель удалён")
