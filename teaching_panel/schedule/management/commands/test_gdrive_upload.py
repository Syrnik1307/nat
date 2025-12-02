from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from schedule.gdrive_utils import get_gdrive_manager
from accounts.models import CustomUser
import tempfile
import os


class Command(BaseCommand):
    help = "Test Google Drive upload with optional teacher and folder overrides"

    def add_arguments(self, parser):
        parser.add_argument("--teacher-id", type=int, default=None)
        parser.add_argument("--folder-id", type=str, default=None)
        parser.add_argument("--file", type=str, default=None)
        parser.add_argument("--name", type=str, default=None)

    def handle(self, *args, **options):
        teacher = None
        if options["teacher_id"] is not None:
            try:
                teacher = CustomUser.objects.get(id=options["teacher_id"])
            except CustomUser.DoesNotExist:
                raise CommandError(f"Teacher with id={options['teacher_id']} not found")
        else:
            teacher = CustomUser.objects.filter(role="teacher").first()

        folder_id = options["folder_id"] or getattr(settings, "GDRIVE_RECORDINGS_FOLDER_ID", "") or None

        file_path = options["file"]
        file_name = options["name"]

        tmp_created = False
        if not file_path:
            fd, tmp_path = tempfile.mkstemp(suffix=".txt")
            os.write(fd, b"Teaching Panel GDrive upload test\n")
            os.close(fd)
            file_path = tmp_path
            tmp_created = True
            if not file_name:
                file_name = os.path.basename(file_path)

        if not file_name:
            file_name = os.path.basename(file_path)

        try:
            mgr = get_gdrive_manager()
            result = mgr.upload_file(file_path, file_name, folder_id=folder_id, teacher=teacher, mime_type="text/plain")
            self.stdout.write(self.style.SUCCESS("Upload succeeded"))
            self.stdout.write(str(result))
        finally:
            if tmp_created:
                try:
                    os.remove(file_path)
                except OSError:
                    pass
