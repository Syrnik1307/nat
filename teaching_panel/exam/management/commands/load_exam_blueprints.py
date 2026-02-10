"""
Management command для загрузки предустановленных шаблонов экзаменов.

Использование:
    python manage.py load_exam_blueprints
    python manage.py load_exam_blueprints --exam ege_informatics_2026
    python manage.py load_exam_blueprints --list
"""

from django.core.management.base import BaseCommand
from exam.models import ExamBlueprint, ExamTaskSlot
from exam.scoring import (
    EXAM_STRUCTURES, SCORE_SCALES, GRADE_THRESHOLDS,
    list_available_exams,
)
from knowledge_map.models import ExamType, Subject


class Command(BaseCommand):
    help = 'Загрузить предустановленные шаблоны экзаменов ЕГЭ/ОГЭ'

    def add_arguments(self, parser):
        parser.add_argument(
            '--exam',
            type=str,
            help='Ключ конкретного экзамена (например: ege_informatics_2026)',
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='Показать доступные шаблоны',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Пересоздать существующие шаблоны',
        )

    def handle(self, *args, **options):
        if options['list']:
            self.stdout.write('Доступные шаблоны экзаменов:')
            for key in list_available_exams():
                struct = EXAM_STRUCTURES[key]
                self.stdout.write(f'  {key}: {struct["title"]} ({len(struct["tasks"])} заданий)')
            return

        exams_to_load = [options['exam']] if options['exam'] else list_available_exams()
        
        for exam_key in exams_to_load:
            if exam_key not in EXAM_STRUCTURES:
                self.stderr.write(f'Неизвестный экзамен: {exam_key}')
                continue
            
            self._load_blueprint(exam_key, force=options['force'])

    def _load_blueprint(self, exam_key: str, force: bool = False):
        struct = EXAM_STRUCTURES[exam_key]
        
        # Находим или создаём Subject
        exam_type_code = struct['exam_type']
        subject_code = struct['subject_code']
        
        exam_type, _ = ExamType.objects.get_or_create(
            code=exam_type_code,
            defaults={'name': 'ЕГЭ' if exam_type_code == 'ege' else 'ОГЭ'}
        )
        
        subject, _ = Subject.objects.get_or_create(
            exam_type=exam_type,
            code=subject_code,
            defaults={
                'name': struct['title'].replace(f'{"ЕГЭ" if exam_type_code == "ege" else "ОГЭ"} ', '').split(' 20')[0],
                'max_primary_score': struct['total_primary_score'],
                'total_tasks': len(struct['tasks']),
            }
        )
        
        # Проверяем существующий
        existing = ExamBlueprint.objects.filter(
            subject=subject,
            year=2026,
            title=struct['title'],
        ).first()
        
        if existing and not force:
            self.stdout.write(f'  [SKIP] {struct["title"]} (уже существует, id={existing.id})')
            return
        
        if existing and force:
            existing.delete()
            self.stdout.write(f'  [DELETE] Удалён старый шаблон {struct["title"]}')
        
        # Шкала
        scale_key = exam_key
        grade_key = f'{exam_type_code}_{subject_code}'
        
        blueprint = ExamBlueprint.objects.create(
            subject=subject,
            title=struct['title'],
            year=2026,
            duration_minutes=struct['duration_minutes'],
            total_primary_score=struct['total_primary_score'],
            score_scale=SCORE_SCALES.get(scale_key, {}),
            grade_thresholds=GRADE_THRESHOLDS.get(grade_key, {}),
            description=f'Шаблон {struct["title"]}. Автоматически загружен из предустановок.',
            is_active=True,
            is_public=True,  # Доступен всем учителям
        )
        
        # Создаём слоты
        for task in struct['tasks']:
            ExamTaskSlot.objects.create(
                blueprint=blueprint,
                task_number=task['task_number'],
                title=task['title'],
                answer_type=task['answer_type'],
                max_points=task['max_points'],
                order=task['task_number'],
            )
        
        self.stdout.write(self.style.SUCCESS(
            f'  [OK] {struct["title"]}: {len(struct["tasks"])} слотов, '
            f'макс {struct["total_primary_score"]} баллов'
        ))
