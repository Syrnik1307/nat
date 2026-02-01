#!/usr/bin/env python
"""
Диагностика и восстановление пропавших изображений ДЗ.

ПРОБЛЕМА: Изображения в вопросах ДЗ пропадают (отображаются как битые ссылки).
ПРИМЕР: ДЗ от 14.12 для группы "Информатика 1"

АРХИТЕКТУРА ХРАНЕНИЯ:
1. Question.config = {'imageUrl': '...', 'imageFileId': '...'}
2. HomeworkFile - модель для файлов с полями:
   - storage: 'local' | 'gdrive'
   - local_path: путь к локальному файлу
   - gdrive_file_id: ID файла на Google Drive
   - gdrive_url: прямая ссылка на GDrive

ВОЗМОЖНЫЕ ПРИЧИНЫ ПРОБЛЕМ:
1. imageFileId указывает на несуществующий HomeworkFile
2. HomeworkFile.gdrive_file_id пустой или указывает на удалённый файл
3. Файл на GDrive был перемещён в корзину cleanup-скриптом
4. Локальный файл удалён, а миграция на GDrive не завершилась

ИСПОЛЬЗОВАНИЕ:
    cd teaching_panel
    source ../venv/bin/activate
    python ../diagnose_and_restore_hw_images.py --diagnose                    # Только диагностика
    python ../diagnose_and_restore_hw_images.py --group "Информатика 1"       # Искать в группе
    python ../diagnose_and_restore_hw_images.py --date 2024-12-14             # Искать по дате
    python ../diagnose_and_restore_hw_images.py --restore                     # Восстановить
    python ../diagnose_and_restore_hw_images.py --restore --dry-run           # Проверить без изменений
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')

import django
django.setup()

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from homework.models import Homework, Question, HomeworkFile
from schedule.models import Group


def parse_args():
    parser = argparse.ArgumentParser(description='Диагностика и восстановление изображений ДЗ')
    parser.add_argument('--diagnose', action='store_true', help='Только диагностика без изменений')
    parser.add_argument('--restore', action='store_true', help='Попытаться восстановить')
    parser.add_argument('--dry-run', action='store_true', help='Показать что будет сделано без изменений')
    parser.add_argument('--group', type=str, help='Фильтр по названию группы')
    parser.add_argument('--date', type=str, help='Фильтр по дате (YYYY-MM-DD)')
    parser.add_argument('--homework-id', type=int, help='Конкретный ID домашки')
    parser.add_argument('--verbose', '-v', action='store_true', help='Подробный вывод')
    parser.add_argument('--backup', action='store_true', help='Создать бэкап перед восстановлением')
    return parser.parse_args()


def log(msg, verbose_only=False, args=None):
    if verbose_only and args and not args.verbose:
        return
    print(msg)


def get_gdrive_manager():
    """Получить менеджер Google Drive если доступен."""
    if not getattr(settings, 'USE_GDRIVE_STORAGE', False):
        return None
    try:
        from schedule.gdrive_utils import get_gdrive_manager
        return get_gdrive_manager()
    except Exception as e:
        print(f"[WARN] Не удалось инициализировать Google Drive: {e}")
        return None


def check_gdrive_file_exists(gdrive, file_id):
    """Проверить существует ли файл на GDrive."""
    if not gdrive or not file_id:
        return False, None
    try:
        file_info = gdrive.service.files().get(
            fileId=file_id,
            fields='id, name, trashed, mimeType, size',
            supportsAllDrives=True
        ).execute()
        return not file_info.get('trashed', False), file_info
    except Exception as e:
        return False, {'error': str(e)}


def search_gdrive_by_name(gdrive, filename, include_trash=True):
    """Искать файл на GDrive по имени."""
    if not gdrive or not filename:
        return []
    
    results = []
    
    # Поиск в активных файлах
    try:
        query = f"name='{filename}' and trashed=false"
        res = gdrive.service.files().list(
            q=query,
            spaces='drive',
            corpora='allDrives',
            includeItemsFromAllDrives=True,
            supportsAllDrives=True,
            fields='files(id, name, mimeType, trashed, parents)',
            pageSize=10
        ).execute()
        results.extend(res.get('files', []))
    except Exception as e:
        print(f"  [GDRIVE] Ошибка поиска: {e}")
    
    # Поиск в корзине
    if include_trash:
        try:
            query = f"name='{filename}' and trashed=true"
            res = gdrive.service.files().list(
                q=query,
                spaces='drive',
                corpora='allDrives',
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
                fields='files(id, name, mimeType, trashed)',
                pageSize=10
            ).execute()
            for f in res.get('files', []):
                f['_in_trash'] = True
            results.extend(res.get('files', []))
        except Exception as e:
            print(f"  [GDRIVE] Ошибка поиска в корзине: {e}")
    
    return results


def restore_gdrive_file_from_trash(gdrive, file_id):
    """Восстановить файл из корзины GDrive."""
    if not gdrive or not file_id:
        return False
    try:
        gdrive.service.files().update(
            fileId=file_id,
            body={'trashed': False},
            supportsAllDrives=True
        ).execute()
        return True
    except Exception as e:
        print(f"  [GDRIVE] Ошибка восстановления {file_id}: {e}")
        return False


def diagnose_question(question, gdrive, args):
    """Диагностировать один вопрос с изображением."""
    config = question.config or {}
    
    image_url = config.get('imageUrl', '')
    image_file_id = config.get('imageFileId', '')
    audio_url = config.get('audioUrl', '')
    audio_file_id = config.get('audioFileId', '')
    
    issues = []
    
    # Проверяем изображение
    if image_file_id or image_url:
        issue = diagnose_media_field(
            question, gdrive, args,
            media_type='image',
            file_id_key='imageFileId',
            url_key='imageUrl',
            file_id_value=image_file_id,
            url_value=image_url
        )
        if issue:
            issues.append(issue)
    
    # Проверяем аудио
    if audio_file_id or audio_url:
        issue = diagnose_media_field(
            question, gdrive, args,
            media_type='audio',
            file_id_key='audioFileId',
            url_key='audioUrl',
            file_id_value=audio_file_id,
            url_value=audio_url
        )
        if issue:
            issues.append(issue)
    
    return issues


def diagnose_media_field(question, gdrive, args, media_type, file_id_key, url_key, file_id_value, url_value):
    """Диагностировать одно медиа-поле (image или audio)."""
    
    # Случай 1: Есть fileId - проверяем HomeworkFile
    if file_id_value:
        try:
            hw_file = HomeworkFile.objects.get(id=file_id_value)
            
            # Проверяем локальный файл
            if hw_file.storage == HomeworkFile.STORAGE_LOCAL:
                if hw_file.local_path and os.path.exists(hw_file.local_path):
                    log(f"  [OK] Q{question.id} {media_type}: локальный файл существует", True, args)
                    return None
                else:
                    return {
                        'question_id': question.id,
                        'homework_id': question.homework_id,
                        'media_type': media_type,
                        'problem': 'LOCAL_FILE_MISSING',
                        'file_id': file_id_value,
                        'expected_path': hw_file.local_path,
                        'hw_file': hw_file,
                    }
            
            # Проверяем GDrive файл
            elif hw_file.storage == HomeworkFile.STORAGE_GDRIVE:
                if hw_file.gdrive_file_id:
                    exists, info = check_gdrive_file_exists(gdrive, hw_file.gdrive_file_id)
                    if exists:
                        log(f"  [OK] Q{question.id} {media_type}: GDrive файл существует", True, args)
                        return None
                    else:
                        return {
                            'question_id': question.id,
                            'homework_id': question.homework_id,
                            'media_type': media_type,
                            'problem': 'GDRIVE_FILE_MISSING_OR_TRASHED',
                            'file_id': file_id_value,
                            'gdrive_file_id': hw_file.gdrive_file_id,
                            'gdrive_info': info,
                            'hw_file': hw_file,
                        }
                else:
                    return {
                        'question_id': question.id,
                        'homework_id': question.homework_id,
                        'media_type': media_type,
                        'problem': 'GDRIVE_ID_EMPTY',
                        'file_id': file_id_value,
                        'hw_file': hw_file,
                    }
        
        except HomeworkFile.DoesNotExist:
            return {
                'question_id': question.id,
                'homework_id': question.homework_id,
                'media_type': media_type,
                'problem': 'HOMEWORK_FILE_NOT_FOUND',
                'file_id': file_id_value,
            }
    
    # Случай 2: Только URL (старый формат)
    elif url_value:
        # Локальный путь /media/...
        if url_value.startswith('/media/'):
            local_path = url_value.replace('/media/', str(settings.MEDIA_ROOT) + '/')
            if os.path.exists(local_path):
                log(f"  [OK] Q{question.id} {media_type}: локальный URL файл существует", True, args)
                return None
            else:
                return {
                    'question_id': question.id,
                    'homework_id': question.homework_id,
                    'media_type': media_type,
                    'problem': 'LOCAL_URL_FILE_MISSING',
                    'url': url_value,
                    'expected_path': local_path,
                }
        
        # GDrive URL
        elif 'drive.google.com' in url_value or 'lh3.googleusercontent.com' in url_value:
            # Извлекаем ID из URL
            import re
            gdrive_id = None
            patterns = [
                r'[?&]id=([a-zA-Z0-9_-]+)',
                r'/file/d/([a-zA-Z0-9_-]+)',
                r'/d/([a-zA-Z0-9_-]+)',
                r'/open\?id=([a-zA-Z0-9_-]+)',
            ]
            for pattern in patterns:
                match = re.search(pattern, url_value)
                if match:
                    gdrive_id = match.group(1)
                    break
            
            if gdrive_id:
                exists, info = check_gdrive_file_exists(gdrive, gdrive_id)
                if exists:
                    log(f"  [OK] Q{question.id} {media_type}: GDrive URL файл существует", True, args)
                    return None
                else:
                    return {
                        'question_id': question.id,
                        'homework_id': question.homework_id,
                        'media_type': media_type,
                        'problem': 'GDRIVE_URL_FILE_MISSING',
                        'url': url_value,
                        'gdrive_file_id': gdrive_id,
                        'gdrive_info': info,
                    }
            else:
                return {
                    'question_id': question.id,
                    'homework_id': question.homework_id,
                    'media_type': media_type,
                    'problem': 'GDRIVE_URL_INVALID',
                    'url': url_value,
                }
        
        # API прокси URL
        elif url_value.startswith('/api/homework/file/'):
            import re
            match = re.search(r'/api/homework/file/([^/]+)/', url_value)
            if match:
                file_id = match.group(1)
                # Рекурсивно проверяем через HomeworkFile
                return diagnose_media_field(
                    question, gdrive, args,
                    media_type=media_type,
                    file_id_key=file_id_key,
                    url_key=url_key,
                    file_id_value=file_id,
                    url_value=None
                )
    
    return None


def backup_question_configs(questions, backup_file):
    """Создать бэкап config для списка вопросов."""
    backup_data = []
    for q in questions:
        backup_data.append({
            'question_id': q.id,
            'homework_id': q.homework_id,
            'config': q.config,
            'backup_time': datetime.now().isoformat(),
        })
    
    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(backup_data, f, ensure_ascii=False, indent=2)
    
    print(f"[BACKUP] Сохранено {len(backup_data)} вопросов в {backup_file}")


def try_restore_issue(issue, gdrive, args):
    """Попытаться восстановить проблему."""
    problem = issue['problem']
    question_id = issue['question_id']
    media_type = issue['media_type']
    
    print(f"\n[RESTORE] Q{question_id} ({media_type}): {problem}")
    
    if args.dry_run:
        print(f"  [DRY-RUN] Пропускаем...")
        return False
    
    # Восстановление из корзины GDrive
    if problem in ('GDRIVE_FILE_MISSING_OR_TRASHED', 'GDRIVE_URL_FILE_MISSING'):
        gdrive_file_id = issue.get('gdrive_file_id')
        gdrive_info = issue.get('gdrive_info', {})
        
        # Если файл в корзине - восстанавливаем
        if gdrive_info and gdrive_info.get('trashed'):
            print(f"  [RESTORING] Восстанавливаем из корзины: {gdrive_file_id}")
            if restore_gdrive_file_from_trash(gdrive, gdrive_file_id):
                print(f"  [SUCCESS] Файл восстановлен из корзины")
                return True
        
        # Если файл удалён насовсем - ищем по имени
        hw_file = issue.get('hw_file')
        if hw_file:
            print(f"  [SEARCHING] Ищем файл {hw_file.original_name} на GDrive...")
            candidates = search_gdrive_by_name(gdrive, hw_file.original_name)
            if candidates:
                for c in candidates:
                    print(f"    - {c['name']} (ID: {c['id']}, trash: {c.get('_in_trash', c.get('trashed'))})")
                
                # Берём первый подходящий
                best = candidates[0]
                new_gdrive_id = best['id']
                
                # Если в корзине - сначала восстанавливаем
                if best.get('_in_trash') or best.get('trashed'):
                    if not restore_gdrive_file_from_trash(gdrive, new_gdrive_id):
                        print(f"  [FAIL] Не удалось восстановить из корзины")
                        return False
                
                # Обновляем HomeworkFile
                hw_file.gdrive_file_id = new_gdrive_id
                hw_file.gdrive_url = f"https://drive.google.com/uc?export=download&id={new_gdrive_id}"
                hw_file.save(update_fields=['gdrive_file_id', 'gdrive_url'])
                print(f"  [SUCCESS] HomeworkFile {hw_file.id} обновлён с новым GDrive ID: {new_gdrive_id}")
                return True
            else:
                print(f"  [NOT FOUND] Файл не найден на GDrive")
    
    # HomeworkFile не найден - нужно искать файл и создать запись
    elif problem == 'HOMEWORK_FILE_NOT_FOUND':
        file_id = issue.get('file_id')
        print(f"  [WARN] HomeworkFile {file_id} не существует в БД")
        print(f"  [TODO] Нужно найти оригинальный файл и создать HomeworkFile")
        # Тут можно добавить логику поиска по file_id в GDrive
    
    # Локальный файл отсутствует
    elif problem == 'LOCAL_FILE_MISSING':
        hw_file = issue.get('hw_file')
        if hw_file and hw_file.gdrive_file_id:
            print(f"  [INFO] Файл есть на GDrive ({hw_file.gdrive_file_id}), переключаем storage")
            hw_file.storage = HomeworkFile.STORAGE_GDRIVE
            hw_file.local_path = ''
            hw_file.save(update_fields=['storage', 'local_path'])
            print(f"  [SUCCESS] HomeworkFile переключён на GDrive")
            return True
        elif hw_file:
            # Ищем на GDrive по имени
            print(f"  [SEARCHING] Ищем файл {hw_file.original_name} на GDrive...")
            candidates = search_gdrive_by_name(gdrive, hw_file.original_name)
            if candidates:
                best = candidates[0]
                if best.get('_in_trash') or best.get('trashed'):
                    restore_gdrive_file_from_trash(gdrive, best['id'])
                
                hw_file.gdrive_file_id = best['id']
                hw_file.gdrive_url = f"https://drive.google.com/uc?export=download&id={best['id']}"
                hw_file.storage = HomeworkFile.STORAGE_GDRIVE
                hw_file.local_path = ''
                hw_file.save(update_fields=['gdrive_file_id', 'gdrive_url', 'storage', 'local_path'])
                print(f"  [SUCCESS] Найден и привязан GDrive файл: {best['id']}")
                return True
    
    return False


def main():
    args = parse_args()
    
    if not args.diagnose and not args.restore:
        print("Укажите --diagnose или --restore")
        print("Используйте --help для справки")
        return
    
    print("=" * 60)
    print("ДИАГНОСТИКА ИЗОБРАЖЕНИЙ ДОМАШНИХ ЗАДАНИЙ")
    print("=" * 60)
    
    # Фильтруем домашки
    homeworks = Homework.objects.filter(status='published')
    
    if args.homework_id:
        homeworks = homeworks.filter(id=args.homework_id)
        print(f"Фильтр: homework_id = {args.homework_id}")
    
    if args.group:
        # Ищем группу
        groups = Group.objects.filter(name__icontains=args.group)
        if groups.exists():
            print(f"Фильтр: группа содержит '{args.group}'")
            group_ids = list(groups.values_list('id', flat=True))
            homeworks = homeworks.filter(assigned_groups__id__in=group_ids).distinct()
        else:
            print(f"[WARN] Группа '{args.group}' не найдена")
    
    if args.date:
        try:
            target_date = datetime.strptime(args.date, '%Y-%m-%d').date()
            homeworks = homeworks.filter(
                created_at__date=target_date
            )
            print(f"Фильтр: дата = {target_date}")
        except ValueError:
            print(f"[ERROR] Неверный формат даты. Используйте YYYY-MM-DD")
            return
    
    homeworks = homeworks.order_by('-created_at')
    
    print(f"\nНайдено домашек: {homeworks.count()}")
    
    # Получаем GDrive manager
    gdrive = get_gdrive_manager()
    if not gdrive:
        print("[WARN] Google Drive недоступен, проверка GDrive файлов невозможна")
    
    # Диагностика
    all_issues = []
    all_questions = []
    
    for hw in homeworks:
        groups_str = ', '.join(hw.assigned_groups.values_list('name', flat=True)[:3])
        print(f"\n[HW {hw.id}] {hw.title} ({hw.created_at.strftime('%Y-%m-%d')}) -> {groups_str}")
        
        questions = hw.questions.all()
        for q in questions:
            config = q.config or {}
            has_media = config.get('imageUrl') or config.get('imageFileId') or \
                       config.get('audioUrl') or config.get('audioFileId')
            
            if has_media:
                all_questions.append(q)
                issues = diagnose_question(q, gdrive, args)
                if issues:
                    all_issues.extend(issues)
                    for issue in issues:
                        print(f"  [ISSUE] Q{q.id}: {issue['media_type']} - {issue['problem']}")
    
    print("\n" + "=" * 60)
    print(f"ИТОГО: {len(all_issues)} проблем в {len(all_questions)} вопросах с медиа")
    print("=" * 60)
    
    if not all_issues:
        print("\n[OK] Все изображения доступны!")
        return
    
    # Группируем проблемы по типу
    problems_by_type = {}
    for issue in all_issues:
        problem = issue['problem']
        problems_by_type.setdefault(problem, []).append(issue)
    
    print("\nПроблемы по типам:")
    for problem, issues in problems_by_type.items():
        print(f"  {problem}: {len(issues)}")
    
    # Восстановление
    if args.restore:
        print("\n" + "=" * 60)
        print("ВОССТАНОВЛЕНИЕ")
        print("=" * 60)
        
        if args.backup:
            backup_file = f"hw_images_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            backup_question_configs(all_questions, backup_file)
        
        restored = 0
        failed = 0
        
        for issue in all_issues:
            if try_restore_issue(issue, gdrive, args):
                restored += 1
            else:
                failed += 1
        
        print("\n" + "=" * 60)
        print(f"РЕЗУЛЬТАТ: Восстановлено {restored}, Не удалось {failed}")
        print("=" * 60)


if __name__ == '__main__':
    main()
