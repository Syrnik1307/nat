#!/usr/bin/env python
"""Исправление записей: убрать ограничение по времени и проверить доступ GDrive"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from schedule.models import LessonRecording
from schedule.gdrive_utils import get_gdrive_manager

print("=== Исправление записей ===\n")

# 1. Убираем available_until у всех записей
updated = LessonRecording.objects.filter(available_until__isnull=False).update(available_until=None)
print(f"Убрано ограничение по времени у {updated} записей\n")

# 2. Проверяем и исправляем права доступа в Google Drive
gdrive = get_gdrive_manager()

for r in LessonRecording.objects.filter(status='ready', gdrive_file_id__isnull=False).exclude(gdrive_file_id=''):
    print(f"ID={r.id} file_id={r.gdrive_file_id}")
    
    try:
        # Делаем файл публичным для просмотра
        gdrive.service.permissions().create(
            fileId=r.gdrive_file_id,
            body={'type': 'anyone', 'role': 'reader'},
            fields='id'
        ).execute()
        print(f"  -> Права доступа установлены (anyone can view)")
    except Exception as e:
        if 'already exists' in str(e).lower() or 'duplicate' in str(e).lower():
            print(f"  -> Уже публичный")
        else:
            print(f"  -> Ошибка: {e}")

print("\n=== Готово ===")
