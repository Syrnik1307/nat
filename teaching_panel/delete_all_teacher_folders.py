#!/usr/bin/env python
"""Удаление ВСЕХ папок Teacher_* со всего Google Drive"""

import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
import django
django.setup()

from schedule.gdrive_utils import get_gdrive_manager

gdrive = get_gdrive_manager()

# Ищем ВСЕ папки Teacher_* везде (без ограничения по родителю)
query = "mimeType='application/vnd.google-apps.folder' and name contains 'Teacher_' and trashed=false"

all_folders = []
page_token = None

print("Ищу все папки Teacher_*...")

while True:
    results = gdrive.service.files().list(
        q=query,
        spaces='drive',
        fields='nextPageToken, files(id, name)',
        pageToken=page_token,
        pageSize=1000
    ).execute()
    
    folders = results.get('files', [])
    all_folders.extend(folders)
    print(f"  Найдено: {len(all_folders)}...")
    
    page_token = results.get('nextPageToken')
    if not page_token:
        break

print(f"\nВсего найдено папок Teacher_*: {len(all_folders)}")

if not all_folders:
    print("Нет папок для удаления")
    exit()

# Показываем примеры
print("\nПримеры:")
for f in all_folders[:5]:
    print(f"  - {f['name']}")
if len(all_folders) > 5:
    print(f"  ... и ещё {len(all_folders) - 5}")

print(f"\n🗑️ Удаляю {len(all_folders)} папок...")

deleted = 0
errors = 0

for f in all_folders:
    try:
        gdrive.service.files().delete(fileId=f['id']).execute()
        deleted += 1
        if deleted % 100 == 0:
            print(f"  Удалено: {deleted}/{len(all_folders)}")
    except Exception as e:
        errors += 1
        if errors <= 5:
            print(f"  ⚠️ Ошибка: {f['name']}: {e}")

print(f"\n✅ Удалено: {deleted}")
if errors:
    print(f"⚠️ Ошибок: {errors}")
print("Готово!")
