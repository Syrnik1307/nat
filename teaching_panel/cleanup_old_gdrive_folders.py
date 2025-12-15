#!/usr/bin/env python
"""
Скрипт для очистки старых папок учителей на Google Drive.

Удаляет все папки Teacher_* и teacher_* из корневой папки lectio.space,
КРОМЕ папок, которые привязаны к активным подпискам.

Запуск:
    cd teaching_panel
    python manage.py shell < cleanup_old_gdrive_folders.py
    
или интерактивно:
    python manage.py shell
    >>> exec(open('cleanup_old_gdrive_folders.py').read())
"""
import os
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from django.conf import settings
from accounts.models import Subscription
from schedule.gdrive_utils import get_gdrive_manager
import logging

logger = logging.getLogger(__name__)

def cleanup_old_teacher_folders(dry_run=True):
    """
    Удалить старые папки учителей, которые не привязаны к подпискам.
    
    Args:
        dry_run: Если True, только показать что будет удалено, без удаления
    """
    if not settings.USE_GDRIVE_STORAGE or not settings.GDRIVE_ROOT_FOLDER_ID:
        print("❌ Google Drive не настроен (USE_GDRIVE_STORAGE или GDRIVE_ROOT_FOLDER_ID)")
        return
    
    try:
        gdrive = get_gdrive_manager()
        root_folder_id = settings.GDRIVE_ROOT_FOLDER_ID
        
        print(f"🔍 Сканирую папки в корневой директории lectio.space (ID: {root_folder_id})...")
        
        # Получаем все папки учителей
        query = f"mimeType='application/vnd.google-apps.folder' and '{root_folder_id}' in parents and trashed=false"
        
        all_folders = []
        page_token = None
        
        while True:
            results = gdrive.service.files().list(
                q=query,
                spaces='drive',
                fields='nextPageToken, files(id, name, createdTime)',
                pageToken=page_token
            ).execute()
            
            all_folders.extend(results.get('files', []))
            page_token = results.get('nextPageToken')
            
            if not page_token:
                break
        
        print(f"📁 Найдено папок в корне: {len(all_folders)}")
        
        # Получаем ID папок, которые привязаны к активным подпискам
        active_folder_ids = set(
            Subscription.objects
            .exclude(gdrive_folder_id='')
            .values_list('gdrive_folder_id', flat=True)
        )
        
        print(f"✅ Папок привязано к подпискам: {len(active_folder_ids)}")
        
        # Фильтруем папки учителей (Teacher_* или teacher_*)
        teacher_folders = [
            f for f in all_folders 
            if f['name'].lower().startswith('teacher_')
        ]
        
        print(f"👤 Папок учителей (Teacher_*): {len(teacher_folders)}")
        
        # Определяем что удалить
        to_delete = [
            f for f in teacher_folders 
            if f['id'] not in active_folder_ids
        ]
        
        to_keep = [
            f for f in teacher_folders 
            if f['id'] in active_folder_ids
        ]
        
        print(f"\n📋 РЕЗУЛЬТАТ:")
        print(f"   - Оставить (привязаны к подпискам): {len(to_keep)}")
        print(f"   - Удалить (не привязаны): {len(to_delete)}")
        
        if to_keep:
            print(f"\n✅ Папки которые ОСТАНУТСЯ:")
            for f in to_keep[:10]:
                print(f"   📁 {f['name']} (ID: {f['id']})")
            if len(to_keep) > 10:
                print(f"   ... и ещё {len(to_keep) - 10}")
        
        if to_delete:
            print(f"\n🗑️ Папки которые будут УДАЛЕНЫ:")
            for f in to_delete:
                print(f"   📁 {f['name']} (ID: {f['id']}, создана: {f.get('createdTime', 'N/A')[:10]})")
            
            if dry_run:
                print(f"\n⚠️ DRY RUN: Никакие папки не удалены.")
                print(f"   Для реального удаления запустите: cleanup_old_teacher_folders(dry_run=False)")
            else:
                print(f"\n🗑️ Удаляю {len(to_delete)} папок...")
                deleted = 0
                failed = 0
                
                for f in to_delete:
                    try:
                        # Перемещаем в корзину (можно восстановить)
                        gdrive.service.files().update(
                            fileId=f['id'],
                            body={'trashed': True}
                        ).execute()
                        deleted += 1
                        print(f"   ✓ Удалено: {f['name']}")
                    except Exception as e:
                        failed += 1
                        print(f"   ✗ Ошибка удаления {f['name']}: {e}")
                
                print(f"\n✅ Готово! Удалено: {deleted}, Ошибок: {failed}")
                print(f"   Папки перемещены в корзину Google Drive (можно восстановить в течение 30 дней)")
        else:
            print(f"\n✅ Нет папок для удаления!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


def list_all_root_folders():
    """Показать все папки в корневой директории"""
    if not settings.USE_GDRIVE_STORAGE or not settings.GDRIVE_ROOT_FOLDER_ID:
        print("❌ Google Drive не настроен")
        return
    
    try:
        gdrive = get_gdrive_manager()
        root_folder_id = settings.GDRIVE_ROOT_FOLDER_ID
        
        query = f"mimeType='application/vnd.google-apps.folder' and '{root_folder_id}' in parents and trashed=false"
        
        results = gdrive.service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name, createdTime)',
            orderBy='createdTime desc',
            pageSize=100
        ).execute()
        
        folders = results.get('files', [])
        
        print(f"📁 Папки в корневой директории ({len(folders)}):\n")
        
        for i, f in enumerate(folders, 1):
            created = f.get('createdTime', 'N/A')[:10]
            print(f"  {i:2}. {f['name']:50} | {created} | ID: {f['id']}")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")


if __name__ == '__main__':
    print("=" * 60)
    print("🧹 ОЧИСТКА СТАРЫХ ПАПОК УЧИТЕЛЕЙ НА GOOGLE DRIVE")
    print("=" * 60)
    print()
    
    # Сначала показать что есть
    cleanup_old_teacher_folders(dry_run=True)
    
    print()
    print("=" * 60)
    print("💡 Для реального удаления выполните в Django shell:")
    print("   cleanup_old_teacher_folders(dry_run=False)")
    print("=" * 60)
