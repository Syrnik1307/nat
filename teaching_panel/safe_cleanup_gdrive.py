#!/usr/bin/env python
"""
БЕЗОПАСНАЯ очистка папок Google Drive.

Этот скрипт проверяет наличие активных файлов HomeworkFile перед удалением папок.
Заменяет опасные скрипты cleanup_lectio_folders.py и cleanup_teacher_folders.py.

Что проверяется перед удалением папки Teacher_*:
1. Subscription.gdrive_folder_id - привязка к подписке
2. HomeworkFile.gdrive_file_id - файлы ДЗ внутри папки
3. CustomUser.gdrive_folder_id - привязка к учителю

ИСПОЛЬЗОВАНИЕ:
    cd teaching_panel
    source ../venv/bin/activate
    
    # Показать что будет удалено (DRY RUN)
    python safe_cleanup_gdrive.py --dry-run
    
    # Реальное удаление (перемещает в корзину, можно восстановить 30 дней)
    python safe_cleanup_gdrive.py --execute
    
    # Удалить только конкретные тестовые папки
    python safe_cleanup_gdrive.py --execute --filter "test_"
"""

import os
import sys
import re
import argparse
from collections import defaultdict

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')

import django
django.setup()

from django.conf import settings
from accounts.models import Subscription, CustomUser
from homework.models import HomeworkFile
from schedule.gdrive_utils import get_gdrive_manager


def parse_args():
    parser = argparse.ArgumentParser(description='Безопасная очистка папок Google Drive')
    parser.add_argument('--dry-run', action='store_true', help='Только показать что будет удалено')
    parser.add_argument('--execute', action='store_true', help='Реально выполнить удаление')
    parser.add_argument('--filter', type=str, help='Удалять только папки содержащие эту подстроку в имени')
    parser.add_argument('--force', action='store_true', help='Удалить даже папки с файлами (ОПАСНО!)')
    parser.add_argument('--permanent', action='store_true', help='Удалить безвозвратно (иначе в корзину)')
    return parser.parse_args()


def get_all_referenced_gdrive_ids():
    """Получить все gdrive_file_id, которые используются в системе."""
    referenced = set()
    
    # 1. HomeworkFile.gdrive_file_id
    for gid in HomeworkFile.objects.exclude(gdrive_file_id='').values_list('gdrive_file_id', flat=True):
        if gid:
            referenced.add(gid)
    
    return referenced


def get_protected_folder_ids():
    """Получить ID папок, которые НЕЛЬЗЯ удалять."""
    protected = set()
    
    # 1. Subscription.gdrive_folder_id
    for folder_id in Subscription.objects.exclude(gdrive_folder_id='').values_list('gdrive_folder_id', flat=True):
        if folder_id:
            protected.add(folder_id)
    
    # 2. CustomUser.gdrive_folder_id (если такое поле есть)
    if hasattr(CustomUser, 'gdrive_folder_id'):
        for folder_id in CustomUser.objects.exclude(gdrive_folder_id='').values_list('gdrive_folder_id', flat=True):
            if folder_id:
                protected.add(folder_id)
    
    return protected


def list_files_in_folder(gdrive, folder_id, depth=0, max_depth=3):
    """Рекурсивно получить все файлы в папке."""
    if depth > max_depth:
        return []
    
    files = []
    
    try:
        query = f"'{folder_id}' in parents and trashed=false"
        page_token = None
        
        while True:
            results = gdrive.service.files().list(
                q=query,
                spaces='drive',
                fields='nextPageToken, files(id, name, mimeType, size)',
                pageToken=page_token,
                pageSize=100
            ).execute()
            
            items = results.get('files', [])
            
            for item in items:
                if item['mimeType'] == 'application/vnd.google-apps.folder':
                    # Рекурсия для подпапок
                    files.extend(list_files_in_folder(gdrive, item['id'], depth + 1, max_depth))
                else:
                    files.append(item)
            
            page_token = results.get('nextPageToken')
            if not page_token:
                break
                
    except Exception as e:
        print(f"  [WARN] Ошибка чтения папки {folder_id}: {e}")
    
    return files


def analyze_folder(gdrive, folder, referenced_ids):
    """Анализировать папку и вернуть информацию о защищённых файлах."""
    files = list_files_in_folder(gdrive, folder['id'])
    
    protected_files = []
    for f in files:
        if f['id'] in referenced_ids:
            protected_files.append(f)
    
    return {
        'id': folder['id'],
        'name': folder['name'],
        'total_files': len(files),
        'protected_files': protected_files,
        'can_delete': len(protected_files) == 0,
    }


def main():
    args = parse_args()
    
    if not args.dry_run and not args.execute:
        print("Укажите --dry-run или --execute")
        print("Используйте --help для справки")
        return
    
    if not getattr(settings, 'USE_GDRIVE_STORAGE', False):
        print("Google Drive отключён (USE_GDRIVE_STORAGE=False)")
        return
    
    if not settings.GDRIVE_ROOT_FOLDER_ID:
        print("GDRIVE_ROOT_FOLDER_ID не задан")
        return
    
    print("=" * 60)
    print("БЕЗОПАСНАЯ ОЧИСТКА GOOGLE DRIVE")
    print("=" * 60)
    
    if args.dry_run:
        print("РЕЖИМ: DRY RUN (никакие файлы не будут удалены)")
    else:
        print("РЕЖИМ: EXECUTE (файлы будут перемещены в корзину)")
        if args.permanent:
            print("ВНИМАНИЕ: --permanent включён, файлы будут УДАЛЕНЫ НАВСЕГДА!")
    
    print()
    
    try:
        gdrive = get_gdrive_manager()
        if not hasattr(gdrive, 'service'):
            print("Используется DummyGoogleDriveManager, нельзя удалять")
            return
    except Exception as e:
        print(f"Ошибка инициализации GDrive: {e}")
        return
    
    root_id = settings.GDRIVE_ROOT_FOLDER_ID
    print(f"Корневая папка: {root_id}")
    print()
    
    # Получаем защищённые ID
    print("1. Собираем защищённые ресурсы...")
    protected_folders = get_protected_folder_ids()
    referenced_ids = get_all_referenced_gdrive_ids()
    print(f"   - Защищённых папок (подписки): {len(protected_folders)}")
    print(f"   - Защищённых файлов (HomeworkFile): {len(referenced_ids)}")
    print()
    
    # Получаем папки Teacher_*
    print("2. Ищем папки Teacher_*...")
    query = f"'{root_id}' in parents and mimeType='application/vnd.google-apps.folder' and name contains 'Teacher_' and trashed=false"
    
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
        
        all_folders.extend(results.get('files', []))
        page_token = results.get('nextPageToken')
        if not page_token:
            break
    
    print(f"   Найдено папок: {len(all_folders)}")
    
    # Фильтрация
    if args.filter:
        all_folders = [f for f in all_folders if args.filter.lower() in f['name'].lower()]
        print(f"   После фильтра '{args.filter}': {len(all_folders)}")
    
    print()
    
    if not all_folders:
        print("Нет папок для анализа")
        return
    
    # Анализируем папки
    print("3. Анализируем содержимое папок...")
    
    to_delete = []
    to_keep = []
    
    for i, folder in enumerate(all_folders, 1):
        print(f"   [{i}/{len(all_folders)}] {folder['name'][:40]}...", end="")
        
        # Проверка 1: папка защищена напрямую
        if folder['id'] in protected_folders:
            print(" [PROTECTED: subscription]")
            to_keep.append({
                'folder': folder,
                'reason': 'subscription',
            })
            continue
        
        # Проверка 2: содержит защищённые файлы
        analysis = analyze_folder(gdrive, folder, referenced_ids)
        
        if not analysis['can_delete'] and not args.force:
            print(f" [PROTECTED: {len(analysis['protected_files'])} files]")
            to_keep.append({
                'folder': folder,
                'reason': f"{len(analysis['protected_files'])} homework files",
                'files': analysis['protected_files'][:5],  # первые 5 для примера
            })
        else:
            print(f" [CAN DELETE: {analysis['total_files']} files]")
            to_delete.append({
                'folder': folder,
                'total_files': analysis['total_files'],
            })
    
    print()
    print("=" * 60)
    print("РЕЗУЛЬТАТ АНАЛИЗА")
    print("=" * 60)
    print(f"Можно удалить: {len(to_delete)}")
    print(f"Нужно сохранить: {len(to_keep)}")
    print()
    
    if to_keep:
        print("Защищённые папки (НЕ будут удалены):")
        for item in to_keep[:10]:
            folder = item['folder']
            reason = item['reason']
            print(f"  - {folder['name']} [{reason}]")
        if len(to_keep) > 10:
            print(f"  ... и ещё {len(to_keep) - 10}")
        print()
    
    if to_delete:
        print("Папки к удалению:")
        total_files_to_delete = 0
        for item in to_delete[:20]:
            folder = item['folder']
            files_count = item['total_files']
            total_files_to_delete += files_count
            created = folder.get('createdTime', 'N/A')[:10]
            print(f"  - {folder['name']} ({files_count} files, created: {created})")
        if len(to_delete) > 20:
            print(f"  ... и ещё {len(to_delete) - 20}")
        print()
        print(f"Всего файлов будет удалено: ~{total_files_to_delete}")
        print()
    
    # Удаление
    if args.execute and to_delete:
        print("=" * 60)
        print("УДАЛЕНИЕ")
        print("=" * 60)
        
        confirm = input(f"Удалить {len(to_delete)} папок? (yes/no): ").strip().lower()
        
        if confirm != 'yes':
            print("Отменено")
            return
        
        deleted = 0
        errors = 0
        
        for item in to_delete:
            folder = item['folder']
            try:
                if args.permanent:
                    gdrive.service.files().delete(fileId=folder['id']).execute()
                    action = "DELETED"
                else:
                    gdrive.service.files().update(
                        fileId=folder['id'],
                        body={'trashed': True}
                    ).execute()
                    action = "TRASHED"
                
                deleted += 1
                print(f"  [{action}] {folder['name']}")
                
            except Exception as e:
                errors += 1
                print(f"  [ERROR] {folder['name']}: {e}")
        
        print()
        print(f"Готово: {deleted} удалено, {errors} ошибок")
        if not args.permanent:
            print("Папки перемещены в корзину GDrive (можно восстановить 30 дней)")
    
    elif args.dry_run:
        print("[DRY RUN] Никакие файлы не были удалены")


if __name__ == '__main__':
    main()
