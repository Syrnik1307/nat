#!/usr/bin/env python
"""
Удаление всех тестовых папок Teacher_* с Google Drive
"""

import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')

import django
django.setup()

from django.conf import settings


def main():
    print("=" * 60)
    print("  ОЧИСТКА ТЕСТОВЫХ ПАПОК GOOGLE DRIVE")
    print("=" * 60)
    print()
    
    if not settings.USE_GDRIVE_STORAGE:
        print("❌ Google Drive отключен (USE_GDRIVE_STORAGE=False)")
        return
    
    if not settings.GDRIVE_ROOT_FOLDER_ID:
        print("❌ GDRIVE_ROOT_FOLDER_ID не задан")
        return
    
    try:
        from schedule.gdrive_utils import get_gdrive_manager
        gdrive = get_gdrive_manager()
        
        if not hasattr(gdrive, 'service'):
            print("❌ Используется DummyGoogleDriveManager, нельзя удалять")
            return
        
        root_id = settings.GDRIVE_ROOT_FOLDER_ID
        print(f"📁 Корневая папка: {root_id}")
        print()
        
        # Находим все папки Teacher_* в корневой папке
        query = f"'{root_id}' in parents and mimeType='application/vnd.google-apps.folder' and name contains 'Teacher_' and trashed=false"
        
        print("🔍 Ищу папки Teacher_*...")
        
        all_folders = []
        page_token = None
        
        while True:
            results = gdrive.service.files().list(
                q=query,
                spaces='drive',
                fields='nextPageToken, files(id, name, createdTime)',
                pageToken=page_token,
                pageSize=100
            ).execute()
            
            folders = results.get('files', [])
            all_folders.extend(folders)
            
            page_token = results.get('nextPageToken')
            if not page_token:
                break
        
        print(f"📊 Найдено папок: {len(all_folders)}")
        print()
        
        if not all_folders:
            print("✅ Нет папок для удаления")
            return
        
        # Показываем первые 10 для примера
        print("Примеры папок:")
        for folder in all_folders[:10]:
            print(f"  - {folder['name']} ({folder['id'][:15]}...)")
        
        if len(all_folders) > 10:
            print(f"  ... и ещё {len(all_folders) - 10} папок")
        
        print()
        
        # Подтверждение
        confirm = input(f"🗑️  Удалить ВСЕ {len(all_folders)} папок? (yes/no): ").strip().lower()
        
        if confirm != 'yes':
            print("❌ Отменено пользователем")
            return
        
        print()
        print("🗑️  Удаляю папки...")
        
        deleted = 0
        errors = 0
        
        for folder in all_folders:
            try:
                gdrive.service.files().delete(fileId=folder['id']).execute()
                deleted += 1
                if deleted % 50 == 0:
                    print(f"  Удалено: {deleted}/{len(all_folders)}")
            except Exception as e:
                errors += 1
                print(f"  ⚠️ Ошибка удаления {folder['name']}: {e}")
        
        print()
        print("=" * 60)
        print(f"✅ Удалено папок: {deleted}")
        if errors:
            print(f"⚠️ Ошибок: {errors}")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
