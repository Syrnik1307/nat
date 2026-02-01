#!/usr/bin/env python
"""
DEPRECATED - ОПАСНЫЙ СКРИПТ!

Этот скрипт ЗАБЛОКИРОВАН, так как он удалял папки Teacher_*
БЕЗ ПРОВЕРКИ наличия активных файлов HomeworkFile внутри.

Это приводило к потере изображений в домашних заданиях!

См. RCA_HOMEWORK_IMAGES_LOSS.md для деталей.

Используйте вместо него:
  - cleanup_old_gdrive_folders.py (проверяет подписки)
  - safe_cleanup_gdrive.py (проверяет HomeworkFile)
"""

import sys

print("=" * 60)
print("ЭТОТ СКРИПТ ЗАБЛОКИРОВАН!")
print("=" * 60)
print()
print("Причина: Скрипт удалял папки Teacher_* без проверки,")
print("что приводило к потере файлов домашних заданий.")
print()
print("Используйте безопасные альтернативы:")
print("  - python cleanup_old_gdrive_folders.py (проверяет подписки)")  
print("  - python safe_cleanup_gdrive.py (проверяет HomeworkFile)")
print()
print("Подробности: см. RCA_HOMEWORK_IMAGES_LOSS.md")
print("=" * 60)

sys.exit(1)


# ============================================================
# СТАРЫЙ ОПАСНЫЙ КОД (ОТКЛЮЧЁН) - см. ниже
# ============================================================


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
