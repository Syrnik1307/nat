from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Avg, Count, Q, F, DurationField, ExpressionWrapper
from django.utils import timezone
from .models import ControlPoint, ControlPointResult
from .serializers import ControlPointSerializer, ControlPointResultSerializer
from schedule.models import Attendance, Group
from homework.models import StudentSubmission

class ControlPointViewSet(viewsets.ModelViewSet):
    queryset = ControlPoint.objects.all().select_related('teacher', 'group', 'lesson')
    serializer_class = ControlPointSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_authenticated:
            if getattr(user, 'role', None) == 'teacher':
                return qs.filter(teacher=user)
            elif getattr(user, 'role', None) == 'student':
                return qs.filter(group__students=user)
        return qs.none()

class ControlPointResultViewSet(viewsets.ModelViewSet):
    queryset = ControlPointResult.objects.all().select_related('control_point', 'student')
    serializer_class = ControlPointResultSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_authenticated:
            if getattr(user, 'role', None) == 'student':
                return qs.filter(student=user)
            elif getattr(user, 'role', None) == 'teacher':
                return qs.filter(control_point__teacher=user)
        return qs.none()

class GradebookViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def group(self, request):
        group_id = request.query_params.get('group')
        if not group_id:
            return Response({'detail': 'group параметр обязателен'}, status=400)
        try:
            group = Group.objects.get(id=group_id)
        except Group.DoesNotExist:
            return Response({'detail': 'Группа не найдена'}, status=404)

        students = group.students.all()
        attendance_stats = Attendance.objects.filter(lesson__group=group).values('student').annotate(
            present_count=Count('id', filter=Q(status='present')),
            absent_count=Count('id', filter=Q(status='absent')),
            excused_count=Count('id', filter=Q(status='excused'))
        )
        attendance_map = {a['student']: a for a in attendance_stats}

        # Homework averages (exclude NULL total_score for cleaner average)
        hw_avgs = StudentSubmission.objects.filter(homework__lesson__group=group, total_score__isnull=False).values('student').annotate(avg_score=Avg('total_score'))
        hw_map = {h['student']: h for h in hw_avgs}

        # Control point averages
        cp_avgs = ControlPointResult.objects.filter(control_point__group=group).values('student').annotate(avg_points=Avg('points'))
        cp_map = {c['student']: c for c in cp_avgs}

        data = []
        for st in students:
            a = attendance_map.get(st.id, {})
            hw = hw_map.get(st.id, {})
            cp = cp_map.get(st.id, {})
            present = a.get('present_count', 0)
            absent = a.get('absent_count', 0)
            excused = a.get('excused_count', 0)
            total_marked = present + absent + excused
            attendance_pct = round((present / total_marked) * 100, 2) if total_marked else None
            data.append({
                'student_id': st.id,
                'student_email': st.email,
                'student_name': st.get_full_name(),
                'attendance_present': present,
                'attendance_absent': absent,
                'attendance_excused': excused,
                'attendance_percent': attendance_pct,
                'homework_avg': hw.get('avg_score'),
                'control_points_avg': cp.get('avg_points')
            })
        return Response({'group': group.name, 'students': data})


class TeacherStatsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def summary(self, request):
        user = request.user
        if getattr(user, 'role', None) != 'teacher':
            return Response({'detail': 'Только для преподавателей'}, status=403)
        from schedule.models import Lesson, LessonRecording, Group
        lessons = Lesson.objects.filter(teacher=user)
        total_lessons = lessons.count()
        duration_expr = ExpressionWrapper(F('end_time') - F('start_time'), output_field=DurationField())
        avg_duration = lessons.aggregate(avg=Avg(duration_expr))['avg']
        # Процент записанных
        recorded_ids = LessonRecording.objects.filter(lesson__teacher=user).values_list('lesson_id', flat=True).distinct()
        recorded_count = len(recorded_ids)
        recording_ratio = round((recorded_count / total_lessons) * 100, 2) if total_lessons else 0.0
        # Уникальные студенты
        student_ids = Group.objects.filter(teacher=user).values_list('students__id', flat=True).distinct()
        total_students = len([s for s in student_ids if s])
        upcoming = lessons.filter(start_time__gte=timezone.now()).order_by('start_time')[:5]
        upcoming_serialized = [
            {
                'id': l.id,
                'title': l.title,
                'start_time': l.start_time,
                'group': l.group.name
            } for l in upcoming
        ]
        return Response({
            'total_lessons': total_lessons,
            'average_duration_seconds': int(avg_duration.total_seconds()) if avg_duration else None,
            'recorded_lessons': recorded_count,
            'recording_ratio_percent': recording_ratio,
            'total_students': total_students,
            'upcoming_lessons': upcoming_serialized
        })
