#!/usr/bin/env python
"""Показать содержимое папки TeachingPanel"""

import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
import django
django.setup()

from django.conf import settings
from schedule.gdrive_utils import get_gdrive_manager

gdrive = get_gdrive_manager()
root_id = settings.GDRIVE_ROOT_FOLDER_ID

print(f"Корневая папка ID: {root_id}")
print(f"Ссылка: https://drive.google.com/drive/folders/{root_id}")
print()

# Смотрим содержимое папки TeachingPanel
query = f"'{root_id}' in parents and trashed=false"
results = gdrive.service.files().list(q=query, fields='files(id, name, mimeType)', pageSize=100).execute()
files = results.get('files', [])

print(f'Содержимое папки ({len(files)} объектов):')
for f in files:
    icon = '📁' if 'folder' in f['mimeType'] else '📄'
    print(f'  {icon} {f["name"]}')

if not files:
    print("  (пусто)")
