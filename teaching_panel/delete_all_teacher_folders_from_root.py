#!/usr/bin/env python
"""Удаление ВСЕХ папок Teacher_* из КОРНЯ Google Drive (не из подпапки)"""

import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
import django
django.setup()

from schedule.gdrive_utils import get_gdrive_manager

gdrive = get_gdrive_manager()

# Ищем в КОРНЕ (root), без указания parent
query = "mimeType='application/vnd.google-apps.folder' and name contains 'Teacher_' and trashed=false and 'root' in parents"

print("🔍 Ищу папки Teacher_* в КОРНЕ Google Drive...")

all_folders = []
page_token = None

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

print(f"\n📊 ИТОГО найдено папок: {len(all_folders)}")

if not all_folders:
    print("✅ Нет папок для удаления")
    exit(0)

print("\n🗑️ Удаляю ВСЕ папки...")

deleted = 0
errors = 0

for folder in all_folders:
    try:
        gdrive.service.files().delete(fileId=folder['id']).execute()
        deleted += 1
        if deleted % 100 == 0:
            print(f"  Удалено: {deleted}/{len(all_folders)}")
    except Exception as e:
        errors += 1
        if errors <= 5:
            print(f"  ⚠️ Ошибка: {folder['name']}: {e}")

print(f"\n✅ Удалено: {deleted}")
if errors:
    print(f"⚠️ Ошибок: {errors}")
