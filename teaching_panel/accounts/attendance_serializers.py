"""
Сериализаторы для системы посещений, рейтинга и индивидуальных учеников.
"""

from rest_framework import serializers
from django.utils import timezone

from accounts.models import (
    AttendanceRecord, 
    UserRating, 
    IndividualStudent,
    CustomUser
)
from schedule.models import Lesson, Group


class AttendanceRecordSerializer(serializers.ModelSerializer):
    """Сериализатор для записи посещения"""
    
    lesson_title = serializers.CharField(source='lesson.title', read_only=True)
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    student_email = serializers.CharField(source='student.email', read_only=True)
    teacher_name = serializers.CharField(source='recorded_by.get_full_name', read_only=True, allow_null=True)
    
    class Meta:
        model = AttendanceRecord
        fields = [
            'id', 'lesson', 'lesson_title',
            'student', 'student_name', 'student_email',
            'status', 'auto_recorded',
            'recorded_by', 'teacher_name',
            'recorded_at', 'updated_at'
        ]
        read_only_fields = ['recorded_at', 'updated_at', 'auto_recorded']


class UserRatingSerializer(serializers.ModelSerializer):
    """Сериализатор для рейтинга ученика"""
    
    student_name = serializers.CharField(source='user.get_full_name', read_only=True)
    student_email = serializers.CharField(source='user.email', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True, allow_null=True)
    
    class Meta:
        model = UserRating
        fields = [
            'id', 'user', 'student_name', 'student_email',
            'group', 'group_name',
            'total_points', 'attendance_points', 'homework_points',
            'control_points_value', 'rank',
            'updated_at'
        ]
        read_only_fields = ['total_points', 'rank', 'updated_at']


class IndividualStudentSerializer(serializers.ModelSerializer):
    """Сериализатор для индивидуального ученика"""
    
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    teacher_name = serializers.CharField(source='teacher.get_full_name', read_only=True, allow_null=True)
    
    class Meta:
        model = IndividualStudent
        fields = [
            'user_id', 'email', 'first_name', 'last_name',
            'teacher', 'teacher_name',
            'teacher_notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class AttendanceLogSerializer(serializers.Serializer):
    """Сериализатор для журнала посещений группы."""

    lessons = serializers.SerializerMethodField()
    students = serializers.SerializerMethodField()
    records = serializers.SerializerMethodField()
    meta = serializers.SerializerMethodField()

    def get_lessons(self, obj):
        """Получить список занятий группы"""
        precomputed = self.context.get('lessons_data')
        if precomputed is not None:
            return precomputed

        group_id = self.context.get('group_id')
        lessons = Lesson.objects.filter(group_id=group_id).order_by('start_time')

        return [
            {
                'id': lesson.id,
                'title': lesson.title,
                'start_time': lesson.start_time,
                'end_time': lesson.end_time,
            }
            for lesson in lessons
        ]

    def get_students(self, obj):
        """Получить список учеников группы"""
        precomputed = self.context.get('students_data')
        if precomputed is not None:
            return precomputed

        group_id = self.context.get('group_id')
        group = Group.objects.get(id=group_id)
        students = group.students.all()

        return [
            {
                'id': student.id,
                'name': student.get_full_name(),
                'email': student.email,
            }
            for student in students
        ]

    def get_records(self, obj):
        """Получить записи посещений"""
        precomputed = self.context.get('records_data')
        if precomputed is not None:
            return precomputed

        group_id = self.context.get('group_id')
        records_data = {}
        records = AttendanceRecord.objects.filter(lesson__group_id=group_id)

        for record in records:
            key = f"{record.student_id}_{record.lesson_id}"
            records_data[key] = {
                'status': record.status,
                'auto_recorded': record.auto_recorded,
            }

        return records_data

    def get_meta(self, obj):
        """Дополнительная мета-информация по журналу"""
        return self.context.get('meta', {})


class GroupRatingSerializer(serializers.Serializer):
    """Сериализатор для рейтинга группы"""
    
    students = serializers.SerializerMethodField()
    group_stats = serializers.SerializerMethodField()
    
    def get_students(self, obj):
        """Получить список рейтинга учеников в группе"""
        group_id = self.context.get('group_id')
        ratings = UserRating.objects.filter(
            group_id=group_id
        ).select_related('user').order_by('-total_points')
        
        return [
            {
                'rank': rating.rank,
                'student_id': rating.user.id,
                'student_name': rating.user.get_full_name(),
                'email': rating.user.email,
                'total_points': rating.total_points,
                'attendance_points': rating.attendance_points,
                'homework_points': rating.homework_points,
                'control_points': rating.control_points_value,
            }
            for rating in ratings
        ]
    
    def get_group_stats(self, obj):
        """Получить статистику группы"""
        group_id = self.context.get('group_id')
        ratings = UserRating.objects.filter(group_id=group_id)
        
        if not ratings.exists():
            return {
                'average_points': 0,
                'total_students': 0,
            }
        
        average_points = ratings.aggregate(
            avg=serializers.models.Avg('total_points')
        )['avg'] or 0
        
        return {
            'average_points': round(average_points, 1),
            'total_students': ratings.count(),
        }


class StudentCardSerializer(serializers.Serializer):
    """Сериализатор для карточки ученика"""
    
    student_id = serializers.IntegerField()
    name = serializers.CharField()
    email = serializers.CharField()
    stats = serializers.SerializerMethodField()
    errors = serializers.SerializerMethodField()
    teacher_notes = serializers.CharField(required=False, allow_blank=True)
    
    def get_stats(self, obj):
        """Получить статистику ученика"""
        from accounts.attendance_service import RatingService
        
        student_id = obj.get('student_id')
        group_id = self.context.get('group_id')
        
        stats = RatingService.get_student_stats(
            student_id=student_id,
            group_id=group_id
        )
        
        return stats
    
    def get_errors(self, obj):
        """Получить ошибки ученика (недовыполненные ДЗ и контрольные)"""
        # TODO: Интегрировать когда доступны модели ДЗ и контрольных точек
        return {
            'incomplete_homework': [],
            'failed_control_points': [],
        }


class GroupReportSerializer(serializers.Serializer):
    """Сериализатор для отчета группы"""
    
    group_id = serializers.IntegerField()
    group_name = serializers.CharField()
    
    attendance_percent = serializers.FloatField()
    homework_percent = serializers.FloatField()
    control_points_percent = serializers.FloatField()
    
    total_lessons = serializers.IntegerField()
    total_students = serializers.IntegerField()
    
    def get_representation(self, instance):
        """Переопределяем получение представления"""
        group_id = self.context.get('group_id')
        group = Group.objects.get(id=group_id)
        
        # Рассчитываем статистику
        all_records = AttendanceRecord.objects.filter(lesson__group_id=group_id)
        total_possible = group.students.count() * group.lessons.count()
        
        attended = all_records.filter(status=AttendanceRecord.STATUS_ATTENDED).count()
        attendance_percent = (attended / total_possible * 100) if total_possible > 0 else 0
        
        return {
            'group_id': group.id,
            'group_name': group.name,
            'attendance_percent': round(attendance_percent, 1),
            'homework_percent': 0,  # TODO
            'control_points_percent': 0,  # TODO
            'total_lessons': group.lessons.count(),
            'total_students': group.students.count(),
        }
