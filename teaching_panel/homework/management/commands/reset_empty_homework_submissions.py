from django.core.management.base import BaseCommand
from django.db.models import Count

from homework.models import StudentSubmission


class Command(BaseCommand):
    help = (
        "Сбрасывает ошибочно созданные сабмишены, которые помечены как submitted, "
        "но при этом не содержат ни одного ответа. "
        "По умолчанию работает в режиме dry-run."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Применить изменения (без этого флага команда ничего не изменяет).',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Ограничить количество обрабатываемых записей (0 = без лимита).',
        )

    def handle(self, *args, **options):
        apply_changes = bool(options['apply'])
        limit = int(options['limit'] or 0)

        qs = (
            StudentSubmission.objects
            .filter(status='submitted')
            .annotate(answer_count=Count('answers'))
            .filter(answer_count=0)
            .order_by('id')
        )

        total = qs.count()
        if limit > 0:
            qs = qs[:limit]

        self.stdout.write(
            self.style.WARNING(
                f"Найдено submitted-сабмишенов без ответов: {total}" + (f" (лимит {limit})" if limit else '')
            )
        )

        if not total:
            self.stdout.write(self.style.SUCCESS('Нечего исправлять.'))
            return

        if not apply_changes:
            self.stdout.write(
                self.style.NOTICE(
                    'DRY-RUN: ничего не изменено. Запустите с --apply чтобы сбросить статусы.'
                )
            )
            sample = list(qs[:20])
            for sub in sample:
                self.stdout.write(
                    f"- submission_id={sub.id} homework_id={sub.homework_id} student_id={sub.student_id} "
                    f"submitted_at={sub.submitted_at!s} created_at={sub.created_at!s}"
                )
            if total > 20:
                self.stdout.write(f"... и ещё {total - 20}")
            return

        updated = 0
        for sub in qs:
            sub.status = 'in_progress'
            sub.submitted_at = None
            sub.save(update_fields=['status', 'submitted_at'])
            updated += 1

        self.stdout.write(self.style.SUCCESS(f'Сброшено сабмишенов: {updated}'))
