"""
Сервис для работы с домашними заданиями
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

from asgiref.sync import sync_to_async
from django.utils import timezone
from django.db.models import Count, Q, Case, When, IntegerField

logger = logging.getLogger(__name__)


class HomeworkService:
    """Сервис для работы с ДЗ в контексте бота"""
    
    @staticmethod
    async def get_teacher_homeworks(teacher_id: int, limit: int = 10) -> List:
        """Получает активные ДЗ учителя"""
        from homework.models import Homework
        
        def query():
            now = timezone.now()
            return list(
                Homework.objects.filter(
                    teacher_id=teacher_id,
                    status='published',
                ).select_related('lesson', 'lesson__group').prefetch_related(
                    'assigned_groups'
                ).order_by('-created_at')[:limit]
            )
        
        return await sync_to_async(query)()
    
    @staticmethod
    async def get_homework_stats(homework_id: int) -> Dict[str, int]:
        """
        Получает статистику сдачи ДЗ.
        Возвращает: total, submitted, graded, pending, overdue
        """
        from homework.models import Homework, StudentSubmission
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        def query():
            hw = Homework.objects.get(id=homework_id)
            now = timezone.now()
            
            # Собираем всех целевых учеников
            target_students = set()
            
            # Из урока
            if hw.lesson and hw.lesson.group:
                for s in hw.lesson.group.students.filter(is_active=True):
                    target_students.add(s.id)
            
            # Из assigned_groups
            for group in hw.assigned_groups.all():
                for s in group.students.filter(is_active=True):
                    target_students.add(s.id)
            
            # Из assigned_students
            for s in hw.assigned_students.filter(is_active=True):
                target_students.add(s.id)
            
            total = len(target_students)
            
            if total == 0:
                return {'total': 0, 'submitted': 0, 'graded': 0, 'pending': 0, 'overdue': 0}
            
            # Получаем сдачи
            submissions = StudentSubmission.objects.filter(
                homework_id=homework_id,
                student_id__in=target_students,
            ).values('student_id', 'status')
            
            submitted_students = set()
            graded_count = 0
            submitted_count = 0
            
            for sub in submissions:
                submitted_students.add(sub['student_id'])
                if sub['status'] == 'graded':
                    graded_count += 1
                elif sub['status'] == 'submitted':
                    submitted_count += 1
            
            pending_students = target_students - submitted_students
            pending_count = len(pending_students)
            
            # Считаем просроченных
            overdue_count = 0
            if hw.deadline and hw.deadline < now:
                overdue_count = pending_count
                pending_count = 0
            
            return {
                'total': total,
                'submitted': submitted_count,
                'graded': graded_count,
                'pending': pending_count,
                'overdue': overdue_count,
            }
        
        return await sync_to_async(query)()
    
    @staticmethod
    async def get_not_submitted_students(homework_id: int) -> List[Tuple[int, str, Optional[str]]]:
        """
        Получает список учеников, не сдавших ДЗ.
        Возвращает: [(student_id, name, telegram_id), ...]
        """
        from homework.models import Homework, StudentSubmission
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        def query():
            hw = Homework.objects.get(id=homework_id)
            
            # Собираем всех целевых учеников
            target_students = set()
            
            if hw.lesson and hw.lesson.group:
                for s in hw.lesson.group.students.filter(is_active=True):
                    target_students.add(s.id)
            
            for group in hw.assigned_groups.all():
                for s in group.students.filter(is_active=True):
                    target_students.add(s.id)
            
            for s in hw.assigned_students.filter(is_active=True):
                target_students.add(s.id)
            
            # Получаем сдавших
            submitted_ids = set(
                StudentSubmission.objects.filter(
                    homework_id=homework_id,
                    student_id__in=target_students,
                ).values_list('student_id', flat=True)
            )
            
            # Не сдавшие
            not_submitted_ids = target_students - submitted_ids
            
            # Получаем данные учеников
            students = User.objects.filter(
                id__in=not_submitted_ids,
                is_active=True,
            ).values('id', 'first_name', 'last_name', 'email', 'telegram_id')
            
            result = []
            for s in students:
                name = f"{s['first_name'] or ''} {s['last_name'] or ''}".strip() or s['email']
                result.append((s['id'], name, s['telegram_id']))
            
            return result
        
        return await sync_to_async(query)()
    
    @staticmethod
    async def get_student_homeworks(student_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Получает ДЗ для ученика с их статусами.
        """
        from homework.models import Homework, StudentSubmission
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        def query():
            now = timezone.now()
            student = User.objects.get(id=student_id)
            
            # Получаем группы ученика
            group_ids = list(student.enrolled_groups.values_list('id', flat=True))
            
            # Находим ДЗ доступные ученику
            homeworks = Homework.objects.filter(
                status='published',
            ).filter(
                Q(lesson__group_id__in=group_ids) |
                Q(assigned_groups__id__in=group_ids) |
                Q(assigned_students=student)
            ).distinct().select_related('lesson', 'lesson__group').order_by('-created_at')[:limit]
            
            # Получаем сдачи
            hw_ids = [hw.id for hw in homeworks]
            submissions = {
                sub.homework_id: sub
                for sub in StudentSubmission.objects.filter(
                    homework_id__in=hw_ids,
                    student=student,
                )
            }
            
            result = []
            for hw in homeworks:
                sub = submissions.get(hw.id)
                
                status = 'not_submitted'
                score = None
                
                if sub:
                    status = sub.status
                    score = sub.total_score
                elif hw.deadline and hw.deadline < now:
                    status = 'overdue'
                
                result.append({
                    'homework': hw,
                    'status': status,
                    'score': score,
                    'deadline': hw.deadline,
                    'is_overdue': hw.deadline and hw.deadline < now and not sub,
                })
            
            return result
        
        return await sync_to_async(query)()
    
    @staticmethod
    async def get_upcoming_deadlines(student_id: int, days: int = 7) -> List[Dict[str, Any]]:
        """
        Получает ДЗ с приближающимися дедлайнами.
        """
        from homework.models import Homework, StudentSubmission
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        def query():
            now = timezone.now()
            deadline_limit = now + timedelta(days=days)
            student = User.objects.get(id=student_id)
            
            group_ids = list(student.enrolled_groups.values_list('id', flat=True))
            
            # ДЗ с дедлайном в ближайшие N дней
            homeworks = Homework.objects.filter(
                status='published',
                deadline__gte=now,
                deadline__lte=deadline_limit,
            ).filter(
                Q(lesson__group_id__in=group_ids) |
                Q(assigned_groups__id__in=group_ids) |
                Q(assigned_students=student)
            ).distinct().select_related('lesson', 'lesson__group').order_by('deadline')
            
            # Исключаем уже сданные
            submitted_hw_ids = set(
                StudentSubmission.objects.filter(
                    student=student,
                    homework_id__in=[hw.id for hw in homeworks],
                ).values_list('homework_id', flat=True)
            )
            
            result = []
            for hw in homeworks:
                if hw.id not in submitted_hw_ids:
                    result.append({
                        'homework': hw,
                        'deadline': hw.deadline,
                        'time_remaining': hw.deadline - now if hw.deadline else None,
                    })
            
            return result
        
        return await sync_to_async(query)()
