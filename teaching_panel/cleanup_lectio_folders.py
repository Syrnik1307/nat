#!/usr/bin/env python
"""Очистка тестовых папок из папки lectio.space"""

import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
import django
django.setup()

from django.conf import settings
from schedule.gdrive_utils import get_gdrive_manager
from accounts.models import CustomUser

# Удаляем папку из lectio.space
gdrive = get_gdrive_manager()
root_id = settings.GDRIVE_ROOT_FOLDER_ID
query = f"'{root_id}' in parents and mimeType='application/vnd.google-apps.folder' and name contains 'Teacher_' and trashed=false"
results = gdrive.service.files().list(q=query, fields='files(id, name)').execute()
folders = results.get('files', [])
print(f'Папок в lectio.space: {len(folders)}')
for f in folders:
    print(f'Удаляю: {f["name"]}')
    gdrive.service.files().delete(fileId=f['id']).execute()
print('Готово!')

# Удаляем тестового юзера
try:
    u = CustomUser.objects.get(email='test_storage_single@test.local')
    u.delete()
    print('Юзер удалён')
except Exception as e:
    print(f'Юзер не найден: {e}')
