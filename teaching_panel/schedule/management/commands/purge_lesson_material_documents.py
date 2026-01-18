from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Удаляет legacy материалы LessonMaterial типов document/link/image. "
        "Актуальные разделы: только miro и notes."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Показать сколько записей будет удалено, без удаления",
        )

    def handle(self, *args, **options):
        from schedule.models import LessonMaterial

        legacy_types = [
            LessonMaterial.MaterialType.DOCUMENT,
            LessonMaterial.MaterialType.LINK,
            LessonMaterial.MaterialType.IMAGE,
        ]

        qs = LessonMaterial.objects.filter(material_type__in=legacy_types)
        count = qs.count()

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING(f"DRY RUN: would delete {count} legacy materials"))
            return

        deleted_count, deleted_map = qs.delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted_count} objects"))
        self.stdout.write(str(deleted_map))
