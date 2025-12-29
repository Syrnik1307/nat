#!/usr/bin/env python
"""Быстрое удаление всех папок Teacher_* без подтверждения"""

import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
import django
django.setup()

from django.conf import settings
from schedule.gdrive_utils import get_gdrive_manager

gdrive = get_gdrive_manager()
root_id = settings.GDRIVE_ROOT_FOLDER_ID

query = f"'{root_id}' in parents and mimeType='application/vnd.google-apps.folder' and name contains 'Teacher_' and trashed=false"
results = gdrive.service.files().list(q=query, fields='files(id, name)').execute()
folders = results.get('files', [])

print(f'Найдено папок: {len(folders)}')
for f in folders:
    print(f'Удаляю: {f["name"]}')
    gdrive.service.files().delete(fileId=f['id']).execute()
    print('✅ Удалено')

print('Готово!')
