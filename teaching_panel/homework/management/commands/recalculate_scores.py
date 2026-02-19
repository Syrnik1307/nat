"""
Management-команда для пересчёта total_score у всех StudentSubmission.

Восстанавливает оценки, которые были потеряны из-за бага с отсутствующим
методом recalculate_total() (AttributeError в ai_callback_views).

Использование:
  # Dry-run — показать, что будет исправлено (без реальных изменений):
  python manage.py recalculate_scores --dry-run

  # Пересчитать все submission, где total_score IS NULL:
  python manage.py recalculate_scores

  # Пересчитать ВСЕ submission (включая те, где total_score уже задан):
  python manage.py recalculate_scores --all

  # Пересчитать только для конкретного ДЗ:
  python manage.py recalculate_scores --homework-id=42
"""

from django.core.management.base import BaseCommand
from django.db.models import Q, Sum, Case, When, F, IntegerField, Value
from django.db.models.functions import Coalesce

from homework.models import StudentSubmission, Answer


class Command(BaseCommand):
    help = 'Пересчитать total_score для StudentSubmission из auto_score/teacher_score ответов'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Не сохранять изменения, только показать что будет исправлено',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Пересчитать ВСЕ submission (не только те, где total_score=NULL)',
        )
        parser.add_argument(
            '--homework-id',
            type=int,
            default=None,
            help='Пересчитать только для конкретного homework_id',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        recalc_all = options['all']
        homework_id = options['homework_id']

        qs = StudentSubmission.objects.all()

        if homework_id:
            qs = qs.filter(homework_id=homework_id)

        if not recalc_all:
            # По умолчанию — только submission с потерянными оценками
            # (total_score IS NULL или = 0, но есть ненулевые ответы)
            qs = qs.filter(
                Q(total_score__isnull=True) | Q(total_score=0)
            )

        # Предзагрузим ответы
        qs = qs.prefetch_related('answers', 'answers__question')

        total_count = qs.count()
        if total_count == 0:
            self.stdout.write(self.style.SUCCESS(
                'Нет submission для пересчёта. Все оценки в порядке!'
            ))
            return

        self.stdout.write(f'Найдено {total_count} submission для пересчёта...\n')

        fixed_count = 0
        skipped_count = 0
        errors = []

        for submission in qs.iterator():
            try:
                old_score = submission.total_score

                # Вычисляем правильный total_score из ответов
                new_score = 0
                has_any_score = False
                for answer in submission.answers.all():
                    if answer.teacher_score is not None:
                        new_score += answer.teacher_score
                        has_any_score = True
                    elif answer.auto_score is not None:
                        new_score += answer.auto_score
                        has_any_score = True

                # Если нет ни одной оценки — пропускаем
                if not has_any_score:
                    skipped_count += 1
                    if dry_run:
                        self.stdout.write(
                            f'  [SKIP] Submission #{submission.id} '
                            f'({submission.student.email} → {submission.homework.title}): '
                            f'нет оценок в ответах'
                        )
                    continue

                # Если оценка не изменилась — пропускаем
                if old_score == new_score and not recalc_all:
                    skipped_count += 1
                    continue

                if dry_run:
                    self.stdout.write(
                        f'  [FIX] Submission #{submission.id} '
                        f'({submission.student.email} → {submission.homework.title}): '
                        f'{old_score} → {new_score}'
                    )
                else:
                    submission.total_score = new_score
                    submission.save(update_fields=['total_score'])

                fixed_count += 1

            except Exception as exc:
                errors.append(f'Submission #{submission.id}: {exc}')
                self.stderr.write(self.style.ERROR(
                    f'  [ERROR] Submission #{submission.id}: {exc}'
                ))

        # Итоги
        self.stdout.write('\n' + '=' * 60)
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — изменения НЕ сохранены'))
        self.stdout.write(f'Всего обработано: {total_count}')
        self.stdout.write(self.style.SUCCESS(f'Исправлено: {fixed_count}'))
        self.stdout.write(f'Пропущено (нет данных или без изменений): {skipped_count}')
        if errors:
            self.stdout.write(self.style.ERROR(f'Ошибок: {len(errors)}'))
            for e in errors:
                self.stdout.write(self.style.ERROR(f'  - {e}'))

        if not dry_run and fixed_count > 0:
            self.stdout.write(self.style.SUCCESS(
                f'\n✅ Успешно восстановлено {fixed_count} оценок!'
            ))
