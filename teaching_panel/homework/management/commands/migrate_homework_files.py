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


# Максимальное количество ПОСЛЕДОВАТЕЛЬНЫХ ошибок до остановки batch
# Если GDrive лежит, нет смысла генерировать сотни событий в Sentry
CIRCUIT_BREAKER_THRESHOLD = 3

# Per-file cooldown: сколько раз файл может упасть до пометки как "отравленный"
FILE_MAX_FAILURES = 5
# Начальный cooldown для файла после превышения лимита неудач (секунды)
FILE_COOLDOWN_BASE = 1800  # 30 минут
# Максимальный cooldown для файла (секунды)
FILE_COOLDOWN_MAX = 86400  # 24 часа
# Глобальный cooldown после срабатывания circuit breaker (секунды)
GLOBAL_COOLDOWN = 600  # 10 минут


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
        
        # Глобальный cooldown после срабатывания circuit breaker
        global_cooldown_key = 'migrate_homework_files_global_cooldown'
        cooldown_remaining = cache.get(global_cooldown_key)
        if cooldown_remaining:
            self.stdout.write(
                self.style.WARNING(
                    f'Global cooldown active (circuit breaker was triggered). Skipping.'
                )
            )
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
            all_pending = HomeworkFile.objects.filter(
                storage=HomeworkFile.STORAGE_LOCAL
            ).exclude(
                local_path=''
            ).order_by('created_at')[:batch_size]

            # Фильтруем файлы с активным per-file cooldown
            pending_files = []
            skipped_cooldown = 0
            for hf in all_pending:
                cooldown_key = f'migrate_hw_file_cooldown_{hf.id}'
                if cache.get(cooldown_key):
                    skipped_cooldown += 1
                else:
                    pending_files.append(hf)

            if skipped_cooldown > 0:
                self.stdout.write(
                    self.style.WARNING(f'Skipped {skipped_cooldown} files on cooldown')
                )
            
            total = len(pending_files)
            
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
            consecutive_failures = 0
            
            for hw_file in pending_files:
                try:
                    self._migrate_file(hw_file)
                    migrated += 1
                    consecutive_failures = 0  # сброс при успехе
                    self.stdout.write(self.style.SUCCESS(f'  [{migrated}/{total}] {hw_file.id}: migrated'))
                except socket.timeout as e:
                    failed += 1
                    consecutive_failures += 1
                    self.stdout.write(self.style.ERROR(f'  [{migrated + failed}/{total}] {hw_file.id}: TIMEOUT - {e}'))
                    logger.error(f'migrate_homework_files: timeout migrating {hw_file.id}: {e}')
                except Exception as e:
                    failed += 1
                    consecutive_failures += 1
                    error_msg = str(e).lower()
                    
                    # Классификация ошибок для правильного логирования
                    if 'redirect' in error_msg and 'location' in error_msg:
                        # RedirectMissingLocation - транзиентная ошибка Google API
                        self.stdout.write(
                            self.style.WARNING(
                                f'  [{migrated + failed}/{total}] {hw_file.id}: '
                                f'GDRIVE REDIRECT ERROR (transient) - {e}'
                            )
                        )
                        logger.warning(
                            f'migrate_homework_files: Google Drive redirect error '
                            f'for {hw_file.id} (transient API issue): {e}'
                        )
                    elif 'timeout' in error_msg or 'timed out' in error_msg:
                        self.stdout.write(self.style.ERROR(f'  [{migrated + failed}/{total}] {hw_file.id}: TIMEOUT - {e}'))
                        logger.error(f'migrate_homework_files: timeout migrating {hw_file.id}: {e}')
                    else:
                        self.stdout.write(self.style.ERROR(f'  [{migrated + failed}/{total}] {hw_file.id}: FAILED - {e}'))
                        logger.error(f'migrate_homework_files: failed to migrate {hw_file.id}: {e}', exc_info=True)
                
                # Per-file cooldown: помечаем файл как "отравленный" после N неудач
                if consecutive_failures > 0:
                    fail_count_key = f'migrate_hw_file_fails_{hw_file.id}'
                    fail_count = (cache.get(fail_count_key) or 0) + 1
                    cache.set(fail_count_key, fail_count, FILE_COOLDOWN_MAX * 2)
                    
                    if fail_count >= FILE_MAX_FAILURES:
                        # Экспоненциальный cooldown: 30 мин, 60 мин, 120 мин... до 24ч
                        cooldown = min(
                            FILE_COOLDOWN_BASE * (2 ** (fail_count - FILE_MAX_FAILURES)),
                            FILE_COOLDOWN_MAX
                        )
                        cooldown_key = f'migrate_hw_file_cooldown_{hw_file.id}'
                        cache.set(cooldown_key, True, int(cooldown))
                        self.stdout.write(
                            self.style.WARNING(
                                f'  File {hw_file.id} failed {fail_count} times, '
                                f'cooldown {int(cooldown/60)} min'
                            )
                        )
                        logger.warning(
                            f'migrate_homework_files: file {hw_file.id} put on cooldown '
                            f'({int(cooldown/60)} min) after {fail_count} failures'
                        )

                # Circuit breaker: если N файлов подряд упали, GDrive скорее всего недоступен
                if consecutive_failures >= CIRCUIT_BREAKER_THRESHOLD:
                    # Устанавливаем глобальный cooldown чтобы cron не спамил
                    cache.set(global_cooldown_key, True, GLOBAL_COOLDOWN)
                    msg = (
                        f'Circuit breaker triggered: {consecutive_failures} consecutive failures. '
                        f'Google Drive is likely unavailable. Stopping batch. '
                        f'Global cooldown {GLOBAL_COOLDOWN//60} min set. '
                        f'Migrated: {migrated}, Failed: {failed}'
                    )
                    self.stdout.write(self.style.ERROR(f'\n{msg}'))
                    logger.error(f'migrate_homework_files: {msg}')
                    break
                
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
