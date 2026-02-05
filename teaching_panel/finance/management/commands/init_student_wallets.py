"""
Management command to initialize financial profiles for existing students.

Creates StudentFinancialProfile for each unique (student, teacher) pair
found in existing groups.

Usage:
    python manage.py init_student_wallets --dry-run  # Preview changes
    python manage.py init_student_wallets            # Create wallets
"""
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import CustomUser
from schedule.models import Group
from finance.models import StudentFinancialProfile


class Command(BaseCommand):
    help = 'Создать финансовые профили для всех существующих пар ученик-учитель'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Только показать что будет создано, без изменений в БД'
        )
        parser.add_argument(
            '--teacher-id',
            type=int,
            help='Создать только для конкретного учителя (по ID)'
        )
    
    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        teacher_id = options.get('teacher_id')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('=== DRY RUN MODE ===\n'))
        
        # Собираем уникальные пары (student_id, teacher_id) из групп
        pairs = set()
        
        groups_qs = Group.objects.prefetch_related('students').select_related('teacher')
        if teacher_id:
            groups_qs = groups_qs.filter(teacher_id=teacher_id)
        
        for group in groups_qs:
            teacher = group.teacher
            for student in group.students.all():
                pairs.add((student.id, teacher.id))
        
        self.stdout.write(f'Найдено {len(pairs)} уникальных пар ученик-учитель\n')
        
        created = 0
        skipped = 0
        
        for student_id, teacher_id in sorted(pairs):
            # Проверяем, существует ли уже кошелёк
            exists = StudentFinancialProfile.objects.filter(
                student_id=student_id,
                teacher_id=teacher_id
            ).exists()
            
            if exists:
                skipped += 1
                continue
            
            # Получаем объекты для отображения
            try:
                student = CustomUser.objects.get(id=student_id)
                teacher = CustomUser.objects.get(id=teacher_id)
            except CustomUser.DoesNotExist:
                self.stdout.write(self.style.ERROR(
                    f'  Пользователь не найден: student_id={student_id} или teacher_id={teacher_id}'
                ))
                continue
            
            if dry_run:
                self.stdout.write(
                    f'  [DRY] Создать: {student.email} <-> {teacher.email}'
                )
            else:
                StudentFinancialProfile.objects.create(
                    student_id=student_id,
                    teacher_id=teacher_id,
                    balance=Decimal('0.00'),
                    default_lesson_price=Decimal('0.00')  # Учитель установит сам
                )
                self.stdout.write(
                    f'  Создан: {student.email} <-> {teacher.email}'
                )
            
            created += 1
        
        # Итог
        self.stdout.write('')
        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'=== DRY RUN: Будет создано {created}, пропущено (уже есть) {skipped} ==='
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'Создано: {created}, пропущено (уже есть): {skipped}'
            ))
