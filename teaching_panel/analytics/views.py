from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Avg, Count, Q, F, DurationField, ExpressionWrapper, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.conf import settings
from .models import ControlPoint, ControlPointResult, StudentAIReport
from .serializers import (
    ControlPointSerializer, 
    ControlPointResultSerializer,
    StudentAIReportSerializer,
    StudentAIReportListSerializer
)
from schedule.models import Attendance, Group
from homework.models import StudentSubmission
from homework.models import Homework
from homework.models import Answer
from accounts.models import CustomUser

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
        total_duration_seconds = completed_lessons.annotate(duration=duration_expr).aggregate(
            total=Sum('duration')
        )['total']
        
        # Считаем реальные минуты преподавания
        if total_duration_seconds:
            teaching_minutes = int(total_duration_seconds.total_seconds() / 60)
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


class StudentStatsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Сводная статистика ученика по всем его группам.

        Возвращает:
        {
          overall: {
            groups_count,
            attendance_percent,
            attendance_present,
            attendance_total_marked,
            homework_percent,
            homeworks_total,
            homeworks_completed,
            homework_errors,
            homework_answers_checked
          },
          groups: [
            {
              id,
              name,
              teacher: { id, first_name, email },
              students_count,
              attendance_percent,
              attendance_present,
              attendance_total_marked,
              homework_percent,
              homeworks_total,
              homeworks_completed,
              homework_errors,
              homework_answers_checked
            }
          ]
        }
        """

        user = request.user
        if getattr(user, 'role', None) != 'student':
            return Response({'detail': 'Только для учеников'}, status=403)

        groups_qs = (
            Group.objects.filter(students=user)
            .select_related('teacher')
            .prefetch_related('students')
            .order_by('name')
        )
        group_ids = list(groups_qs.values_list('id', flat=True))

        if not group_ids:
            return Response({
                'overall': {
                    'groups_count': 0,
                    'attendance_percent': None,
                    'attendance_present': 0,
                    'attendance_total_marked': 0,
                    'homework_percent': None,
                    'homeworks_total': 0,
                    'homeworks_completed': 0,
                    'homework_errors': 0,
                    'homework_answers_checked': 0,
                },
                'groups': []
            })

        # Attendance aggregates per group for this student
        att_rows = (
            Attendance.objects
            .filter(student=user, lesson__group_id__in=group_ids)
            .values('lesson__group')
            .annotate(
                present=Count('id', filter=Q(status='present')),
                total_marked=Count('id')
            )
        )
        att_map = {r['lesson__group']: r for r in att_rows}

        # Homework totals per group (published only)
        hw_total_rows = (
            Homework.objects
            .filter(status='published', lesson__group_id__in=group_ids)
            .values('lesson__group')
            .annotate(total=Count('id'))
        )
        hw_total_map = {r['lesson__group']: r for r in hw_total_rows}

        # Homework completed per group for this student
        hw_done_rows = (
            StudentSubmission.objects
            .filter(
                student=user,
                status__in=['submitted', 'graded'],
                homework__status='published',
                homework__lesson__group_id__in=group_ids,
            )
            .values('homework__lesson__group')
            .annotate(done=Count('id'))
        )
        hw_done_map = {r['homework__lesson__group']: r for r in hw_done_rows}

        # Homework errors per group for this student
        # Error = ответ проверен (есть teacher_score или auto_score), не требует ручной проверки,
        # и итоговый балл < max points вопроса.
        answer_base = (
            Answer.objects
            .filter(
                submission__student=user,
                submission__homework__status='published',
                submission__homework__lesson__group_id__in=group_ids,
                question__points__gt=0,
            )
            .exclude(needs_manual_review=True, teacher_score__isnull=True)
            .exclude(teacher_score__isnull=True, auto_score__isnull=True)
            .annotate(resolved_score=Coalesce('teacher_score', 'auto_score'))
        )
        err_rows = (
            answer_base
            .values('submission__homework__lesson__group')
            .annotate(
                errors=Count('id', filter=Q(resolved_score__lt=F('question__points'))),
                checked=Count('id')
            )
        )
        err_map = {r['submission__homework__lesson__group']: r for r in err_rows}

        groups_payload = []
        overall_present = 0
        overall_att_total = 0
        overall_hw_total = 0
        overall_hw_done = 0
        overall_errors = 0
        overall_checked = 0

        for g in groups_qs:
            att = att_map.get(g.id, {})
            present = int(att.get('present', 0) or 0)
            total_marked = int(att.get('total_marked', 0) or 0)
            attendance_percent = round((present / total_marked) * 100, 2) if total_marked else None

            hw_total = int((hw_total_map.get(g.id, {}) or {}).get('total', 0) or 0)
            hw_done = int((hw_done_map.get(g.id, {}) or {}).get('done', 0) or 0)
            homework_percent = round((hw_done / hw_total) * 100, 2) if hw_total else None

            err = err_map.get(g.id, {})
            errors = int(err.get('errors', 0) or 0)
            checked = int(err.get('checked', 0) or 0)

            groups_payload.append({
                'id': g.id,
                'name': g.name,
                'teacher': {
                    'id': g.teacher_id,
                    'first_name': getattr(g.teacher, 'first_name', '') if g.teacher else '',
                    'email': getattr(g.teacher, 'email', '') if g.teacher else '',
                },
                'students_count': g.students.count(),
                'attendance_percent': attendance_percent,
                'attendance_present': present,
                'attendance_total_marked': total_marked,
                'homework_percent': homework_percent,
                'homeworks_total': hw_total,
                'homeworks_completed': hw_done,
                'homework_errors': errors,
                'homework_answers_checked': checked,
            })

            overall_present += present
            overall_att_total += total_marked
            overall_hw_total += hw_total
            overall_hw_done += hw_done
            overall_errors += errors
            overall_checked += checked

        overall_attendance_percent = round((overall_present / overall_att_total) * 100, 2) if overall_att_total else None
        overall_homework_percent = round((overall_hw_done / overall_hw_total) * 100, 2) if overall_hw_total else None

        return Response({
            'overall': {
                'groups_count': len(group_ids),
                'attendance_percent': overall_attendance_percent,
                'attendance_present': overall_present,
                'attendance_total_marked': overall_att_total,
                'homework_percent': overall_homework_percent,
                'homeworks_total': overall_hw_total,
                'homeworks_completed': overall_hw_done,
                'homework_errors': overall_errors,
                'homework_answers_checked': overall_checked,
            },
            'groups': groups_payload,
        })


class StudentAIReportViewSet(viewsets.ModelViewSet):
    """
    API для AI-отчётов по студентам
    
    GET /api/analytics/ai-reports/ - список отчётов
    GET /api/analytics/ai-reports/{id}/ - детали отчёта
    POST /api/analytics/ai-reports/generate/ - сгенерировать новый отчёт
    GET /api/analytics/ai-reports/for-student/{student_id}/ - отчёты по студенту
    """
    queryset = StudentAIReport.objects.all().select_related('student', 'teacher', 'group')
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return StudentAIReportListSerializer
        return StudentAIReportSerializer
    
    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        
        if not user.is_authenticated:
            return qs.none()
        
        if getattr(user, 'role', None) == 'teacher':
            qs = qs.filter(teacher=user)
        elif getattr(user, 'role', None) == 'admin':
            pass  # Admin видит все
        else:
            return qs.none()
        
        # Фильтры
        group_id = self.request.query_params.get('group')
        if group_id:
            qs = qs.filter(group_id=group_id)
        
        student_id = self.request.query_params.get('student')
        if student_id:
            qs = qs.filter(student_id=student_id)
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        
        return qs.order_by('-created_at')
    
    @action(detail=False, methods=['post'], url_path='generate')
    def generate_report(self, request):
        """
        Сгенерировать AI-отчёт по студенту
        
        POST /api/analytics/ai-reports/generate/
        {
            "student_id": 123,
            "group_id": 456,  // опционально
            "period_days": 30  // опционально, по умолчанию 30
        }
        """
        user = request.user
        if getattr(user, 'role', None) not in ['teacher', 'admin']:
            return Response(
                {'detail': 'Только для преподавателей'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        student_id = request.data.get('student_id')
        if not student_id:
            return Response(
                {'detail': 'student_id обязателен'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            student = CustomUser.objects.get(id=student_id, role='student')
        except CustomUser.DoesNotExist:
            return Response(
                {'detail': 'Студент не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        group_id = request.data.get('group_id')
        group = None
        if group_id:
            try:
                group = Group.objects.get(id=group_id)
            except Group.DoesNotExist:
                pass
        
        period_days = int(request.data.get('period_days', 30))
        
        # Генерируем отчёт
        from .ai_analytics_service import generate_student_report
        
        report = generate_student_report(
            student=student,
            teacher=user,
            group=group,
            period_days=period_days,
            provider=getattr(settings, 'AI_ANALYTICS_PROVIDER', 'deepseek')
        )
        
        serializer = StudentAIReportSerializer(report)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'], url_path='generate-for-group')
    def generate_for_group(self, request):
        """
        Сгенерировать AI-отчёты для всех студентов группы
        
        POST /api/analytics/ai-reports/generate-for-group/
        {
            "group_id": 456,
            "period_days": 30
        }
        """
        user = request.user
        if getattr(user, 'role', None) not in ['teacher', 'admin']:
            return Response(
                {'detail': 'Только для преподавателей'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        group_id = request.data.get('group_id')
        if not group_id:
            return Response(
                {'detail': 'group_id обязателен'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            group = Group.objects.get(id=group_id)
        except Group.DoesNotExist:
            return Response(
                {'detail': 'Группа не найдена'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Проверяем что это группа преподавателя
        if group.teacher != user and getattr(user, 'role', None) != 'admin':
            return Response(
                {'detail': 'Нет доступа к этой группе'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        period_days = int(request.data.get('period_days', 30))
        
        from .ai_analytics_service import generate_student_report
        from django.conf import settings
        
        students = group.students.all()
        reports = []
        errors = []
        
        for student in students:
            try:
                report = generate_student_report(
                    student=student,
                    teacher=user,
                    group=group,
                    period_days=period_days,
                    provider=getattr(settings, 'AI_ANALYTICS_PROVIDER', 'deepseek')
                )
                reports.append(report)
            except Exception as e:
                errors.append({
                    'student_id': student.id,
                    'student_email': student.email,
                    'error': str(e)
                })
        
        return Response({
            'generated': len(reports),
            'total_students': students.count(),
            'errors': errors,
            'reports': StudentAIReportListSerializer(reports, many=True).data
        })
    
    @action(detail=False, methods=['get'], url_path='for-student/(?P<student_id>[^/.]+)')
    def for_student(self, request, student_id=None):
        """
        Получить все отчёты по конкретному студенту
        
        GET /api/analytics/ai-reports/for-student/{student_id}/
        """
        user = request.user
        if getattr(user, 'role', None) not in ['teacher', 'admin']:
            return Response(
                {'detail': 'Только для преподавателей'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        reports = self.get_queryset().filter(student_id=student_id)
        serializer = StudentAIReportListSerializer(reports, many=True)
        return Response(serializer.data)
