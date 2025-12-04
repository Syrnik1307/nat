"""
Management command для миграции файлов на Google Drive
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from schedule.gdrive_storage import GoogleDriveStorage
import os
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Migrate local files to Google Drive storage'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without actually migrating',
        )
        parser.add_argument(
            '--type',
            type=str,
            choices=['homework', 'materials', 'attachments', 'all'],
            default='all',
            help='Type of files to migrate',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        file_type = options['type']
        
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Google Drive Migration Tool'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No files will be migrated'))
        
        # Проверка настроек
        if not getattr(settings, 'USE_GDRIVE_STORAGE', False):
            self.stdout.write(self.style.ERROR('USE_GDRIVE_STORAGE not enabled in settings!'))
            self.stdout.write('Set USE_GDRIVE_STORAGE=1 in .env file')
            return
        
        # Миграция по типам
        if file_type == 'all':
            types_to_migrate = ['homework', 'materials', 'attachments']
        else:
            types_to_migrate = [file_type]
        
        total_migrated = 0
        total_size = 0
        
        for ftype in types_to_migrate:
            migrated, size = self.migrate_type(ftype, dry_run)
            total_migrated += migrated
            total_size += size
        
        # Итоги
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS(f'Total files: {total_migrated}'))
        self.stdout.write(self.style.SUCCESS(f'Total size: {self.format_size(total_size)}'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nThis was a DRY RUN. Run without --dry-run to execute.'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ Migration completed!'))
    
    def migrate_type(self, file_type, dry_run):
        """Миграция файлов определённого типа"""
        
        self.stdout.write(self.style.SUCCESS(f'\n--- Migrating {file_type.upper()} files ---'))
        
        # Пути для разных типов
        paths = {
            'homework': 'media/homework_submissions',
            'materials': 'media/lesson_materials',
            'attachments': 'media/attachments',
        }
        
        media_path = os.path.join(settings.BASE_DIR, paths.get(file_type, ''))
        
        if not os.path.exists(media_path):
            self.stdout.write(self.style.WARNING(f'Path not found: {media_path}'))
            return 0, 0
        
        # Инициализация storage
        try:
            storage = GoogleDriveStorage(folder_type=file_type)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to initialize Google Drive: {e}'))
            return 0, 0
        
        # Сканирование файлов
        files_to_migrate = []
        total_size = 0
        
        for root, dirs, files in os.walk(media_path):
            for filename in files:
                filepath = os.path.join(root, filename)
                filesize = os.path.getsize(filepath)
                files_to_migrate.append((filepath, filename, filesize))
                total_size += filesize
        
        if not files_to_migrate:
            self.stdout.write(self.style.WARNING('No files found'))
            return 0, 0
        
        self.stdout.write(f'Found {len(files_to_migrate)} files ({self.format_size(total_size)})')
        
        if dry_run:
            for filepath, filename, filesize in files_to_migrate[:5]:  # Показываем первые 5
                self.stdout.write(f'  - {filename} ({self.format_size(filesize)})')
            if len(files_to_migrate) > 5:
                self.stdout.write(f'  ... and {len(files_to_migrate) - 5} more')
            return len(files_to_migrate), total_size
        
        # Миграция файлов
        migrated = 0
        for filepath, filename, filesize in files_to_migrate:
            try:
                with open(filepath, 'rb') as f:
                    from django.core.files.base import File
                    django_file = File(f, name=filename)
                    file_id = storage._save(filename, django_file)
                    
                    self.stdout.write(self.style.SUCCESS(f'✓ {filename} → {file_id}'))
                    migrated += 1
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ {filename}: {e}'))
        
        return migrated, total_size
    
    def format_size(self, bytes):
        """Форматирование размера файла"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes < 1024.0:
                return f"{bytes:.2f} {unit}"
            bytes /= 1024.0
        return f"{bytes:.2f} TB"
