"""
Management command для очистки локальных файлов домашек,
которые уже мигрированы на GDrive или застряли.

Usage:
    python manage.py cleanup_local_homework_files --dry-run  # Показать что будет удалено
    python manage.py cleanup_local_homework_files            # Реально удалить
"""

import os
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from homework.models import HomeworkFile

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Очистить локальные файлы домашек, которые уже мигрированы на GDrive'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Только показать что будет удалено, не удалять реально',
        )
        parser.add_argument(
            '--force-migrate',
            action='store_true',
            help='Попробовать мигрировать файлы, которые остались локальными',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force_migrate = options['force_migrate']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('=== DRY RUN MODE ==='))
        
        # 1. Найти файлы которые уже на GDrive, но local_path не очищен
        gdrive_with_local = HomeworkFile.objects.filter(
            storage=HomeworkFile.STORAGE_GDRIVE
        ).exclude(local_path='')
        
        self.stdout.write(f"\n1. Файлы на GDrive с неочищенным local_path: {gdrive_with_local.count()}")
        
        for hw_file in gdrive_with_local:
            if hw_file.local_path and os.path.exists(hw_file.local_path):
                self.stdout.write(f"   - {hw_file.id}: {hw_file.local_path} (EXISTS)")
                if not dry_run:
                    hw_file.delete_local_file()
            else:
                self.stdout.write(f"   - {hw_file.id}: {hw_file.local_path} (already gone)")
                if not dry_run:
                    hw_file.local_path = ''
                    hw_file.save(update_fields=['local_path'])
        
        # 2. Найти файлы которые остались локальными
        local_files = HomeworkFile.objects.filter(
            storage=HomeworkFile.STORAGE_LOCAL
        )
        
        self.stdout.write(f"\n2. Файлы, оставшиеся локальными: {local_files.count()}")
        
        for hw_file in local_files:
            exists = hw_file.local_path and os.path.exists(hw_file.local_path)
            status = "EXISTS" if exists else "MISSING"
            self.stdout.write(f"   - {hw_file.id}: {hw_file.original_name} ({status})")
            
            if force_migrate and exists and not dry_run:
                self.stdout.write(f"     -> Attempting migration...")
                try:
                    from homework.views import _migrate_file_to_gdrive
                    _migrate_file_to_gdrive(hw_file.id)
                    self.stdout.write(self.style.SUCCESS(f"     -> Migrated!"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"     -> Failed: {e}"))
        
        # 3. Проверить orphaned файлы в папке (файлы без записи в БД)
        homework_media_dir = os.path.join(settings.MEDIA_ROOT, 'homework_files')
        
        if os.path.exists(homework_media_dir):
            all_files = set(os.listdir(homework_media_dir))
            known_files = set()
            
            for hw_file in HomeworkFile.objects.exclude(local_path=''):
                if hw_file.local_path:
                    known_files.add(os.path.basename(hw_file.local_path))
            
            orphaned = all_files - known_files
            
            self.stdout.write(f"\n3. Orphaned файлы (нет записи в БД): {len(orphaned)}")
            
            total_size = 0
            for filename in orphaned:
                filepath = os.path.join(homework_media_dir, filename)
                size = os.path.getsize(filepath)
                total_size += size
                self.stdout.write(f"   - {filename} ({size // 1024} KB)")
                
                if not dry_run:
                    try:
                        os.remove(filepath)
                        self.stdout.write(self.style.SUCCESS(f"     -> Deleted"))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"     -> Failed: {e}"))
            
            if orphaned:
                self.stdout.write(f"\n   Total orphaned size: {total_size // 1024} KB")
        
        self.stdout.write(self.style.SUCCESS('\n=== Done ==='))
