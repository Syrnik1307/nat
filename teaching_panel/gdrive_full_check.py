#!/usr/bin/env python
"""Полная проверка Google Drive и очистка"""

import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
import django
django.setup()

from django.conf import settings
from schedule.gdrive_utils import get_gdrive_manager

gdrive = get_gdrive_manager()

print('=' * 60)
print('  ПОЛНАЯ ПРОВЕРКА GOOGLE DRIVE')
print('=' * 60)
print()

# 1. Проверяем корневую папку
root_id = settings.GDRIVE_ROOT_FOLDER_ID
print(f'GDRIVE_ROOT_FOLDER_ID: {root_id}')

try:
    info = gdrive.service.files().get(fileId=root_id, fields='id,name,trashed').execute()
    print(f'Папка: {info["name"]} (trashed={info["trashed"]})')
    print(f'Ссылка: https://drive.google.com/drive/folders/{root_id}')
except Exception as e:
    print(f'ОШИБКА доступа к папке: {e}')
    exit(1)

# 2. Содержимое корневой папки TeachingPanel
print()
print('=== Содержимое TeachingPanel ===')
query = f"'{root_id}' in parents and trashed=false"
results = gdrive.service.files().list(q=query, fields='files(id,name,mimeType)', pageSize=100).execute()
for f in results.get('files', []):
    icon = '📁' if 'folder' in f['mimeType'] else '📄'
    print(f'  {icon} {f["name"]}')
if not results.get('files'):
    print('  (пусто)')

# 3. Ищем ВСЕ папки Teacher_* везде на диске
print()
print('=== ВСЕ папки Teacher_* на ВСЁМ диске ===')
query = "mimeType='application/vnd.google-apps.folder' and name contains 'Teacher_' and trashed=false"
all_folders = []
page_token = None
while True:
    results = gdrive.service.files().list(
        q=query, 
        fields='nextPageToken,files(id,name,parents)', 
        pageSize=500,
        pageToken=page_token
    ).execute()
    all_folders.extend(results.get('files', []))
    page_token = results.get('nextPageToken')
    if not page_token:
        break

print(f'Найдено ВСЕГО: {len(all_folders)}')

in_teaching_panel = []
outside = []

for f in all_folders:
    parents = f.get('parents', [])
    if root_id in parents:
        in_teaching_panel.append(f)
    else:
        outside.append(f)

print(f'  ✅ В TeachingPanel: {len(in_teaching_panel)}')
print(f'  ❌ ВНЕ TeachingPanel (в корне или других папках): {len(outside)}')

if in_teaching_panel:
    print()
    print('Папки ВНУТРИ TeachingPanel:')
    for f in in_teaching_panel[:10]:
        print(f'  📁 {f["name"]}')
    if len(in_teaching_panel) > 10:
        print(f'  ... и ещё {len(in_teaching_panel)-10}')

if outside:
    print()
    print('Папки ВНЕ TeachingPanel (нужно удалить!):')
    for f in outside[:10]:
        print(f'  ⚠️  {f["name"]}')
    if len(outside) > 10:
        print(f'  ... и ещё {len(outside)-10}')

# Спрашиваем про удаление
print()
if all_folders:
    answer = input(f'Удалить ВСЕ {len(all_folders)} папок Teacher_*? (yes/no): ').strip().lower()
    if answer == 'yes':
        print()
        print('Удаляю...')
        deleted = 0
        for f in all_folders:
            try:
                gdrive.service.files().delete(fileId=f['id']).execute()
                deleted += 1
                if deleted % 50 == 0:
                    print(f'  Удалено: {deleted}/{len(all_folders)}')
            except Exception as e:
                print(f'  Ошибка удаления {f["name"]}: {e}')
        print(f'✅ Удалено: {deleted} папок')
    else:
        print('Отменено')
else:
    print('✅ Нет папок Teacher_* для удаления')
