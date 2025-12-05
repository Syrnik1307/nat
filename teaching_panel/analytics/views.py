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
        """Сводная статистика преподавателя для главной страницы."""
        user = request.user
        if getattr(user, 'role', None) != 'teacher':
            return Response({'detail': 'Только для преподавателей'}, status=403)
        from schedule.models import Lesson, LessonRecording, Group
        from datetime import timedelta
        
        # Все уроки преподавателя
        lessons = Lesson.objects.filter(teacher=user)
        
        # Проведенные уроки (в прошлом)
        completed_lessons = lessons.filter(start_time__lt=timezone.now())
        total_completed = completed_lessons.count()
        
        # Подсчет реальных минут преподавания (сумма длительности проведенных уроков)
        duration_expr = ExpressionWrapper(F('end_time') - F('start_time'), output_field=DurationField())
        total_duration = completed_lessons.aggregate(total=Avg(duration_expr))['total']
        
        # Считаем реальные минуты на платформе
        if total_duration:
            teaching_minutes = int(total_duration.total_seconds() / 60) * total_completed
        else:
            teaching_minutes = 0
        
        # Минуты на платформе = время преподавания + работа с ДЗ/материалами (примерная оценка +15%)
        portal_minutes = int(teaching_minutes * 1.15)
        
        # Количество групп
        groups = Group.objects.filter(teacher=user)
        total_groups = groups.count()
        
        # Уникальные студенты (из всех групп)
        student_ids = groups.values_list('students__id', flat=True).distinct()
        total_students = len([s for s in student_ids if s])
        
        # Предстоящие уроки
        upcoming = lessons.filter(start_time__gte=timezone.now()).order_by('start_time')[:5]
        upcoming_serialized = [
            {
                'id': l.id,
                'title': l.title,
                'start_time': l.start_time,
                'group': l.group.name if l.group else 'Индивидуальный'
            } for l in upcoming
        ]
        
        return Response({
            'total_lessons': total_completed,
            'teaching_minutes': teaching_minutes,
            'portal_minutes': portal_minutes,
            'total_groups': total_groups,
            'total_students': total_students,
            'upcoming_lessons': upcoming_serialized
        })

    @action(detail=False, methods=['get'])
    def breakdown(self, request):
        """Детализированная статистика по группам и отдельным ученикам.

        Формат ответа:
        {
          groups: [
            {id, name, students_count, attendance_percent, homework_percent}
          ],
          students: [
            {id, name, email, group_id, group_name, attendance_percent, homework_percent}
          ]
        }
        """
        user = request.user
        if getattr(user, 'role', None) != 'teacher':
            return Response({'detail': 'Только для преподавателей'}, status=403)
        from schedule.models import Group, Lesson, Attendance
        from homework.models import Homework, StudentSubmission

        groups = Group.objects.filter(teacher=user).prefetch_related('students')
        group_data = []
        student_rows = []
        for g in groups:
            students = list(g.students.all())
            student_count = len(students)
            # Attendance aggregated
            att_qs = Attendance.objects.filter(lesson__group=g)
            present_count = att_qs.filter(status='present').count()
            total_marked = att_qs.exclude(status__isnull=True).count()
            attendance_percent = round((present_count / total_marked) * 100, 2) if total_marked else None

            # Homework aggregated
            hw_qs = Homework.objects.filter(lesson__group=g)
            total_homeworks = hw_qs.count()
            submissions_completed = StudentSubmission.objects.filter(
                homework__in=hw_qs.values_list('id', flat=True),
                total_score__isnull=False
            ).count()
            # Если каждое ДЗ -> одна попытка на ученика: процент выполненных = завершенные / (доступные * студентов)
            denominator = total_homeworks * student_count if total_homeworks and student_count else 0
            homework_percent = round((submissions_completed / denominator) * 100, 2) if denominator else None

            group_data.append({
                'id': g.id,
                'name': g.name,
                'students_count': student_count,
                'attendance_percent': attendance_percent,
                'homework_percent': homework_percent
            })

            # Individual students breakdown
            for st in students:
                st_att_qs = att_qs.filter(student=st)
                st_present = st_att_qs.filter(status='present').count()
                st_total_marked = st_att_qs.exclude(status__isnull=True).count()
                st_att_pct = round((st_present / st_total_marked) * 100, 2) if st_total_marked else None

                if total_homeworks:
                    st_submissions_completed = StudentSubmission.objects.filter(
                        student=st,
                        homework__in=hw_qs.values_list('id', flat=True),
                        total_score__isnull=False
                    ).count()
                    st_hw_pct = round((st_submissions_completed / total_homeworks) * 100, 2) if total_homeworks else None
                else:
                    st_hw_pct = None

                student_rows.append({
                    'id': st.id,
                    'name': st.get_full_name(),
                    'email': st.email,
                    'group_id': g.id,
                    'group_name': g.name,
                    'attendance_percent': st_att_pct,
                    'homework_percent': st_hw_pct
                })

        return Response({'groups': group_data, 'students': student_rows})
