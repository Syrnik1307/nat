"""
Management command для миграции локальных файлов домашек на Google Drive.

Запускается периодически через cron/systemd timer.
Обрабатывает файлы пачками с rate limiting для масштабируемости.

Usage:
    python manage.py migrate_homework_files              # Мигрировать до 50 файлов
    python manage.py migrate_homework_files --batch=100  # Мигрировать до 100 файлов
    python manage.py migrate_homework_files --dry-run    # Показать что будет мигрировано

Рекомендуемый cron (каждые 2 минуты):
    */2 * * * * cd /var/www/teaching_panel/teaching_panel && /var/www/teaching_panel/venv/bin/python manage.py migrate_homework_files --batch=20 >> /var/log/homework_migration.log 2>&1
"""

import os
import time
import logging
import socket
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from homework.models import HomeworkFile

logger = logging.getLogger(__name__)

# Таймауты для миграции файлов
FILE_MIGRATION_TIMEOUT = 120  # секунд на один файл (включает upload)
FOLDER_OPERATION_TIMEOUT = 30  # секунд на операции с папками


class Command(BaseCommand):
    help = 'Мигрировать локальные файлы домашек на Google Drive'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch',
            type=int,
            default=50,
            help='Максимальное количество файлов для миграции за один запуск (default: 50)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Только показать что будет мигрировано, не выполнять',
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=0.5,
            help='Задержка между миграциями в секундах (rate limiting, default: 0.5)',
        )

    def handle(self, *args, **options):
        batch_size = options['batch']
        dry_run = options['dry_run']
        delay = options['delay']
        
        # Проверяем что GDrive включён
        if not getattr(settings, 'USE_GDRIVE_STORAGE', False):
            self.stdout.write(self.style.WARNING('USE_GDRIVE_STORAGE is False, nothing to migrate'))
            return
        
        # Используем lock чтобы избежать одновременного запуска
        lock_key = 'migrate_homework_files_lock'
        if cache.get(lock_key):
            self.stdout.write(self.style.WARNING('Another migration is already running, skipping'))
            return
        
        try:
            # Устанавливаем lock на 10 минут
            cache.set(lock_key, True, 600)
            
            # Получаем файлы для миграции (самые старые первыми)
            pending_files = HomeworkFile.objects.filter(
                storage=HomeworkFile.STORAGE_LOCAL
            ).exclude(
                local_path=''
            ).order_by('created_at')[:batch_size]
            
            total = pending_files.count()
            
            if total == 0:
                self.stdout.write('No files to migrate')
                return
            
            self.stdout.write(f'Found {total} files to migrate (batch={batch_size}, delay={delay}s)')
            
            if dry_run:
                self.stdout.write(self.style.WARNING('=== DRY RUN ==='))
                for hw_file in pending_files:
                    age = (timezone.now() - hw_file.created_at).total_seconds()
                    self.stdout.write(f'  - {hw_file.id}: {hw_file.original_name} ({hw_file.size // 1024} KB, age: {age:.0f}s)')
                return
            
            migrated = 0
            failed = 0
            
            for hw_file in pending_files:
                try:
                    self._migrate_file(hw_file)
                    migrated += 1
                    self.stdout.write(self.style.SUCCESS(f'  [{migrated}/{total}] {hw_file.id}: migrated'))
                except socket.timeout as e:
                    failed += 1
                    self.stdout.write(self.style.ERROR(f'  [{migrated + failed}/{total}] {hw_file.id}: TIMEOUT - {e}'))
                    logger.error(f'migrate_homework_files: timeout migrating {hw_file.id}: {e}')
                except Exception as e:
                    failed += 1
                    error_msg = str(e).lower()
                    if 'timeout' in error_msg or 'timed out' in error_msg:
                        self.stdout.write(self.style.ERROR(f'  [{migrated + failed}/{total}] {hw_file.id}: TIMEOUT - {e}'))
                        logger.error(f'migrate_homework_files: timeout migrating {hw_file.id}: {e}')
                    else:
                        self.stdout.write(self.style.ERROR(f'  [{migrated + failed}/{total}] {hw_file.id}: FAILED - {e}'))
                        logger.error(f'migrate_homework_files: failed to migrate {hw_file.id}: {e}', exc_info=True)
                
                # Rate limiting - задержка между запросами к GDrive API
                if delay > 0:
                    time.sleep(delay)
            
            self.stdout.write(self.style.SUCCESS(f'\nDone: {migrated} migrated, {failed} failed'))
            
        finally:
            cache.delete(lock_key)

    def _migrate_file(self, hw_file: HomeworkFile):
        """
        Мигрировать один файл на GDrive.
        
        Использует retry_on_error декоратор из gdrive_utils для автоматических
        повторных попыток при таймаутах и сетевых ошибках.
        """
        from schedule.gdrive_utils import get_gdrive_manager, TimeoutError
        
        if not hw_file.local_path or not os.path.exists(hw_file.local_path):
            raise FileNotFoundError(f'Local file not found: {hw_file.local_path}')
        
        gdrive = get_gdrive_manager()
        
        # Для файлов учителей используем их папку, для студентов - общую папку
        if hw_file.teacher:
            # get_or_create_teacher_folder уже обёрнут в retry_on_error с таймаутом
            teacher_folders = gdrive.get_or_create_teacher_folder(hw_file.teacher)
            homework_root_folder_id = teacher_folders.get('homework')
            uploads_cache_key = f"gdrive_uploads_folder_{hw_file.teacher.id}"
            folder_name = 'Uploads'
        else:
            # Студенческие файлы загружаются в общую папку StudentUploads в корне
            uploads_cache_key = "gdrive_student_uploads_folder"
            homework_root_folder_id = gdrive.root_folder_id
            folder_name = 'StudentUploads'
        
        uploads_folder_id = cache.get(uploads_cache_key)
        
        if not uploads_folder_id:
            # Создаём/находим подпапку Uploads или StudentUploads
            try:
                query = (
                    f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' "
                    f"and trashed=false and '{homework_root_folder_id}' in parents"
                )
                results = gdrive.service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
                items = results.get('files', [])
                if items:
                    uploads_folder_id = items[0]['id']
                else:
                    uploads_folder_id = gdrive.create_folder(folder_name, homework_root_folder_id)
            except (TimeoutError, socket.timeout) as e:
                logger.warning(f'Timeout finding/creating folder, will retry: {e}')
                uploads_folder_id = gdrive.create_folder(folder_name, homework_root_folder_id)
            except Exception:
                uploads_folder_id = gdrive.create_folder(folder_name, homework_root_folder_id)
            
            cache.set(uploads_cache_key, uploads_folder_id, 86400)
        
        # Загружаем файл на GDrive
        storage_name = f"hw_{hw_file.id}_{hw_file.original_name}"
        
        with open(hw_file.local_path, 'rb') as f:
            result = gdrive.upload_file(
                f,
                storage_name,
                folder_id=uploads_folder_id,
                mime_type=hw_file.mime_type,
                teacher=hw_file.teacher
            )
        
        gdrive_file_id = result['file_id']
        gdrive_url = gdrive.get_direct_download_link(gdrive_file_id)
        
        # Обновляем запись в БД
        hw_file.storage = HomeworkFile.STORAGE_GDRIVE
        hw_file.gdrive_file_id = gdrive_file_id
        hw_file.gdrive_url = gdrive_url
        hw_file.migrated_at = timezone.now()
        hw_file.save(update_fields=['storage', 'gdrive_file_id', 'gdrive_url', 'migrated_at'])
        
        # Удаляем локальный файл
        hw_file.delete_local_file()
        
        logger.info(f'migrate_homework_files: {hw_file.id} -> GDrive {gdrive_file_id}')
