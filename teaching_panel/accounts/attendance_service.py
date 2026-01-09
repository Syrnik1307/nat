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
ATTENDANCE_POINTS = 10  # За присутствие
WATCHED_RECORDING_POINTS = 10  # За просмотр записи
ABSENCE_POINTS = -5  # За отсутствие
HOMEWORK_POINTS = 5  # За выполненное ДЗ
CONTROL_POINT_PASSED = 15  # За пройденную контрольную точку
CONTROL_POINT_PARTIAL = 8  # За контрольную точку с ошибками (50%)


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
        
        # Расчет: присутствие (+10) + просмотр записи (+10, но не суммируется с присутствием)
        # То есть, если ученик был, но не смотрел запись = +10
        # Если не был, но смотрел запись = +10
        points = (attended_count * ATTENDANCE_POINTS) + (watched_count * WATCHED_RECORDING_POINTS)
        
        # Штраф за отсутствие
        absent_count = records.filter(
            status=AttendanceRecord.STATUS_ABSENT
        ).count()
        points += (absent_count * ABSENCE_POINTS)
        
        return max(0, points)  # Не может быть отрицательным
    
    @staticmethod
    def _calculate_homework_points(student_id, group_id):
        """
        Рассчитать очки за домашние задания.
        Подсчитываем выполненные и проверенные ДЗ.
        """
        # TODO: Интегрировать с системой ДЗ когда доступна модель Homework
        # На данный момент возвращаем 0
        return 0
    
    @staticmethod
    def _calculate_control_points(student_id, group_id):
        """
        Рассчитать очки за контрольные точки.
        Подсчитываем пройденные контрольные точки.
        """
        # TODO: Интегрировать с системой контрольных точек когда доступна модель ControlPoint
        # На данный момент возвращаем 0
        return 0
    
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
        Получить статистику ученика по посещениям.
        
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
        
        return {
            'total_lessons': total_lessons,
            'attended': attended,
            'absent': absent,
            'watched_recording': watched,
            'attendance_percent': round(attendance_percent, 1),
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
