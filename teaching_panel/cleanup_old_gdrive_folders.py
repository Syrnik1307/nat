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
from homework.models import HomeworkFile
from schedule.gdrive_utils import get_gdrive_manager
import logging

logger = logging.getLogger(__name__)


def get_all_homework_file_gdrive_ids():
    """Получить все gdrive_file_id из HomeworkFile."""
    return set(
        HomeworkFile.objects
        .exclude(gdrive_file_id='')
        .values_list('gdrive_file_id', flat=True)
    )


def list_files_in_folder_recursive(gdrive, folder_id, max_depth=3, current_depth=0):
    """Рекурсивно получить все ID файлов в папке."""
    if current_depth > max_depth:
        return set()
    
    file_ids = set()
    
    try:
        query = f"'{folder_id}' in parents and trashed=false"
        page_token = None
        
        while True:
            results = gdrive.service.files().list(
                q=query,
                spaces='drive',
                fields='nextPageToken, files(id, mimeType)',
                pageToken=page_token,
                pageSize=100
            ).execute()
            
            for item in results.get('files', []):
                if item['mimeType'] == 'application/vnd.google-apps.folder':
                    file_ids.update(list_files_in_folder_recursive(
                        gdrive, item['id'], max_depth, current_depth + 1
                    ))
                else:
                    file_ids.add(item['id'])
            
            page_token = results.get('nextPageToken')
            if not page_token:
                break
    except Exception as e:
        logger.warning(f"Ошибка чтения папки {folder_id}: {e}")
    
    return file_ids


def folder_contains_homework_files(gdrive, folder_id, homework_file_ids):
    """Проверить, содержит ли папка файлы, используемые в HomeworkFile."""
    folder_files = list_files_in_folder_recursive(gdrive, folder_id)
    protected = folder_files & homework_file_ids
    return len(protected), protected


def cleanup_old_teacher_folders(dry_run=True, skip_homework_check=False):
    """
    Удалить старые папки учителей, которые не привязаны к подпискам
    И не содержат файлов HomeworkFile.
    
    Args:
        dry_run: Если True, только показать что будет удалено, без удаления
        skip_homework_check: Если True, не проверять HomeworkFile (ОПАСНО!)
    """
    if not settings.USE_GDRIVE_STORAGE or not settings.GDRIVE_ROOT_FOLDER_ID:
        print("Google Drive не настроен (USE_GDRIVE_STORAGE или GDRIVE_ROOT_FOLDER_ID)")
        return
    
    try:
        gdrive = get_gdrive_manager()
        root_folder_id = settings.GDRIVE_ROOT_FOLDER_ID
        
        print(f"Сканирую папки в корневой директории lectio.space (ID: {root_folder_id})...")
        
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
        
        print(f"Найдено папок в корне: {len(all_folders)}")
        
        # Получаем ID папок, которые привязаны к активным подпискам
        active_folder_ids = set(
            Subscription.objects
            .exclude(gdrive_folder_id='')
            .values_list('gdrive_folder_id', flat=True)
        )
        
        print(f"Папок привязано к подпискам: {len(active_folder_ids)}")
        
        # НОВОЕ: Получаем все gdrive_file_id из HomeworkFile
        if not skip_homework_check:
            homework_file_ids = get_all_homework_file_gdrive_ids()
            print(f"Файлов HomeworkFile на GDrive: {len(homework_file_ids)}")
        else:
            homework_file_ids = set()
            print("ВНИМАНИЕ: Проверка HomeworkFile отключена (skip_homework_check=True)")
        
        # Фильтруем папки учителей (Teacher_* или teacher_*)
        teacher_folders = [
            f for f in all_folders 
            if f['name'].lower().startswith('teacher_')
        ]
        
        print(f"Папок учителей (Teacher_*): {len(teacher_folders)}")
        
        # Анализируем каждую папку
        print("\nАнализируем содержимое папок...")
        
        to_delete = []
        to_keep_subscription = []
        to_keep_homework = []
        
        for i, f in enumerate(teacher_folders, 1):
            folder_id = f['id']
            folder_name = f['name']
            
            # Проверка 1: привязана к подписке
            if folder_id in active_folder_ids:
                to_keep_subscription.append(f)
                continue
            
            # Проверка 2: содержит файлы HomeworkFile
            if not skip_homework_check and homework_file_ids:
                hw_count, _ = folder_contains_homework_files(gdrive, folder_id, homework_file_ids)
                if hw_count > 0:
                    f['_hw_count'] = hw_count
                    to_keep_homework.append(f)
                    print(f"  [{i}/{len(teacher_folders)}] {folder_name}: PROTECTED ({hw_count} homework files)")
                    continue
            
            to_delete.append(f)
            print(f"  [{i}/{len(teacher_folders)}] {folder_name}: can delete")
        
        print(f"\nРЕЗУЛЬТАТ:")
        print(f"   - Оставить (привязаны к подпискам): {len(to_keep_subscription)}")
        print(f"   - Оставить (содержат HomeworkFile): {len(to_keep_homework)}")
        print(f"   - Удалить (не используются): {len(to_delete)}")
        
        if to_keep_subscription:
            print(f"\nПапки с подписками (ОСТАНУТСЯ):")
            for f in to_keep_subscription[:10]:
                print(f"   {f['name']} (ID: {f['id']})")
            if len(to_keep_subscription) > 10:
                print(f"   ... и ещё {len(to_keep_subscription) - 10}")
        
        if to_keep_homework:
            print(f"\nПапки с файлами ДЗ (ОСТАНУТСЯ):")
            for f in to_keep_homework[:10]:
                hw_count = f.get('_hw_count', '?')
                print(f"   {f['name']} ({hw_count} homework files)")
            if len(to_keep_homework) > 10:
                print(f"   ... и ещё {len(to_keep_homework) - 10}")
        
        if to_delete:
            print(f"\nПапки которые будут УДАЛЕНЫ:")
            for f in to_delete:
                print(f"   {f['name']} (ID: {f['id']}, создана: {f.get('createdTime', 'N/A')[:10]})")
            
            if dry_run:
                print(f"\nDRY RUN: Никакие папки не удалены.")
                print(f"   Для реального удаления запустите: cleanup_old_teacher_folders(dry_run=False)")
            else:
                print(f"\nУдаляю {len(to_delete)} папок...")
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
                        print(f"   Удалено: {f['name']}")
                    except Exception as e:
                        failed += 1
                        print(f"   Ошибка удаления {f['name']}: {e}")
                
                print(f"\nГотово! Удалено: {deleted}, Ошибок: {failed}")
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
