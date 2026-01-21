"""
Сервис управления посещениями и рейтингом учеников.
Обрабатывает логику автоматического заполнения и пересчета очков.
"""

from django.utils import timezone
from django.db.models import Q, Sum, Count
from decimal import Decimal
import logging

from .models import AttendanceRecord, UserRating, IndividualStudent
from schedule.models import Lesson, Group

logger = logging.getLogger(__name__)

# Константы для системы очков
ATTENDANCE_POINTS = 10  # За присутствие на уроке
WATCHED_RECORDING_POINTS = 10  # За просмотр записи (если не был)

# Домашние задания
HOMEWORK_LATE_PENALTY = 10  # Штраф за сдачу после дедлайна (вычитается из балла ДЗ)


class AttendanceService:
    """Сервис управления посещениями учеников"""
    
    @staticmethod
    def auto_record_attendance(lesson_id, student_id, is_joined=True):
        """
        Автоматически записать посещение при подключении к Zoom.
        
        Args:
            lesson_id (int): ID занятия
            student_id (int): ID ученика
            is_joined (bool): Подключился ли ученик (True=был, False=не было)
        
        Returns:
            AttendanceRecord: Созданная/обновленная запись
        """
        try:
            lesson = Lesson.objects.get(id=lesson_id)
            
            status = AttendanceRecord.STATUS_ATTENDED if is_joined else None
            
            record, created = AttendanceRecord.objects.update_or_create(
                lesson=lesson,
                student_id=student_id,
                defaults={
                    'status': status,
                    'auto_recorded': True,
                    'recorded_by': None
                }
            )
            
            # Пересчитать рейтинг
            RatingService.recalculate_student_rating(
                student_id=student_id,
                group_id=lesson.group_id
            )
            
            logger.info(
                f"Auto-recorded attendance: Student {student_id} - Lesson {lesson_id} - Status: {status}"
            )
            
            return record
            
        except Lesson.DoesNotExist:
            logger.error(f"Lesson {lesson_id} not found")
            raise
    
    @staticmethod
    def manual_record_attendance(lesson_id, student_id, status, teacher_id):
        """
        Ручное заполнение посещения учителем.
        
        Args:
            lesson_id (int): ID занятия
            student_id (int): ID ученика
            status (str): Статус ('attended', 'absent', 'watched_recording')
            teacher_id (int): ID учителя (заполнивший запись)
        
        Returns:
            AttendanceRecord: Созданная/обновленная запись
        """
        if status not in [AttendanceRecord.STATUS_ATTENDED, 
                         AttendanceRecord.STATUS_ABSENT,
                         AttendanceRecord.STATUS_WATCHED_RECORDING]:
            raise ValueError(f"Invalid status: {status}")
        
        try:
            lesson = Lesson.objects.get(id=lesson_id)
            
            record, created = AttendanceRecord.objects.update_or_create(
                lesson=lesson,
                student_id=student_id,
                defaults={
                    'status': status,
                    'auto_recorded': False,
                    'recorded_by_id': teacher_id
                }
            )
            
            # Пересчитать рейтинг
            RatingService.recalculate_student_rating(
                student_id=student_id,
                group_id=lesson.group_id
            )
            
            logger.info(
                f"Manual attendance record: Student {student_id} - "
                f"Lesson {lesson_id} - Status: {status} - Teacher: {teacher_id}"
            )
            
            return record
            
        except Lesson.DoesNotExist:
            logger.error(f"Lesson {lesson_id} not found")
            raise
    
    @staticmethod
    def record_watched_recording(lesson_id, student_id):
        """
        Записать просмотр записи занятия.
        Если уже был отмечен как присутствовал, не менять статус.
        
        Args:
            lesson_id (int): ID занятия
            student_id (int): ID ученика
        
        Returns:
            AttendanceRecord: Созданная/обновленная запись
        """
        try:
            lesson = Lesson.objects.get(id=lesson_id)
            
            # Если уже был отмечен как "присутствовал", не менять
            record = AttendanceRecord.objects.filter(
                lesson=lesson,
                student_id=student_id
            ).first()
            
            if record and record.status == AttendanceRecord.STATUS_ATTENDED:
                # Уже был, не меняем
                return record
            
            # Иначе, отмечаем просмотр
            record, created = AttendanceRecord.objects.update_or_create(
                lesson=lesson,
                student_id=student_id,
                defaults={
                    'status': AttendanceRecord.STATUS_WATCHED_RECORDING,
                    'auto_recorded': True,
                    'recorded_by': None
                }
            )
            
            # Пересчитать рейтинг
            RatingService.recalculate_student_rating(
                student_id=student_id,
                group_id=lesson.group_id
            )
            
            logger.info(
                f"Recorded watched recording: Student {student_id} - Lesson {lesson_id}"
            )
            
            return record
            
        except Lesson.DoesNotExist:
            logger.error(f"Lesson {lesson_id} not found")
            raise
    
    @staticmethod
    def auto_mark_absent_for_missed_lessons():
        """
        Celery task: Автоматически отметить как "не был" для уроков,
        которые закончились более 24 часов назад и не имеют записи посещения.
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Найти уроки, закончившиеся более 24 часов назад
        cutoff_time = timezone.now() - timezone.timedelta(hours=24)
        missed_lessons = Lesson.objects.filter(
            end_time__lt=cutoff_time
        )
        
        count = 0
        for lesson in missed_lessons:
            # Найти учеников группы, у которых нет записи посещения
            students_without_record = lesson.group.students.filter(
                ~Q(attendance_records__lesson=lesson)
            )
            
            for student in students_without_record:
                AttendanceService.manual_record_attendance(
                    lesson_id=lesson.id,
                    student_id=student.id,
                    status=AttendanceRecord.STATUS_ABSENT,
                    teacher_id=lesson.teacher_id
                )
                count += 1
        
        logger.info(f"Auto-marked {count} students as absent for missed lessons")
        return count


class RatingService:
    """Сервис управления рейтингом и очками учеников"""
    
    @staticmethod
    def recalculate_student_rating(student_id, group_id=None):
        """
        Пересчитать рейтинг ученика.
        
        Args:
            student_id (int): ID ученика
            group_id (int, optional): ID группы (если None, пересчитываем для всех групп)
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            student = User.objects.get(id=student_id, role='student')
        except User.DoesNotExist:
            logger.error(f"Student {student_id} not found")
            return
        
        if group_id:
            # Пересчитываем для конкретной группы
            groups = Group.objects.filter(id=group_id)
        else:
            # Пересчитываем для всех групп, в которых участвует ученик
            groups = student.enrolled_groups.all()
        
        for group in groups:
            # Рассчитываем очки за посещение
            attendance_points = RatingService._calculate_attendance_points(
                student_id=student_id,
                group_id=group.id
            )
            
            # Рассчитываем очки за ДЗ
            homework_points = RatingService._calculate_homework_points(
                student_id=student_id,
                group_id=group.id
            )
            
            # Рассчитываем очки за контрольные точки
            control_points = RatingService._calculate_control_points(
                student_id=student_id,
                group_id=group.id
            )
            
            # Обновляем или создаем запись рейтинга
            rating, created = UserRating.objects.update_or_create(
                user_id=student_id,
                group_id=group.id,
                defaults={
                    'attendance_points': attendance_points,
                    'homework_points': homework_points,
                    'control_points_value': control_points,
                    'total_points': attendance_points + homework_points + control_points
                }
            )
            
            # Пересчитать rank в группе
            RatingService._recalculate_group_ranking(group_id=group.id)
            
            logger.info(
                f"Recalculated rating for student {student_id} in group {group.id}: "
                f"Total={rating.total_points} (A={attendance_points}, "
                f"H={homework_points}, C={control_points})"
            )
    
    @staticmethod
    def _calculate_attendance_points(student_id, group_id):
        """Рассчитать очки за посещение"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Получить все занятия группы
        group_lessons = Lesson.objects.filter(group_id=group_id)
        
        # Подсчитать посещения и просмотры
        records = AttendanceRecord.objects.filter(
            student_id=student_id,
            lesson__in=group_lessons
        )
        
        attended_count = records.filter(
            status=AttendanceRecord.STATUS_ATTENDED
        ).count()
        watched_count = records.filter(
            status=AttendanceRecord.STATUS_WATCHED_RECORDING
        ).count()
        
        # Расчет: +10 за каждое присутствие, +10 за просмотр записи (если не был)
        points = (attended_count * ATTENDANCE_POINTS) + (watched_count * WATCHED_RECORDING_POINTS)
        
        return points
    
    @staticmethod
    def _calculate_homework_points(student_id, group_id):
        """
        Рассчитать очки за домашние задания.

        Логика:
        - Берём все ДЗ, относящиеся к группе (по lesson.group, assigned_groups и group_assignments)
        - Суммируем total_score по сабмитам (submitted/graded)
        - Если submitted_at > deadline (с учётом пер-групповых дедлайнов) — штраф -HOMEWORK_LATE_PENALTY
        """
        from homework.models import Homework, HomeworkGroupAssignment, StudentSubmission
        from django.db.models import Q

        homework_ids = list(
            Homework.objects.filter(
                Q(lesson__group_id=group_id)
                | Q(assigned_groups__id=group_id)
                | Q(group_assignments__group_id=group_id)
            )
            .distinct()
            .values_list('id', flat=True)
        )

        if not homework_ids:
            return 0

        # Дедлайны: сначала пер-групповой, затем общий
        deadlines_by_homework_id = {}
        for row in HomeworkGroupAssignment.objects.filter(
            group_id=group_id,
            homework_id__in=homework_ids,
        ).values('homework_id', 'deadline'):
            if row['deadline'] is not None:
                deadlines_by_homework_id[row['homework_id']] = row['deadline']

        for row in Homework.objects.filter(id__in=homework_ids).values('id', 'deadline'):
            deadlines_by_homework_id.setdefault(row['id'], row['deadline'])

        submissions = list(
            StudentSubmission.objects.filter(
                student_id=student_id,
                homework_id__in=homework_ids,
                status__in=['submitted', 'graded'],
            ).values('homework_id', 'total_score', 'submitted_at')
        )

        points = 0

        for sub in submissions:
            score = int(sub['total_score'] or 0)

            # Если сдано после дедлайна — вычитаем штраф из балла за эту работу
            deadline = deadlines_by_homework_id.get(sub['homework_id'])
            submitted_at = sub['submitted_at']
            if deadline and submitted_at and submitted_at > deadline:
                score = max(0, score - HOMEWORK_LATE_PENALTY)

            points += score

        return points
    
    @staticmethod
    def _calculate_control_points(student_id, group_id):
        """
        Рассчитать очки за контрольные точки.
        Подсчитываем пройденные контрольные точки.
        """
        from analytics.models import ControlPointResult

        total = ControlPointResult.objects.filter(
            student_id=student_id,
            control_point__group_id=group_id,
        ).aggregate(total=Sum('points'))['total']

        return int(total or 0)
    
    @staticmethod
    def _recalculate_group_ranking(group_id):
        """
        Пересчитать rank (место) для всех учеников в группе.
        """
        ratings = UserRating.objects.filter(
            group_id=group_id
        ).order_by('-total_points')
        
        for rank, rating in enumerate(ratings, start=1):
            rating.rank = rank
            rating.save(update_fields=['rank'])
    
    @staticmethod
    def get_group_rating(group_id):
        """
        Получить список рейтинга группы.
        
        Returns:
            QuerySet: UserRating отсортирован по очкам (убыванию)
        """
        return UserRating.objects.filter(
            group_id=group_id
        ).select_related('user').order_by('-total_points')
    
    @staticmethod
    def get_student_stats(student_id, group_id=None):
        """
        Получить статистику ученика по посещениям и рейтингу.
        
        Args:
            student_id (int): ID ученика
            group_id (int, optional): ID группы (если None, общая статистика)
        
        Returns:
            dict: Статистика {
                'total_lessons': int,
                'attended': int,
                'absent': int,
                'watched_recording': int,
                'attendance_percent': float,
                'total_points': int,
                'attendance_points': int,
                'homework_points': int,
                'control_points': int,
                'rank_in_group': int or None,
                'total_in_group': int or None,
            }
        """
        if group_id:
            lessons = Lesson.objects.filter(group_id=group_id)
        else:
            lessons = Lesson.objects.all()
        
        records = AttendanceRecord.objects.filter(
            student_id=student_id,
            lesson__in=lessons
        )
        
        total_lessons = lessons.count()
        attended = records.filter(status=AttendanceRecord.STATUS_ATTENDED).count()
        absent = records.filter(status=AttendanceRecord.STATUS_ABSENT).count()
        watched = records.filter(status=AttendanceRecord.STATUS_WATCHED_RECORDING).count()
        
        attendance_percent = (attended / total_lessons * 100) if total_lessons > 0 else 0
        
        # Получить рейтинговую информацию
        rating_info = {
            'total_points': 0,
            'attendance_points': 0,
            'homework_points': 0,
            'control_points': 0,
            'rank_in_group': None,
            'total_in_group': None,
        }
        
        if group_id:
            student_rating = UserRating.objects.filter(
                user_id=student_id,
                group_id=group_id
            ).first()
            
            if student_rating:
                rating_info['total_points'] = student_rating.total_points
                rating_info['attendance_points'] = student_rating.attendance_points
                rating_info['homework_points'] = student_rating.homework_points
                rating_info['control_points'] = student_rating.control_points
                
                # Вычислить место в группе
                higher_count = UserRating.objects.filter(
                    group_id=group_id,
                    total_points__gt=student_rating.total_points
                ).count()
                rating_info['rank_in_group'] = higher_count + 1
                rating_info['total_in_group'] = UserRating.objects.filter(group_id=group_id).count()
        
        return {
            'total_lessons': total_lessons,
            'attended': attended,
            'absent': absent,
            'watched_recording': watched,
            'attendance_percent': round(attendance_percent, 1),
            **rating_info,
        }

    @staticmethod
    def get_consecutive_absences(student_id, group_id=None):
        """
        Подсчитать количество пропусков подряд (начиная с последнего урока).
        
        Args:
            student_id (int): ID ученика
            group_id (int, optional): ID группы
        
        Returns:
            int: Количество пропусков подряд
        """
        if group_id:
            lessons = Lesson.objects.filter(
                group_id=group_id,
                end_time__lt=timezone.now()
            ).order_by('-start_time')[:20]  # Последние 20 уроков
        else:
            lessons = Lesson.objects.filter(
                end_time__lt=timezone.now()
            ).order_by('-start_time')[:50]
        
        consecutive = 0
        for lesson in lessons:
            record = AttendanceRecord.objects.filter(
                lesson=lesson,
                student_id=student_id
            ).first()
            
            if record and record.status == AttendanceRecord.STATUS_ABSENT:
                consecutive += 1
            elif record and record.status in [AttendanceRecord.STATUS_ATTENDED, 
                                               AttendanceRecord.STATUS_WATCHED_RECORDING]:
                break  # Прерываем серию
            else:
                # Нет записи — считаем как пропуск (урок закончился)
                consecutive += 1
        
        return consecutive

    @staticmethod
    def get_students_with_consecutive_absences(group_id, min_absences=3):
        """
        Получить список учеников с N+ пропусками подряд.
        
        Args:
            group_id (int): ID группы
            min_absences (int): Минимальное количество пропусков (по умолчанию 3)
        
        Returns:
            list: Список dict с информацией об ученике и количеством пропусков
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        group = Group.objects.get(id=group_id)
        students = group.students.all()
        
        alerts = []
        for student in students:
            consecutive = RatingService.get_consecutive_absences(
                student_id=student.id,
                group_id=group_id
            )
            
            if consecutive >= min_absences:
                alerts.append({
                    'student_id': student.id,
                    'student_name': student.get_full_name() or student.email,
                    'student_email': student.email,
                    'consecutive_absences': consecutive,
                    'severity': 'critical' if consecutive >= 5 else 'warning',
                })
        
        return alerts

    @staticmethod
    def get_group_rating_for_period(group_id, start_date=None, end_date=None):
        """
        Рассчитать рейтинг группы за указанный период (динамический расчёт).
        
        Args:
            group_id (int): ID группы
            start_date (date, optional): Начало периода
            end_date (date, optional): Конец периода
        
        Returns:
            list[dict]: Список учеников с баллами за период
        """
        from homework.models import Homework, HomeworkGroupAssignment, StudentSubmission
        from analytics.models import ControlPointResult
        from django.db.models import Q
        from datetime import datetime
        
        group = Group.objects.get(id=group_id)
        students = list(group.students.all())
        
        # Фильтруем уроки по периоду
        lessons_qs = Lesson.objects.filter(group_id=group_id)
        if start_date:
            lessons_qs = lessons_qs.filter(start_time__date__gte=start_date)
        if end_date:
            lessons_qs = lessons_qs.filter(start_time__date__lte=end_date)
        lesson_ids = list(lessons_qs.values_list('id', flat=True))
        
        # Домашки за период (по дедлайну или created_at)
        hw_qs = Homework.objects.filter(
            Q(lesson__group_id=group_id)
            | Q(assigned_groups__id=group_id)
            | Q(group_assignments__group_id=group_id)
        ).distinct()
        if start_date:
            hw_qs = hw_qs.filter(
                Q(deadline__date__gte=start_date) | Q(created_at__date__gte=start_date)
            )
        if end_date:
            hw_qs = hw_qs.filter(
                Q(deadline__date__lte=end_date) | Q(created_at__date__lte=end_date)
            )
        homework_ids = list(hw_qs.values_list('id', flat=True))
        
        # Дедлайны
        deadlines_by_hw = {}
        for row in HomeworkGroupAssignment.objects.filter(
            group_id=group_id, homework_id__in=homework_ids
        ).values('homework_id', 'deadline'):
            if row['deadline']:
                deadlines_by_hw[row['homework_id']] = row['deadline']
        for row in Homework.objects.filter(id__in=homework_ids).values('id', 'deadline'):
            deadlines_by_hw.setdefault(row['id'], row['deadline'])
        
        # Контрольные точки за период
        cp_qs = ControlPointResult.objects.filter(control_point__group_id=group_id)
        if start_date:
            cp_qs = cp_qs.filter(control_point__date__gte=start_date)
        if end_date:
            cp_qs = cp_qs.filter(control_point__date__lte=end_date)
        
        results = []
        for student in students:
            # Посещаемость
            attendance_records = AttendanceRecord.objects.filter(
                student_id=student.id,
                lesson_id__in=lesson_ids
            )
            attended = attendance_records.filter(status=AttendanceRecord.STATUS_ATTENDED).count()
            watched = attendance_records.filter(status=AttendanceRecord.STATUS_WATCHED_RECORDING).count()
            attendance_pts = (attended * ATTENDANCE_POINTS) + (watched * WATCHED_RECORDING_POINTS)
            
            # ДЗ
            hw_pts = 0
            submissions = StudentSubmission.objects.filter(
                student_id=student.id,
                homework_id__in=homework_ids,
                status__in=['submitted', 'graded'],
            )
            for sub in submissions:
                score = int(sub.total_score or 0)
                deadline = deadlines_by_hw.get(sub.homework_id)
                if deadline and sub.submitted_at and sub.submitted_at > deadline:
                    score = max(0, score - HOMEWORK_LATE_PENALTY)
                hw_pts += score
            
            # Контрольные
            cp_pts = cp_qs.filter(student_id=student.id).aggregate(
                total=Sum('points')
            )['total'] or 0
            
            total = attendance_pts + hw_pts + int(cp_pts)
            results.append({
                'student_id': student.id,
                'student_name': student.get_full_name() or student.email,
                'email': student.email,
                'attendance_points': attendance_pts,
                'homework_points': hw_pts,
                'control_points': int(cp_pts),
                'total_points': total,
            })
        
        # Сортируем по баллам и присваиваем rank
        results.sort(key=lambda x: x['total_points'], reverse=True)
        for rank, r in enumerate(results, start=1):
            r['rank'] = rank
        
        return results
