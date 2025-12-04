#!/usr/bin/env python
import os
import sys
sys.path.insert(0, '/var/www/teaching_panel')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')

import django
django.setup()

from schedule.gdrive_utils import get_gdrive_manager

try:
    gdrive = get_gdrive_manager()
    
    # Ищем папку TeachingPanel
    results = gdrive.service.files().list(
        q="name='TeachingPanel' and mimeType='application/vnd.google-apps.folder' and trashed=false",
        spaces='drive',
        fields='files(id, name, parents)'
    ).execute()
    
    items = results.get('files', [])
    
    if items:
        print("Найдена папка TeachingPanel:")
        for item in items:
            print(f"ID: {item['id']}")
            print(f"Имя: {item['name']}")
    else:
        print("Папка TeachingPanel не найдена. Список всех папок:")
        results = gdrive.service.files().list(
            q="mimeType='application/vnd.google-apps.folder' and trashed=false",
            spaces='drive',
            fields='files(id, name)',
            pageSize=50
        ).execute()
        for item in results.get('files', []):
            print(f"{item['name']}: {item['id']}")
            
except Exception as e:
    print(f"Ошибка: {e}")
    import traceback
    traceback.print_exc()
