#!/usr/bin/env python
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
import django
django.setup()

from schedule.gdrive_utils import get_gdrive_manager
from django.conf import settings

print('Тестирую Google Drive...')
gdrive = get_gdrive_manager()
print('✅ GoogleDriveManager инициализирован')

print(f'Root Folder ID: {settings.GDRIVE_ROOT_FOLDER_ID}')
print(f'USE_GDRIVE_STORAGE: {settings.USE_GDRIVE_STORAGE}')

# Попробуем создать тестовую папку
test_folder = gdrive.create_folder('_test_folder', parent_folder_id=settings.GDRIVE_ROOT_FOLDER_ID)
print(f'✅ Тестовая папка создана: {test_folder}')

# Удалим её
gdrive.delete_file(test_folder)
print('✅ Тестовая папка удалена')
print('🎉 Google Drive настроен и работает!')
