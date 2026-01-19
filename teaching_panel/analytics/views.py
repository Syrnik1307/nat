from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Avg, Count, Q, F, DurationField, ExpressionWrapper, Sum, FloatField
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.conf import settings
from .models import ControlPoint, ControlPointResult, StudentAIReport, StudentBehaviorReport
from .serializers import (
    ControlPointSerializer, 
    ControlPointResultSerializer,
    StudentAIReportSerializer,
    StudentAIReportListSerializer,
    StudentBehaviorReportSerializer,
    StudentBehaviorReportListSerializer,
)
from .serializers_analytics_extra import LessonTranscriptStatsSerializer
from schedule.models import Attendance, Group, LessonTranscriptStats
from homework.models import StudentSubmission
from homework.models import Homework
from homework.models import Answer
from accounts.models import CustomUser

class AnalyticsDashboardViewSet(viewsets.ViewSet):
    """
    Dashboard analytics for teacher.
    Aggregates data across all groups.
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def summary(self, request):
        user = request.user
        if getattr(user, 'role', '') != 'teacher':
             return Response({'detail': 'Not allowed'}, status=403)
        
        # Groups count
        groups = Group.objects.filter(teacher=user)
        groups_count = groups.count()
        
        # Students count
        students_count = CustomUser.objects.filter(role='student', enrolled_groups__in=groups).distinct().count()

        return Response({
            'groups_count': groups_count,
            'students_count': students_count,
        })

    @action(detail=False, methods=['get'], url_path='group-transcript-summary')
    def group_transcript_summary(self, request):
        group_id = request.query_params.get('group_id')
        if not group_id:
            return Response({'detail': 'group_id required'}, status=400)
            
        group = get_object_or_404(Group, id=group_id)
        # Check permission (simple check if teacher is related or admin)
        if request.user.role == 'teacher' and group.teacher != request.user:
             return Response({'detail': 'Not your group'}, status=403)

        # Get all stats for lessons in this group
        stats_qs = LessonTranscriptStats.objects.filter(lesson__group_id=group_id)
        
        if not stats_qs.exists():
             return Response({'detail': 'No analytics found'}, status=200)

        # Aggregate data manually from JSON fields (since JSON aggregation is complex/db-specific)
        # or just sum up pre-calculated fields if we had them per student.
        # We only have stats_json.
        
        # Structure of stats_json:
        # {
        #   "clean_talk_time": { "Student Name": 120, "Teacher": 500 },
        #   "mentions": { "Student Name": 5 }
        # }
        
        total_student_talk = {} # "Name": seconds
        total_mentions = {} # "Name": count
        lesson_dates = []
        
        for stat in stats_qs:
            data = stat.stats_json
            date_label = stat.lesson.start_time.strftime('%Y-%m-%d')
            lesson_dates.append(date_label)
            
            # Talk time
            talk_times = data.get('clean_talk_time', {})
            for name, seconds in talk_times.items():
                if name == 'Teacher' or name == 'Preacher':
                    continue
                total_student_talk[name] = total_student_talk.get(name, 0) + seconds
                
            # Mentions
            mentions = data.get('mentions', {})
            for name, count in mentions.items():
                total_mentions[name] = total_mentions.get(name, 0) + count

        # Sort top talkers
        sorted_talk = sorted(total_student_talk.items(), key=lambda x: x[1], reverse=True)
        # Sort top mentions
        sorted_mentions = sorted(total_mentions.items(), key=lambda x: x[1], reverse=True)

        return Response({
            'total_lessons_analyzed': stats_qs.count(),
            'talk_time_leaderboard': [{'name': k, 'seconds': v} for k, v in sorted_talk],
            'mentions_leaderboard': [{'name': k, 'count': v} for k, v in sorted_mentions],
        })

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

        # Доступ: админ всегда, преподаватель только к своим группам, студент только если состоит
        role = getattr(request.user, 'role', None)
        if role == 'teacher' and group.teacher_id != request.user.id:
            return Response({'detail': 'Нет доступа к этой группе'}, status=403)
        if role == 'student' and not group.students.filter(id=request.user.id).exists():
            return Response({'detail': 'Нет доступа к этой группе'}, status=403)

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
        role = getattr(user, 'role', None)
        # На главную "учителя" также может заходить админ (Protected allowRoles=['teacher','admin']).
        # Если админ ведёт группы/уроки, статистика должна работать.
        if role not in ('teacher', 'admin'):
            return Response({'detail': 'Только для преподавателей'}, status=403)

        from schedule.models import Lesson, Group
        from datetime import timedelta
        
        now = timezone.now()

        # Все уроки преподавателя
        lessons = Lesson.objects.filter(teacher=user)

        # Проведенные уроки (у которых уже прошло время окончания)
        completed_lessons = lessons.filter(end_time__lt=now)
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
        total_students = CustomUser.objects.filter(
            role='student',
            enrolled_groups__in=groups
        ).distinct().count()
        
        # Предстоящие уроки
        upcoming = lessons.filter(start_time__gte=now).order_by('start_time')[:5]
        upcoming_serialized = [
            {
                'id': l.id,
                'title': l.title,
                'start_time': l.start_time,
                'group': l.group.name if l.group else 'Индивидуальный'
            } for l in upcoming
        ]
        
        # === HOMEWORK ANALYTICS (за 30 дней) ===
        from homework.models import Homework, StudentSubmission, Answer
        
        thirty_days_ago = now - timedelta(days=30)

        # Все ДЗ учителя (исключаем шаблоны)
        teacher_homeworks = Homework.objects.filter(teacher=user, is_template=False)
        homework_ids = teacher_homeworks.values_list('id', flat=True)
        
        # Все сабмиты за 30 дней (для метрик с явным окном)
        submissions_30d = StudentSubmission.objects.filter(
            homework_id__in=homework_ids,
            submitted_at__isnull=False,
            submitted_at__gte=thirty_days_ago,
        )
        
        # 1. Среднее время проверки (дни) — по проверенным сдачам за последние 30 дней
        graded_submissions_30d = submissions_30d.filter(status='graded', graded_at__isnull=False)
        grading_duration = ExpressionWrapper(F('graded_at') - F('submitted_at'), output_field=DurationField())
        avg_duration = graded_submissions_30d.aggregate(avg=Avg(grading_duration)).get('avg')
        avg_grading_days = round(avg_duration.total_seconds() / 86400, 1) if avg_duration else 0

        # 2. Количество непроверенных работ (все актуальные, без ограничения по 30 дням)
        pending_count = StudentSubmission.objects.filter(
            homework_id__in=homework_ids,
            status='submitted',
            graded_at__isnull=True,
        ).count()
        
        # 3. Проверено ДЗ за 30 дней
        graded_count_30d = graded_submissions_30d.count()
        
        # 4. Автопроверено вопросов (все время): auto_score выставлен системой
        auto_graded_answers = Answer.objects.filter(
            submission__homework_id__in=homework_ids,
            submission__submitted_at__isnull=False,
            auto_score__isnull=False,
        ).count()
        
        # Время сэкономлено: 2 минуты на вопрос
        time_saved_minutes = auto_graded_answers * 2
        
        # 5. % учеников, сдающих ДЗ вовремя
        # Берём ДЗ с дедлайном за последние 30 дней и считаем долю учеников,
        # которые не просрочили ни одной сдачи в этом окне.
        deadline_window_homeworks = teacher_homeworks.filter(
            deadline__isnull=False,
            deadline__gte=thirty_days_ago,
            deadline__lte=now,
        )
        deadline_submissions = StudentSubmission.objects.filter(
            homework__in=deadline_window_homeworks,
            submitted_at__isnull=False,
        )
        student_deadline_stats = list(
            deadline_submissions.values('student').annotate(
                total=Count('id'),
                on_time=Count('id', filter=Q(submitted_at__lte=F('homework__deadline'))),
            )
        )
        if student_deadline_stats:
            on_time_students = sum(1 for row in student_deadline_stats if row.get('on_time') == row.get('total'))
            on_time_percent = round((on_time_students / len(student_deadline_stats)) * 100)
        else:
            on_time_percent = 0
        
        return Response({
            'total_lessons': total_completed,
            'teaching_minutes': teaching_minutes,
            'portal_minutes': portal_minutes,
            'total_groups': total_groups,
            'total_students': total_students,
            'upcoming_lessons': upcoming_serialized,
            # Новые поля для homework-аналитики
            'avg_grading_days': avg_grading_days,
            'pending_submissions': pending_count,
            'graded_count_30d': graded_count_30d,
            'auto_graded_answers': auto_graded_answers,
            'time_saved_minutes': time_saved_minutes,
            'on_time_percent': on_time_percent,
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

    @action(detail=False, methods=['get'])
    def sla_details(self, request):
        """
        Детализация SLA проверки ДЗ.
        
        Возвращает:
        - Распределение работ по времени проверки (до 3 дней, 4-7, 8-10, >10)
        - Список работ ожидающих проверки с "возрастом"
        - Общий "здоровье" SLA
        """
        user = request.user
        role = getattr(user, 'role', None)
        if role not in ('teacher', 'admin'):
            return Response({'detail': 'Только для преподавателей'}, status=403)
        
        from homework.models import Homework, StudentSubmission
        from datetime import timedelta
        
        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)
        
        # Все ДЗ учителя
        teacher_homeworks = Homework.objects.filter(teacher=user, is_template=False)
        homework_ids = list(teacher_homeworks.values_list('id', flat=True))
        
        # === Распределение времени проверки за 30 дней ===
        graded = StudentSubmission.objects.filter(
            homework_id__in=homework_ids,
            status='graded',
            graded_at__isnull=False,
            submitted_at__isnull=False,
            graded_at__gte=thirty_days_ago,
        )
        
        # Считаем время проверки для каждой работы
        sla_distribution = {'ideal': 0, 'good': 0, 'slow': 0, 'critical': 0}
        grading_days = []
        for sub in graded:
            days = (sub.graded_at - sub.submitted_at).total_seconds() / 86400
            grading_days.append(days)
            if days <= 3:
                sla_distribution['ideal'] += 1
            elif days <= 7:
                sla_distribution['good'] += 1
            elif days <= 10:
                sla_distribution['slow'] += 1
            else:
                sla_distribution['critical'] += 1

        def _percentile(sorted_values, pct):
            if not sorted_values:
                return None
            if pct <= 0:
                return float(sorted_values[0])
            if pct >= 100:
                return float(sorted_values[-1])
            n = len(sorted_values)
            if n == 1:
                return float(sorted_values[0])
            pos = (pct / 100) * (n - 1)
            lo = int(pos)
            hi = min(lo + 1, n - 1)
            if lo == hi:
                return float(sorted_values[lo])
            frac = pos - lo
            return float(sorted_values[lo] * (1 - frac) + sorted_values[hi] * frac)

        grading_days_sorted = sorted(grading_days)
        grading_time_days_median = _percentile(grading_days_sorted, 50)
        grading_time_days_p90 = _percentile(grading_days_sorted, 90)
        
        total_graded = sum(sla_distribution.values())
        sla_percents = {
            k: round(v / total_graded * 100) if total_graded else 0
            for k, v in sla_distribution.items()
        }
        
        # === Бэклог: работы ожидающие проверки с "возрастом" ===
        pending = StudentSubmission.objects.filter(
            homework_id__in=homework_ids,
            status='submitted',
            graded_at__isnull=True,
            submitted_at__isnull=False,
        ).select_related('student', 'homework').order_by('submitted_at')
        
        backlog_items = []
        backlog_counts = {'fresh': 0, 'aging': 0, 'old': 0, 'critical': 0}
        
        for sub in pending[:50]:  # Лимит 50 для ответа
            days_waiting = (now - sub.submitted_at).total_seconds() / 86400
            
            if days_waiting <= 3:
                severity = 'fresh'
            elif days_waiting <= 7:
                severity = 'aging'
            elif days_waiting <= 10:
                severity = 'old'
            else:
                severity = 'critical'
            
            backlog_counts[severity] += 1
            backlog_items.append({
                'id': sub.id,
                'homework_id': sub.homework_id,
                'homework_title': sub.homework.title,
                'student_id': sub.student_id,
                'student_name': sub.student.get_full_name(),
                'submitted_at': sub.submitted_at.isoformat(),
                'days_waiting': round(days_waiting, 1),
                'severity': severity,
            })
        
        # Подсчитываем общее количество по категориям для всего бэклога
        for sub in pending[50:]:
            days_waiting = (now - sub.submitted_at).total_seconds() / 86400
            if days_waiting <= 3:
                backlog_counts['fresh'] += 1
            elif days_waiting <= 7:
                backlog_counts['aging'] += 1
            elif days_waiting <= 10:
                backlog_counts['old'] += 1
            else:
                backlog_counts['critical'] += 1
        
        # Общий "здоровье" SLA: 100 если нет critical/old, минус баллы за проблемы
        health_score = 100
        health_score -= backlog_counts['critical'] * 10
        health_score -= backlog_counts['old'] * 5
        health_score -= backlog_counts['aging'] * 2
        health_score = max(0, min(100, health_score))
        
        if health_score >= 80:
            health_status = 'excellent'
        elif health_score >= 60:
            health_status = 'good'
        elif health_score >= 40:
            health_status = 'warning'
        else:
            health_status = 'critical'
        
        return Response({
            'sla_distribution': sla_distribution,
            'sla_percents': sla_percents,
            'total_graded_30d': total_graded,
            'grading_time_days_median': round(grading_time_days_median, 1) if grading_time_days_median is not None else None,
            'grading_time_days_p90': round(grading_time_days_p90, 1) if grading_time_days_p90 is not None else None,
            'backlog': {
                'total': pending.count(),
                'counts': backlog_counts,
                'items': backlog_items,
            },
            'health': {
                'score': health_score,
                'status': health_status,
            },
        })

    @action(detail=False, methods=['get'])
    def monthly_dynamics(self, request):
        """Динамика по месяцам (простые метрики для преподавателя).

        Параметры:
        - months: количество месяцев (по умолчанию 3, максимум 12)

        Метрики (по каждому месяцу):
        - lessons_count
        - attendance_percent
        - homework_submitted_count
        - homework_graded_count
        - avg_score_percent (нормализовано к 100%)
        - below_60_percent_count
        - active_students_count
        """
        user = request.user
        role = getattr(user, 'role', None)
        if role not in ('teacher', 'admin'):
            return Response({'detail': 'Только для преподавателей'}, status=403)

        from datetime import timedelta
        from schedule.models import Lesson, Attendance
        from homework.models import StudentSubmission

        now = timezone.now()
        try:
            months = int(request.query_params.get('months', 3))
        except (TypeError, ValueError):
            months = 3
        months = max(1, min(12, months))

        def _month_start(dt):
            return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        def _add_months(dt, delta_months):
            year = dt.year
            month = dt.month + delta_months
            while month > 12:
                month -= 12
                year += 1
            while month < 1:
                month += 12
                year -= 1
            return dt.replace(year=year, month=month, day=1)

        # Берём диапазон, включающий текущий месяц, и ещё (months-1) месяцев назад
        current_month_start = _month_start(now)
        oldest_month_start = _add_months(current_month_start, -(months - 1))

        results = []
        month_cursor = oldest_month_start
        while month_cursor <= current_month_start:
            next_month = _add_months(month_cursor, 1)

            lessons_qs = Lesson.objects.filter(
                teacher=user,
                start_time__gte=month_cursor,
                start_time__lt=next_month,
            )
            lessons_count = lessons_qs.count()

            attendance_qs = Attendance.objects.filter(
                lesson__teacher=user,
                lesson__start_time__gte=month_cursor,
                lesson__start_time__lt=next_month,
            )
            attendance_total = attendance_qs.exclude(status__isnull=True).count()
            attendance_present = attendance_qs.filter(status='present').count()
            attendance_percent = round((attendance_present / attendance_total) * 100, 1) if attendance_total else None

            submissions_submitted_qs = StudentSubmission.objects.filter(
                homework__teacher=user,
                submitted_at__isnull=False,
                submitted_at__gte=month_cursor,
                submitted_at__lt=next_month,
            ).exclude(status='in_progress')
            homework_submitted_count = submissions_submitted_qs.count()

            submissions_graded_qs = StudentSubmission.objects.filter(
                homework__teacher=user,
                status='graded',
                graded_at__isnull=False,
                graded_at__gte=month_cursor,
                graded_at__lt=next_month,
                total_score__isnull=False,
            )
            homework_graded_count = submissions_graded_qs.count()

            score_pct_expr = ExpressionWrapper(
                100.0 * F('total_score') / Coalesce(F('homework__max_score'), 100),
                output_field=FloatField(),
            )
            avg_score_percent = submissions_graded_qs.annotate(score_pct=score_pct_expr).aggregate(
                avg_pct=Avg('score_pct')
            )['avg_pct']
            avg_score_percent = round(avg_score_percent, 1) if avg_score_percent is not None else None

            below_60_percent_count = submissions_graded_qs.annotate(score_pct=score_pct_expr).filter(
                score_pct__lt=60
            ).count()

            # Активные ученики: отметки посещаемости ИЛИ сдача ДЗ
            active_student_ids = set(attendance_qs.values_list('student_id', flat=True).distinct())
            active_student_ids.update(submissions_submitted_qs.values_list('student_id', flat=True).distinct())

            results.append({
                'month': month_cursor.strftime('%Y-%m'),
                'month_start': month_cursor.date().isoformat(),
                'lessons_count': lessons_count,
                'attendance_percent': attendance_percent,
                'attendance_total': attendance_total,
                'attendance_present': attendance_present,
                'homework_submitted_count': homework_submitted_count,
                'homework_graded_count': homework_graded_count,
                'avg_score_percent': avg_score_percent,
                'below_60_percent_count': below_60_percent_count,
                'active_students_count': len(active_student_ids),
            })

            month_cursor = next_month

        return Response({
            'months': results,
            'window_months': months,
            'generated_at': now.isoformat(),
        })

    @action(detail=False, methods=['get'])
    def weekly_dynamics(self, request):
        """Динамика по неделям (простые метрики, чтобы быстро видеть изменения).

        Параметры:
        - weeks: количество недель (по умолчанию 8, максимум 26)

        Метрики (по каждой неделе):
        - lessons_count
        - attendance_percent
        - homework_submitted_count
        - homework_graded_count
        - avg_score_percent (нормализовано к 100%)
        - below_60_percent_count
        - active_students_count
        """
        user = request.user
        role = getattr(user, 'role', None)
        if role not in ('teacher', 'admin'):
            return Response({'detail': 'Только для преподавателей'}, status=403)

        from datetime import timedelta
        from schedule.models import Lesson, Attendance
        from homework.models import StudentSubmission

        now = timezone.now()
        try:
            weeks = int(request.query_params.get('weeks', 8))
        except (TypeError, ValueError):
            weeks = 8
        weeks = max(1, min(26, weeks))

        def _week_start(dt):
            # Понедельник = начало недели
            base = dt - timedelta(days=dt.weekday())
            return base.replace(hour=0, minute=0, second=0, microsecond=0)

        current_week_start = _week_start(now)
        oldest_week_start = current_week_start - timedelta(days=(weeks - 1) * 7)

        results = []
        week_cursor = oldest_week_start
        while week_cursor <= current_week_start:
            next_week = week_cursor + timedelta(days=7)

            lessons_qs = Lesson.objects.filter(
                teacher=user,
                start_time__gte=week_cursor,
                start_time__lt=next_week,
            )
            lessons_count = lessons_qs.count()

            attendance_qs = Attendance.objects.filter(
                lesson__teacher=user,
                lesson__start_time__gte=week_cursor,
                lesson__start_time__lt=next_week,
            )
            attendance_total = attendance_qs.exclude(status__isnull=True).count()
            attendance_present = attendance_qs.filter(status='present').count()
            attendance_percent = round((attendance_present / attendance_total) * 100, 1) if attendance_total else None

            submissions_submitted_qs = StudentSubmission.objects.filter(
                homework__teacher=user,
                submitted_at__isnull=False,
                submitted_at__gte=week_cursor,
                submitted_at__lt=next_week,
            ).exclude(status='in_progress')
            homework_submitted_count = submissions_submitted_qs.count()

            submissions_graded_qs = StudentSubmission.objects.filter(
                homework__teacher=user,
                status='graded',
                graded_at__isnull=False,
                graded_at__gte=week_cursor,
                graded_at__lt=next_week,
                total_score__isnull=False,
            )
            homework_graded_count = submissions_graded_qs.count()

            score_pct_expr = ExpressionWrapper(
                100.0 * F('total_score') / Coalesce(F('homework__max_score'), 100),
                output_field=FloatField(),
            )
            avg_score_percent = submissions_graded_qs.annotate(score_pct=score_pct_expr).aggregate(
                avg_pct=Avg('score_pct')
            )['avg_pct']
            avg_score_percent = round(avg_score_percent, 1) if avg_score_percent is not None else None

            below_60_percent_count = submissions_graded_qs.annotate(score_pct=score_pct_expr).filter(
                score_pct__lt=60
            ).count()

            active_student_ids = set(attendance_qs.values_list('student_id', flat=True).distinct())
            active_student_ids.update(submissions_submitted_qs.values_list('student_id', flat=True).distinct())

            results.append({
                'week_start': week_cursor.date().isoformat(),
                'week_end': (next_week.date() - timedelta(days=1)).isoformat(),
                'lessons_count': lessons_count,
                'attendance_percent': attendance_percent,
                'attendance_total': attendance_total,
                'attendance_present': attendance_present,
                'homework_submitted_count': homework_submitted_count,
                'homework_graded_count': homework_graded_count,
                'avg_score_percent': avg_score_percent,
                'below_60_percent_count': below_60_percent_count,
                'active_students_count': len(active_student_ids),
            })

            week_cursor = next_week

        return Response({
            'weeks': results,
            'window_weeks': weeks,
            'generated_at': now.isoformat(),
        })

    @action(detail=False, methods=['get'])
    def student_risks(self, request):
        """
        Риск-скоринг учеников.
        
        Объединяет:
        - Пропуски подряд
        - Просрочки ДЗ за последние 14 дней
        - Падение оценок ниже порога (60%)
        
        Возвращает список учеников с риском и рекомендациями.
        """
        user = request.user
        role = getattr(user, 'role', None)
        if role not in ('teacher', 'admin'):
            return Response({'detail': 'Только для преподавателей'}, status=403)
        
        from schedule.models import Group
        from homework.models import Homework, StudentSubmission
        from accounts.models import AttendanceRecord
        from accounts.attendance_service import RatingService
        from datetime import timedelta
        
        now = timezone.now()
        fourteen_days_ago = now - timedelta(days=14)
        thirty_days_ago = now - timedelta(days=30)
        
        # Группы учителя
        groups = Group.objects.filter(teacher=user).prefetch_related('students')
        
        # ДЗ учителя для анализа
        teacher_homeworks = Homework.objects.filter(teacher=user, is_template=False)
        homework_ids = list(teacher_homeworks.values_list('id', flat=True))
        
        # Собираем риски по всем ученикам
        student_risks = {}
        
        for group in groups:
            # 1. Пропуски подряд (используем существующий сервис)
            try:
                absence_alerts = RatingService.get_students_with_consecutive_absences(
                    group_id=group.id,
                    min_absences=2  # Более чувствительный порог
                )
                for alert in absence_alerts:
                    sid = alert['student_id']
                    if sid not in student_risks:
                        student_risks[sid] = {
                            'student_id': sid,
                            'student_name': alert['student_name'],
                            'student_email': alert.get('student_email', ''),
                            'group_id': group.id,
                            'group_name': group.name,
                            'risk_score': 0,
                            'risk_factors': [],
                            'recommendations': [],
                        }
                    
                    absences = alert['consecutive_absences']
                    if absences >= 3:
                        student_risks[sid]['risk_score'] += 40
                        student_risks[sid]['risk_factors'].append({
                            'type': 'attendance',
                            'severity': 'critical',
                            'message': f'Пропустил {absences} занятий подряд',
                        })
                        student_risks[sid]['recommendations'].append('Связаться с учеником/родителем')
                    elif absences >= 2:
                        student_risks[sid]['risk_score'] += 20
                        student_risks[sid]['risk_factors'].append({
                            'type': 'attendance',
                            'severity': 'warning',
                            'message': f'Пропустил {absences} занятия подряд',
                        })
                        student_risks[sid]['recommendations'].append('Предложить личную беседу')
            except Exception:
                pass  # Если сервис недоступен, продолжаем
            
            # 2. Просрочки ДЗ за 14 дней
            for student in group.students.all():
                if student.id not in student_risks:
                    student_risks[student.id] = {
                        'student_id': student.id,
                        'student_name': student.get_full_name(),
                        'student_email': student.email,
                        'group_id': group.id,
                        'group_name': group.name,
                        'risk_score': 0,
                        'risk_factors': [],
                        'recommendations': [],
                    }
                
                # Просрочки: ДЗ с дедлайном в последние 14 дней, которые не сданы или сданы после дедлайна
                late_homeworks = teacher_homeworks.filter(
                    lesson__group=group,
                    deadline__isnull=False,
                    deadline__gte=fourteen_days_ago,
                    deadline__lte=now,
                )
                
                late_count = 0
                not_submitted_count = 0
                
                for hw in late_homeworks:
                    submission = StudentSubmission.objects.filter(
                        homework=hw,
                        student=student,
                    ).first()
                    
                    if not submission or not submission.submitted_at:
                        not_submitted_count += 1
                    elif submission.submitted_at > hw.deadline:
                        late_count += 1
                
                if not_submitted_count >= 2:
                    student_risks[student.id]['risk_score'] += 30
                    student_risks[student.id]['risk_factors'].append({
                        'type': 'homework',
                        'severity': 'critical',
                        'message': f'Не сдал {not_submitted_count} ДЗ за 2 недели',
                    })
                    student_risks[student.id]['recommendations'].append('Уточнить причину невыполнения ДЗ')
                elif not_submitted_count == 1 or late_count >= 2:
                    student_risks[student.id]['risk_score'] += 15
                    student_risks[student.id]['risk_factors'].append({
                        'type': 'homework',
                        'severity': 'warning',
                        'message': f'Проблемы со сдачей ДЗ ({not_submitted_count} не сдано, {late_count} просрочено)',
                    })
                    student_risks[student.id]['recommendations'].append('Обратить внимание на сдачу ДЗ')
                
                # 3. Оценки ниже порога (60%)
                recent_submissions = StudentSubmission.objects.filter(
                    homework_id__in=homework_ids,
                    homework__lesson__group=group,
                    student=student,
                    status='graded',
                    graded_at__gte=thirty_days_ago,
                    total_score__isnull=False,
                )
                
                below_threshold_count = 0
                for sub in recent_submissions[:5]:  # Последние 5 работ
                    max_score = sum(q.points for q in sub.homework.questions.all())
                    if max_score > 0:
                        percent = (sub.total_score / max_score) * 100
                        if percent < 60:
                            below_threshold_count += 1
                
                if below_threshold_count >= 2:
                    student_risks[student.id]['risk_score'] += 25
                    student_risks[student.id]['risk_factors'].append({
                        'type': 'grades',
                        'severity': 'warning',
                        'message': f'{below_threshold_count} работ ниже порога 60%',
                    })
                    student_risks[student.id]['recommendations'].append('Дать дополнительные материалы')
        
        # Фильтруем только учеников с риском
        at_risk_students = [
            s for s in student_risks.values()
            if s['risk_score'] > 0
        ]
        
        # Сортируем по риску (высокий сверху)
        at_risk_students.sort(key=lambda x: -x['risk_score'])
        
        # Определяем уровень риска
        for student in at_risk_students:
            score = student['risk_score']
            if score >= 50:
                student['risk_level'] = 'high'
            elif score >= 25:
                student['risk_level'] = 'medium'
            else:
                student['risk_level'] = 'low'
            
            # Убираем дубликаты рекомендаций
            student['recommendations'] = list(dict.fromkeys(student['recommendations']))
        
        return Response({
            'at_risk_count': len(at_risk_students),
            'high_risk_count': sum(1 for s in at_risk_students if s['risk_level'] == 'high'),
            'medium_risk_count': sum(1 for s in at_risk_students if s['risk_level'] == 'medium'),
            'students': at_risk_students[:20],  # Топ-20 рисковых
        })

    @action(detail=False, methods=['get'])
    def early_warnings(self, request):
        """Раннее предупреждение (7–14 дней вперёд) на базе последних 3–5 уроков.

        Минимальная версия без тяжелого ML:
        - Посещаемость по последним урокам
        - Просрочки/несдачи ДЗ по урокам
        - Падение "активности" через клики join (LessonJoinLog)

        Возвращает витрину "кого трогать" + "что делать".
        """
        user = request.user
        role = getattr(user, 'role', None)
        if role not in ('teacher', 'admin'):
            return Response({'detail': 'Только для преподавателей'}, status=403)

        from datetime import timedelta
        from django.db.models import Q
        from schedule.models import Group, Lesson, LessonJoinLog
        from accounts.models import AttendanceRecord
        from homework.models import Homework, StudentSubmission

        try:
            last_lessons = int(request.query_params.get('lessons', 5))
        except Exception:
            last_lessons = 5
        last_lessons = max(3, min(8, last_lessons))

        now = timezone.now()
        fourteen_days_ago = now - timedelta(days=14)

        groups = Group.objects.filter(teacher=user).prefetch_related('students')
        warnings = []

        for group in groups:
            lessons = list(
                Lesson.objects.filter(group=group, end_time__lt=now)
                .order_by('-end_time')[:last_lessons]
            )
            if not lessons:
                continue

            lesson_ids = [l.id for l in lessons]
            # ДЗ только по этим урокам
            homeworks = list(
                Homework.objects.filter(
                    teacher=user,
                    is_template=False,
                    lesson_id__in=lesson_ids,
                ).select_related('lesson')
            )
            homeworks_by_lesson = {}
            for hw in homeworks:
                homeworks_by_lesson.setdefault(hw.lesson_id, []).append(hw)

            for student in group.students.all():
                risk_score = 0
                factors = []
                actions = []

                # 1) Посещаемость: absences по последним урокам
                att = AttendanceRecord.objects.filter(
                    lesson_id__in=lesson_ids,
                    student=student,
                ).values_list('lesson_id', 'status')
                att_map = {lid: status for (lid, status) in att}

                absent_lessons = 0
                attended_lessons = 0
                unknown_lessons = 0
                for l in lessons:
                    st = att_map.get(l.id)
                    if st == AttendanceRecord.STATUS_ABSENT:
                        absent_lessons += 1
                    elif st in (AttendanceRecord.STATUS_ATTENDED, AttendanceRecord.STATUS_WATCHED_RECORDING):
                        attended_lessons += 1
                    else:
                        unknown_lessons += 1

                if absent_lessons >= 2:
                    risk_score += 35
                    factors.append({'type': 'attendance', 'severity': 'critical', 'message': f'Пропуски: {absent_lessons} из {len(lessons)} последних уроков'})
                    actions.append('Написать ученику и уточнить причину пропусков')
                    actions.append('Дать план догонки: запись + короткое задание')
                elif absent_lessons == 1 and unknown_lessons == 0:
                    risk_score += 15
                    factors.append({'type': 'attendance', 'severity': 'warning', 'message': 'Есть пропуск среди последних уроков'})
                    actions.append('Напомнить про следующий урок')

                # 2) ДЗ: несдачи/просрочки по урокам (последние 14 дней)
                hw_not_submitted = 0
                hw_late = 0
                relevant_homeworks = [hw for hw in homeworks if hw.deadline and hw.deadline >= fourteen_days_ago and hw.deadline <= now]
                for hw in relevant_homeworks:
                    sub = StudentSubmission.objects.filter(homework=hw, student=student).only('submitted_at').first()
                    if not sub or not sub.submitted_at:
                        hw_not_submitted += 1
                    elif hw.deadline and sub.submitted_at > hw.deadline:
                        hw_late += 1

                if hw_not_submitted >= 2:
                    risk_score += 30
                    factors.append({'type': 'homework', 'severity': 'critical', 'message': f'Не сдал {hw_not_submitted} ДЗ за 14 дней'})
                    actions.append('Уточнить причину невыполнения ДЗ')
                elif hw_not_submitted == 1 or hw_late >= 2:
                    risk_score += 15
                    factors.append({'type': 'homework', 'severity': 'warning', 'message': f'Проблемы с ДЗ (не сдано: {hw_not_submitted}, просрочено: {hw_late})'})

                # 3) Активность join: ученик вообще нажимает "Присоединиться"?
                joins = LessonJoinLog.objects.filter(
                    lesson_id__in=lesson_ids,
                    student=student,
                ).values_list('lesson_id', flat=True)
                join_set = set(joins)
                missing_joins = sum(1 for l in lessons[:3] if l.id not in join_set)  # последние 3 урока
                if missing_joins >= 2:
                    risk_score += 15
                    factors.append({'type': 'activity', 'severity': 'warning', 'message': 'Падает активность: редко нажимает «Присоединиться»'})
                    actions.append('Проверить, нет ли технических проблем со входом')

                # Итог
                if risk_score <= 0:
                    continue

                if risk_score >= 60:
                    level = 'high'
                elif risk_score >= 30:
                    level = 'medium'
                else:
                    level = 'low'

                # Убираем дубли рекомендаций
                actions = list(dict.fromkeys(actions))

                warnings.append({
                    'student_id': student.id,
                    'student_name': student.get_full_name(),
                    'student_email': student.email,
                    'group_id': group.id,
                    'group_name': group.name,
                    'risk_score': risk_score,
                    'risk_level': level,
                    'window_lessons': len(lessons),
                    'factors': factors,
                    'actions': actions,
                })

        warnings.sort(key=lambda x: -x['risk_score'])
        return Response({
            'window_lessons': last_lessons,
            'horizon_days': 14,
            'count': len(warnings),
            'high': sum(1 for w in warnings if w['risk_level'] == 'high'),
            'medium': sum(1 for w in warnings if w['risk_level'] == 'medium'),
            'students': warnings[:30],
        })


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

class StudentBehaviorReportViewSet(viewsets.ModelViewSet):
    """
    API для поведенческих AI-отчётов
    
    Анализирует:
    - Посещаемость (присутствие, пропуски, опоздания)
    - Сдачу ДЗ (вовремя, с опозданием, не сдано)  
    - Динамику оценок
    - Риск ухода ученика
    
    Endpoints:
    GET /api/analytics/behavior-reports/ - список отчётов
    GET /api/analytics/behavior-reports/{id}/ - детали отчёта
    POST /api/analytics/behavior-reports/generate/ - сгенерировать отчёт
    GET /api/analytics/behavior-reports/for-student/{student_id}/ - отчёты по студенту
    GET /api/analytics/behavior-reports/for-group/{group_id}/ - отчёты по группе
    """
    queryset = StudentBehaviorReport.objects.all().select_related('student', 'teacher', 'group')
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return StudentBehaviorReportListSerializer
        return StudentBehaviorReportSerializer
    
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
        
        risk_level = self.request.query_params.get('risk_level')
        if risk_level:
            qs = qs.filter(risk_level=risk_level)
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        
        return qs.order_by('-created_at')
    
    @action(detail=False, methods=['post'], url_path='generate')
    def generate_report(self, request):
        """
        Сгенерировать поведенческий отчёт
        
        POST /api/analytics/behavior-reports/generate/
        {
            "student_id": 123,
            "group_id": 456,  // опционально
            "period_days": 30  // опционально
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
        period_end = timezone.now().date()
        period_start = period_end - timezone.timedelta(days=period_days)
        
        # Генерируем отчёт
        from .ai_behavior_service import BehaviorAnalyticsService
        
        service = BehaviorAnalyticsService(
            provider=getattr(settings, 'AI_ANALYTICS_PROVIDER', 'deepseek')
        )
        
        report = service.generate_report(
            student=student,
            teacher=user,
            group=group,
            period_start=period_start,
            period_end=period_end
        )
        
        serializer = StudentBehaviorReportSerializer(report)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'], url_path='generate-for-group')
    def generate_for_group(self, request):
        """
        Сгенерировать отчёты для всех студентов группы
        
        POST /api/analytics/behavior-reports/generate-for-group/
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
        
        period_days = int(request.data.get('period_days', 30))
        period_end = timezone.now().date()
        period_start = period_end - timezone.timedelta(days=period_days)
        
        # Получаем студентов группы
        students = group.students.filter(role='student')
        
        from .ai_behavior_service import BehaviorAnalyticsService
        
        service = BehaviorAnalyticsService(
            provider=getattr(settings, 'AI_ANALYTICS_PROVIDER', 'deepseek')
        )
        
        reports = []
        for student in students:
            report = service.generate_report(
                student=student,
                teacher=user,
                group=group,
                period_start=period_start,
                period_end=period_end
            )
            reports.append(report)
        
        serializer = StudentBehaviorReportListSerializer(reports, many=True)
        return Response({
            'count': len(reports),
            'results': serializer.data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'], url_path='for-student/(?P<student_id>[^/.]+)')
    def for_student(self, request, student_id=None):
        """
        Получить все поведенческие отчёты по студенту
        
        GET /api/analytics/behavior-reports/for-student/{student_id}/
        """
        user = request.user
        if getattr(user, 'role', None) not in ['teacher', 'admin']:
            return Response(
                {'detail': 'Только для преподавателей'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        reports = self.get_queryset().filter(student_id=student_id)
        serializer = StudentBehaviorReportListSerializer(reports, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='for-group/(?P<group_id>[^/.]+)')
    def for_group(self, request, group_id=None):
        """
        Получить все поведенческие отчёты по группе
        
        GET /api/analytics/behavior-reports/for-group/{group_id}/
        """
        user = request.user
        if getattr(user, 'role', None) not in ['teacher', 'admin']:
            return Response(
                {'detail': 'Только для преподавателей'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        reports = self.get_queryset().filter(group_id=group_id)
        serializer = StudentBehaviorReportListSerializer(reports, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='at-risk')
    def at_risk_students(self, request):
        """
        Получить студентов с высоким риском
        
        GET /api/analytics/behavior-reports/at-risk/
        """
        user = request.user
        if getattr(user, 'role', None) not in ['teacher', 'admin']:
            return Response(
                {'detail': 'Только для преподавателей'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Последние отчёты с высоким/средним риском
        reports = self.get_queryset().filter(
            risk_level__in=['high', 'medium'],
            status='completed'
        ).order_by('risk_level', '-created_at')[:20]
        
        serializer = StudentBehaviorReportListSerializer(reports, many=True)
        return Response(serializer.data)


# =============================================================================
# РАСШИРЕННАЯ АНАЛИТИКА УЧЕНИКОВ
# =============================================================================

class ExtendedStudentAnalyticsViewSet(viewsets.ViewSet):
    """
    Расширенная аналитика ученика: когнитивный профиль, мотивация, социальная динамика
    
    Endpoints:
    GET /api/analytics/extended/student/{student_id}/ - полная аналитика ученика
    GET /api/analytics/extended/student/{student_id}/cognitive/ - когнитивный профиль
    GET /api/analytics/extended/student/{student_id}/errors/ - паттерны ошибок
    GET /api/analytics/extended/student/{student_id}/activity/ - хитмап активности
    GET /api/analytics/extended/group/{group_id}/social/ - социальная динамика группы
    GET /api/analytics/extended/group/{group_id}/rankings/ - рейтинг группы
    """
    permission_classes = [IsAuthenticated]
    
    def _check_teacher_access(self, request, *, student=None, group=None):
        """Разрешаем доступ только учителю к своим студентам/группам или админу."""
        role = getattr(request.user, 'role', None)
        if role not in ['teacher', 'admin']:
            return Response(
                {'detail': 'Только для преподавателей'},
                status=status.HTTP_403_FORBIDDEN
            )

        if role == 'admin':
            return None

        # Для учителя проверяем принадлежность группы и ученика
        if group and group.teacher_id != request.user.id:
            return Response({'detail': 'Нет доступа к этой группе'}, status=status.HTTP_403_FORBIDDEN)

        if student:
            owns_student = Group.objects.filter(teacher=request.user, students=student).exists()
            if not owns_student:
                return Response({'detail': 'Нет доступа к этому ученику'}, status=status.HTTP_403_FORBIDDEN)

        return None
    
    @action(detail=False, methods=['get'], url_path='student/(?P<student_id>[^/.]+)')
    def full_analytics(self, request, student_id=None):
        """
        Полная расширенная аналитика ученика
        
        GET /api/analytics/extended/student/{student_id}/?group_id=123&period_days=30
        """
        student = get_object_or_404(CustomUser, id=student_id, role='student')

        group_id = request.query_params.get('group_id')
        group = Group.objects.filter(id=group_id).first() if group_id else None

        error = self._check_teacher_access(request, student=student, group=group)
        if error:
            return error

        period_days = int(request.query_params.get('period_days', 30))
        
        from .extended_analytics_service import ExtendedAnalyticsService
        service = ExtendedAnalyticsService()
        analytics = service.collect_full_analytics(student, group, period_days)
        
        # Сериализуем dataclass
        from dataclasses import asdict
        data = asdict(analytics)
        
        # Конвертируем даты в строки
        data['period_start'] = str(analytics.period_start)
        data['period_end'] = str(analytics.period_end)
        
        return Response(data)
    
    @action(detail=False, methods=['get'], url_path='student/(?P<student_id>[^/.]+)/cognitive')
    def cognitive_profile(self, request, student_id=None):
        """
        Когнитивный профиль ученика
        
        GET /api/analytics/extended/student/{student_id}/cognitive/
        """
        student = get_object_or_404(CustomUser, id=student_id, role='student')

        group_id = request.query_params.get('group_id')
        group = Group.objects.filter(id=group_id).first() if group_id else None

        error = self._check_teacher_access(request, student=student, group=group)
        if error:
            return error

        from .extended_analytics_service import ExtendedAnalyticsService
        service = ExtendedAnalyticsService()
        analytics = service.collect_full_analytics(student, group, 30)
        
        from dataclasses import asdict
        return Response({
            'student_id': student_id,
            'student_name': analytics.student_name,
            'cognitive': asdict(analytics.cognitive),
            'energy': asdict(analytics.energy),
        })
    
    @action(detail=False, methods=['get'], url_path='student/(?P<student_id>[^/.]+)/errors')
    def error_patterns(self, request, student_id=None):
        """
        Паттерны ошибок по типам вопросов
        
        GET /api/analytics/extended/student/{student_id}/errors/
        """
        student = get_object_or_404(CustomUser, id=student_id, role='student')

        group_id = request.query_params.get('group_id')
        group = Group.objects.filter(id=group_id).first() if group_id else None

        error = self._check_teacher_access(request, student=student, group=group)
        if error:
            return error

        from .extended_analytics_service import ExtendedAnalyticsService
        service = ExtendedAnalyticsService()
        analytics = service.collect_full_analytics(student, group, 30)
        
        from dataclasses import asdict
        return Response({
            'student_id': student_id,
            'student_name': analytics.student_name,
            'error_patterns': [asdict(p) for p in analytics.error_patterns],
            'avg_score': analytics.avg_score,
            'score_trend': analytics.score_trend,
        })
    
    @action(detail=False, methods=['get'], url_path='student/(?P<student_id>[^/.]+)/activity')
    def activity_heatmap(self, request, student_id=None):
        """
        Хитмап активности ученика
        
        GET /api/analytics/extended/student/{student_id}/activity/
        """
        student = get_object_or_404(CustomUser, id=student_id, role='student')

        group_id = request.query_params.get('group_id')
        group = Group.objects.filter(id=group_id).first() if group_id else None

        error = self._check_teacher_access(request, student=student, group=group)
        if error:
            return error

        from .extended_analytics_service import ExtendedAnalyticsService
        service = ExtendedAnalyticsService()
        analytics = service.collect_full_analytics(student, group, 30)
        
        from dataclasses import asdict
        energy = asdict(analytics.energy)
        
        # Формируем удобный формат для фронтенда
        heatmap_data = []
        for day, hours in energy.get('activity_heatmap', {}).items():
            for hour, count in hours.items():
                heatmap_data.append({
                    'day': int(day),
                    'hour': int(hour),
                    'value': count,
                })
        
        return Response({
            'student_id': student_id,
            'student_name': analytics.student_name,
            'heatmap': heatmap_data,
            'optimal_hours': energy.get('optimal_hours', []),
            'best_days': energy.get('best_days', []),
            'fatigue_onset_minute': energy.get('fatigue_onset_minute'),
        })
    
    @action(detail=False, methods=['get'], url_path='group/(?P<group_id>[^/.]+)/social')
    def group_social_dynamics(self, request, group_id=None):
        """
        Социальная динамика группы: роли, влиятельность, взаимодействия
        
        GET /api/analytics/extended/group/{group_id}/social/
        """
        group = get_object_or_404(Group, id=group_id)

        error = self._check_teacher_access(request, group=group)
        if error:
            return error
        
        from datetime import timedelta
        
        period_end = timezone.now().date()
        period_start = period_end - timedelta(days=30)
        
        students_data = []
        roles_count = {}
        
        # Пытаемся получить агрегированную аналитику чатов
        try:
            from accounts.models import ChatAnalyticsSummary
            
            summaries = ChatAnalyticsSummary.objects.filter(
                group=group,
                period_end__gte=period_start
            ).select_related('student').order_by('-influence_score')
            
            for summary in summaries:
                students_data.append({
                    'student_id': summary.student_id,
                    'student_name': summary.student.get_full_name(),
                    'total_messages': summary.total_messages,
                    'questions_asked': summary.questions_asked,
                    'answers_given': summary.answers_given,
                    'helpful_messages': summary.helpful_messages,
                    'times_mentioned': summary.times_mentioned,
                    'influence_score': summary.influence_score,
                    'avg_sentiment': summary.avg_sentiment,
                    'detected_role': summary.detected_role,
                    'role_display': dict(ChatAnalyticsSummary.ROLE_CHOICES).get(summary.detected_role, ''),
                })
                
                role = summary.detected_role
                roles_count[role] = roles_count.get(role, 0) + 1
        except Exception:
            pass
        
        # Если нет данных ChatAnalytics, добавляем студентов с дефолтными значениями
        if not students_data:
            students = group.students.all()
            for student in students:
                students_data.append({
                    'student_id': student.id,
                    'student_name': student.get_full_name(),
                    'total_messages': 0,
                    'questions_asked': 0,
                    'answers_given': 0,
                    'helpful_messages': 0,
                    'times_mentioned': 0,
                    'influence_score': 0,
                    'avg_sentiment': None,
                    'detected_role': 'observer',
                    'role_display': 'Наблюдатель',
                })
                roles_count['observer'] = roles_count.get('observer', 0) + 1
        
        return Response({
            'group_id': group_id,
            'group_name': group.name,
            'period_start': str(period_start),
            'period_end': str(period_end),
            'students': students_data,
            'roles_distribution': roles_count,
            'total_students': len(students_data),
        })
    
    @action(detail=False, methods=['get'], url_path='group/(?P<group_id>[^/.]+)/rankings')
    def group_rankings(self, request, group_id=None):
        """
        Рейтинг учеников группы по разным метрикам
        
        GET /api/analytics/extended/group/{group_id}/rankings/
        """
        group = get_object_or_404(Group, id=group_id)

        error = self._check_teacher_access(request, group=group)
        if error:
            return error
        
        from homework.models import StudentSubmission
        from datetime import timedelta
        
        period_end = timezone.now().date()
        period_start = period_end - timedelta(days=30)
        
        # Получаем студентов группы
        students = CustomUser.objects.filter(
            group_students__id=group_id,
            role='student'
        ).distinct()
        
        rankings = []
        
        for student in students:
            # Баллы (используем среднюю оценку ДЗ * 10 как очки)
            avg_score = StudentSubmission.objects.filter(
                student=student,
                homework__lesson__group=group,
                status='graded',
            ).aggregate(avg=Avg('total_score'))['avg']
            
            total_points = int(avg_score * 10) if avg_score else 0
            
            # Посещаемость из модели Attendance (schedule.models)
            attendance_qs = Attendance.objects.filter(
                student=student,
                lesson__group=group,
                lesson__start_time__date__gte=period_start
            )
            total_lessons = attendance_qs.count()
            attended = attendance_qs.filter(status='present').count()
            attendance_rate = (attended / total_lessons * 100) if total_lessons else 0
            
            rankings.append({
                'student_id': student.id,
                'student_name': student.get_full_name(),
                'total_points': total_points,
                'attendance_rate': round(attendance_rate, 1),
                'avg_score': round(avg_score, 1) if avg_score else None,
            })
        
        # Сортируем по баллам
        rankings.sort(key=lambda x: x['total_points'], reverse=True)
        
        # Добавляем ранг
        for i, r in enumerate(rankings):
            r['rank'] = i + 1
        
        return Response({
            'group_id': group_id,
            'group_name': group.name,
            'rankings': rankings,
        })
    
    @action(detail=False, methods=['post'], url_path='recalculate-chat')
    def recalculate_chat_analytics(self, request):
        """
        Пересчитать чат-аналитику для группы
        
        POST /api/analytics/extended/recalculate-chat/
        {"group_id": 123}
        """
        group_id = request.data.get('group_id')
        if not group_id:
            return Response({'detail': 'group_id required'}, status=400)

        group = get_object_or_404(Group, id=group_id)

        error = self._check_teacher_access(request, group=group)
        if error:
            return error
        
        from .extended_analytics_service import recalculate_chat_analytics
        recalculate_chat_analytics(group, period_days=30)
        
        return Response({'status': 'ok', 'message': 'Chat analytics recalculated'})


class StudentQuestionViewSet(viewsets.ModelViewSet):
    """
    CRUD для вопросов учеников (для анализа качества вопросов)
    
    Endpoints:
    GET /api/analytics/student-questions/ - список вопросов
    POST /api/analytics/student-questions/ - создать вопрос
    GET /api/analytics/student-questions/stats/ - статистика по качеству
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        from homework.models import StudentQuestion
        user = self.request.user
        
        if user.role == 'teacher':
            return StudentQuestion.objects.filter(teacher=user)
        elif user.role == 'student':
            return StudentQuestion.objects.filter(student=user)
        elif user.role == 'admin':
            return StudentQuestion.objects.all()
        return StudentQuestion.objects.none()
    
    def get_serializer_class(self):
        from rest_framework import serializers
        from homework.models import StudentQuestion
        
        class StudentQuestionSerializer(serializers.ModelSerializer):
            student_name = serializers.CharField(source='student.get_full_name', read_only=True)
            quality_display = serializers.CharField(source='get_quality_display', read_only=True)
            
            class Meta:
                model = StudentQuestion
                fields = '__all__'
                read_only_fields = ['ai_quality_score', 'ai_classification']
        
        return StudentQuestionSerializer
    
    def perform_create(self, serializer):
        user = self.request.user
        if user.role == 'student':
            serializer.save(student=user)
        else:
            serializer.save()
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Статистика качества вопросов по ученикам
        
        GET /api/analytics/student-questions/stats/?group_id=123
        """
        from homework.models import StudentQuestion
        from django.db.models import Count
        
        if request.user.role not in ['teacher', 'admin']:
            return Response({'detail': 'Forbidden'}, status=403)
        
        group_id = request.query_params.get('group_id')
        
        qs = self.get_queryset()
        if group_id:
            qs = qs.filter(group_id=group_id)
        
        # Агрегируем по студентам
        stats = qs.values('student', 'student__first_name', 'student__last_name').annotate(
            total=Count('id'),
            procedural=Count('id', filter=Q(quality='procedural')),
            conceptual=Count('id', filter=Q(quality='conceptual')),
            clarification=Count('id', filter=Q(quality='clarification')),
        ).order_by('-conceptual')
        
        result = []
        for s in stats:
            name = f"{s['student__first_name']} {s['student__last_name']}".strip() or f"Student {s['student']}"
            quality_score = 0
            if s['total'] > 0:
                quality_score = (s['conceptual'] * 2 + s['procedural']) / (s['total'] * 2)
            
            result.append({
                'student_id': s['student'],
                'student_name': name,
                'total_questions': s['total'],
                'procedural': s['procedural'],
                'conceptual': s['conceptual'],
                'clarification': s['clarification'],
                'quality_score': round(quality_score, 2),
            })
        
        return Response(result)


# =============================================================================
# ДЕТАЛЬНАЯ АНАЛИТИКА УЧЕНИКА (для страницы ученика в аналитике)
# =============================================================================

class StudentDetailAnalyticsViewSet(viewsets.ViewSet):
    """
    Детальная аналитика конкретного ученика для преподавателя.
    
    Включает:
    - Посещаемость по занятиям (на каких был, на каких нет)
    - Участие на уроках (упоминания из транскрипции, время речи)
    - Статус ДЗ (какие сдал, какие нет)
    - Сводную статистику
    
    Endpoints:
    GET /api/analytics/student-detail/{student_id}/ - сводка
    GET /api/analytics/student-detail/{student_id}/attendance/ - детали посещаемости
    GET /api/analytics/student-detail/{student_id}/participation/ - участие на уроках
    GET /api/analytics/student-detail/{student_id}/homework/ - статус ДЗ
    """
    permission_classes = [IsAuthenticated]
    
    def _check_access(self, request, student_id, group_id=None):
        """Проверка доступа: только учитель или админ"""
        user = request.user
        if user.role not in ['teacher', 'admin']:
            return None, Response({'detail': 'Только для преподавателей'}, status=403)
        
        student = get_object_or_404(CustomUser, id=student_id, role='student')
        
        group = None
        if group_id:
            group = Group.objects.filter(id=group_id).first()
            # Проверяем что учитель владеет группой
            if group and user.role == 'teacher' and group.teacher != user:
                return None, Response({'detail': 'Нет доступа к этой группе'}, status=403)
        
        return (student, group), None
    
    @action(detail=False, methods=['get'], url_path='(?P<student_id>[^/.]+)')
    def summary(self, request, student_id=None):
        """
        Сводная информация по ученику
        
        GET /api/analytics/student-detail/{student_id}/?group_id=123
        """
        group_id = request.query_params.get('group_id')
        result, error = self._check_access(request, student_id, group_id)
        if error:
            return error
        student, group = result
        
        from schedule.models import Lesson
        from datetime import timedelta
        
        # Определяем группы для анализа
        if group:
            groups = [group]
        else:
            # Все группы ученика, принадлежащие учителю
            if request.user.role == 'teacher':
                groups = list(Group.objects.filter(teacher=request.user, students=student))
            else:
                groups = list(Group.objects.filter(students=student))
        
        if not groups:
            return Response({
                'student_id': student.id,
                'student_name': student.get_full_name(),
                'email': student.email,
                'groups': [],
                'attendance': {'present': 0, 'absent': 0, 'excused': 0, 'percent': None},
                'homework': {'completed': 0, 'pending': 0, 'percent': None},
                'participation': {'mentions': 0, 'talk_time_seconds': 0},
            })
        
        # === ПОСЕЩАЕМОСТЬ ===
        attendance_qs = Attendance.objects.filter(
            student=student,
            lesson__group__in=groups
        )
        present = attendance_qs.filter(status='present').count()
        absent = attendance_qs.filter(status='absent').count()
        excused = attendance_qs.filter(status='excused').count()
        total_marked = present + absent + excused
        attendance_percent = round((present / total_marked) * 100, 1) if total_marked else None
        
        # === ДОМАШНИЕ ЗАДАНИЯ ===
        from homework.models import Homework, StudentSubmission
        
        homework_qs = Homework.objects.filter(
            status='published',
            lesson__group__in=groups
        )
        total_hw = homework_qs.count()
        
        completed_submissions = StudentSubmission.objects.filter(
            student=student,
            homework__in=homework_qs,
            status__in=['submitted', 'graded']
        ).count()
        
        pending_hw = total_hw - completed_submissions
        hw_percent = round((completed_submissions / total_hw) * 100, 1) if total_hw else None
        
        # === УЧАСТИЕ НА УРОКАХ (из транскрипции) ===
        total_mentions = 0
        total_talk_time = 0
        
        # Ищем упоминания студента в stats_json
        stats_qs = LessonTranscriptStats.objects.filter(
            lesson__group__in=groups
        ).select_related('lesson')
        
        student_name = student.get_full_name().lower()
        student_first_name = (student.first_name or '').lower()
        
        for stats in stats_qs:
            data = stats.stats_json
            
            # Упоминания
            mentions = data.get('mentions', [])
            if isinstance(mentions, list):
                for m in mentions:
                    if m.get('student_id') == student.id:
                        total_mentions += m.get('count', 0)
            elif isinstance(mentions, dict):
                # Старый формат: {'Name': count}
                for name, count in mentions.items():
                    if student_first_name and student_first_name in name.lower():
                        total_mentions += count
            
            # Время речи
            talk_times = data.get('clean_talk_time', {})
            for name, seconds in talk_times.items():
                if student_first_name and student_first_name in name.lower():
                    total_talk_time += seconds
        
        return Response({
            'student_id': student.id,
            'student_name': student.get_full_name(),
            'email': student.email,
            'groups': [{'id': g.id, 'name': g.name} for g in groups],
            'attendance': {
                'present': present,
                'absent': absent,
                'excused': excused,
                'total': total_marked,
                'percent': attendance_percent,
            },
            'homework': {
                'completed': completed_submissions,
                'pending': pending_hw,
                'total': total_hw,
                'percent': hw_percent,
            },
            'participation': {
                'mentions': total_mentions,
                'talk_time_seconds': total_talk_time,
                'talk_time_minutes': round(total_talk_time / 60, 1) if total_talk_time else 0,
            },
        })
    
    @action(detail=False, methods=['get'], url_path='(?P<student_id>[^/.]+)/attendance')
    def attendance_detail(self, request, student_id=None):
        """
        Детальная посещаемость ученика по занятиям
        
        GET /api/analytics/student-detail/{student_id}/attendance/?group_id=123
        """
        group_id = request.query_params.get('group_id')
        result, error = self._check_access(request, student_id, group_id)
        if error:
            return error
        student, group = result
        
        from schedule.models import Lesson
        
        # Определяем группы
        if group:
            groups = [group]
        else:
            if request.user.role == 'teacher':
                groups = list(Group.objects.filter(teacher=request.user, students=student))
            else:
                groups = list(Group.objects.filter(students=student))
        
        if not groups:
            return Response({'lessons': []})
        
        # Получаем все уроки этих групп (прошедшие)
        lessons = Lesson.objects.filter(
            group__in=groups,
            start_time__lt=timezone.now()
        ).select_related('group').order_by('-start_time')[:50]
        
        # Получаем посещаемость ученика
        attendance_map = {}
        for att in Attendance.objects.filter(student=student, lesson__in=lessons):
            attendance_map[att.lesson_id] = {
                'status': att.status,
                'status_display': att.get_status_display(),
                'notes': att.notes,
            }
        
        result = []
        for lesson in lessons:
            att = attendance_map.get(lesson.id, {})
            result.append({
                'lesson_id': lesson.id,
                'title': lesson.title or 'Занятие',
                'date': lesson.start_time.strftime('%d.%m.%Y'),
                'time': lesson.start_time.strftime('%H:%M'),
                'group_id': lesson.group_id,
                'group_name': lesson.group.name if lesson.group else '',
                'status': att.get('status', 'not_marked'),
                'status_display': att.get('status_display', 'Не отмечено'),
                'notes': att.get('notes', ''),
            })
        
        return Response({
            'student_id': student.id,
            'student_name': student.get_full_name(),
            'lessons': result,
        })
    
    @action(detail=False, methods=['get'], url_path='(?P<student_id>[^/.]+)/participation')
    def participation_detail(self, request, student_id=None):
        """
        Участие ученика на уроках (из транскрипции)
        
        GET /api/analytics/student-detail/{student_id}/participation/?group_id=123
        """
        group_id = request.query_params.get('group_id')
        result, error = self._check_access(request, student_id, group_id)
        if error:
            return error
        student, group = result
        
        from schedule.models import Lesson
        
        # Определяем группы
        if group:
            groups = [group]
        else:
            if request.user.role == 'teacher':
                groups = list(Group.objects.filter(teacher=request.user, students=student))
            else:
                groups = list(Group.objects.filter(students=student))
        
        if not groups:
            return Response({'lessons': []})
        
        # Получаем статистику транскриптов
        stats_qs = LessonTranscriptStats.objects.filter(
            lesson__group__in=groups
        ).select_related('lesson', 'lesson__group').order_by('-lesson__start_time')[:50]
        
        student_first_name = (student.first_name or '').lower()
        
        result = []
        total_mentions = 0
        total_talk_time = 0
        
        for stats in stats_qs:
            data = stats.stats_json
            lesson = stats.lesson
            
            # Считаем упоминания для этого ученика
            mentions_count = 0
            mentions = data.get('mentions', [])
            if isinstance(mentions, list):
                for m in mentions:
                    if m.get('student_id') == student.id:
                        mentions_count = m.get('count', 0)
                        break
            elif isinstance(mentions, dict):
                for name, count in mentions.items():
                    if student_first_name and student_first_name in name.lower():
                        mentions_count = count
                        break
            
            # Время речи
            talk_time = 0
            talk_times = data.get('clean_talk_time', {})
            for name, seconds in talk_times.items():
                if student_first_name and student_first_name in name.lower():
                    talk_time = seconds
                    break
            
            # Speakers list (для отображения участия)
            speakers = data.get('speakers', [])
            student_talked = any(
                student_first_name and student_first_name in (s.get('name', '').lower())
                for s in speakers if isinstance(s, dict)
            )
            
            total_mentions += mentions_count
            total_talk_time += talk_time
            
            result.append({
                'lesson_id': lesson.id,
                'title': lesson.title or 'Занятие',
                'date': lesson.start_time.strftime('%d.%m.%Y'),
                'group_id': lesson.group_id,
                'group_name': lesson.group.name if lesson.group else '',
                'mentions_count': mentions_count,
                'talk_time_seconds': talk_time,
                'talk_time_minutes': round(talk_time / 60, 1) if talk_time else 0,
                'participated': mentions_count > 0 or talk_time > 0 or student_talked,
            })
        
        return Response({
            'student_id': student.id,
            'student_name': student.get_full_name(),
            'total_mentions': total_mentions,
            'total_talk_time_seconds': total_talk_time,
            'total_talk_time_minutes': round(total_talk_time / 60, 1) if total_talk_time else 0,
            'lessons': result,
        })
    
    @action(detail=False, methods=['get'], url_path='(?P<student_id>[^/.]+)/homework')
    def homework_detail(self, request, student_id=None):
        """
        Статус ДЗ ученика с детальной аналитикой ошибок и времени
        
        GET /api/analytics/student-detail/{student_id}/homework/?group_id=123
        
        Возвращает:
        - homeworks: список ДЗ с детальной информацией
        - stats: сводная статистика (ошибки, время, дедлайны)
        """
        group_id = request.query_params.get('group_id')
        result, error = self._check_access(request, student_id, group_id)
        if error:
            return error
        student, group = result
        
        from homework.models import Homework, StudentSubmission, Answer
        
        # Определяем группы
        if group:
            groups = [group]
        else:
            if request.user.role == 'teacher':
                groups = list(Group.objects.filter(teacher=request.user, students=student))
            else:
                groups = list(Group.objects.filter(students=student))
        
        if not groups:
            return Response({
                'homeworks': [],
                'stats': {
                    'total_hw': 0,
                    'completed': 0,
                    'on_time': 0,
                    'late': 0,
                    'total_correct': 0,
                    'total_incorrect': 0,
                    'error_rate': None,
                    'avg_time_minutes': None,
                }
            })
        
        # Все опубликованные ДЗ
        homework_qs = Homework.objects.filter(
            status='published',
            lesson__group__in=groups
        ).select_related('lesson', 'lesson__group').order_by('-created_at')[:50]
        
        # Сабмишены ученика с ответами
        submissions = StudentSubmission.objects.filter(
            student=student,
            homework__in=homework_qs
        ).select_related('homework').prefetch_related('answers', 'answers__question')
        
        submission_map = {}
        for sub in submissions:
            # Считаем ошибки и время для этого сабмишена
            answers = list(sub.answers.all())
            correct_count = 0
            incorrect_count = 0
            total_time_seconds = 0
            
            for ans in answers:
                # Определяем итоговый балл
                score = ans.teacher_score if ans.teacher_score is not None else ans.auto_score
                max_points = ans.question.points if ans.question else 1
                
                if score is not None:
                    if score >= max_points:
                        correct_count += 1
                    else:
                        incorrect_count += 1
                
                # Время
                if ans.time_spent_seconds:
                    total_time_seconds += ans.time_spent_seconds
            
            # Проверяем сдачу в срок
            on_time = True
            if sub.homework.deadline and sub.submitted_at:
                on_time = sub.submitted_at <= sub.homework.deadline
            
            submission_map[sub.homework_id] = {
                'id': sub.id,
                'status': sub.status,
                'status_display': dict(StudentSubmission.STATUS_CHOICES).get(sub.status, sub.status),
                'total_score': sub.total_score,
                'submitted_at': sub.submitted_at,
                'graded_at': sub.graded_at,
                'correct_count': correct_count,
                'incorrect_count': incorrect_count,
                'total_answers': len(answers),
                'time_spent_seconds': total_time_seconds,
                'on_time': on_time,
            }
        
        # Агрегируем статистику
        total_correct = 0
        total_incorrect = 0
        total_time_seconds = 0
        completed_count = 0
        on_time_count = 0
        late_count = 0
        time_data_count = 0
        
        result = []
        for hw in homework_qs:
            sub = submission_map.get(hw.id)
            
            # Определяем статус
            if sub:
                hw_status = sub['status']
                hw_status_display = sub['status_display']
                
                if hw_status in ['submitted', 'graded']:
                    completed_count += 1
                    if sub['on_time']:
                        on_time_count += 1
                    else:
                        late_count += 1
                
                total_correct += sub['correct_count']
                total_incorrect += sub['incorrect_count']
                
                if sub['time_spent_seconds'] > 0:
                    total_time_seconds += sub['time_spent_seconds']
                    time_data_count += 1
            else:
                hw_status = 'not_started'
                hw_status_display = 'Не начато'
            
            # Проверяем просрочку
            is_overdue = False
            if hw.deadline and hw_status in ['not_started', 'in_progress']:
                is_overdue = timezone.now() > hw.deadline
            
            # Процент правильных для этого ДЗ
            hw_correct_rate = None
            if sub and sub['total_answers'] > 0:
                hw_correct_rate = round((sub['correct_count'] / sub['total_answers']) * 100, 1)
            
            result.append({
                'homework_id': hw.id,
                'title': hw.title,
                'lesson_id': hw.lesson_id,
                'lesson_title': hw.lesson.title if hw.lesson else '',
                'group_id': hw.lesson.group_id if hw.lesson else None,
                'group_name': hw.lesson.group.name if hw.lesson and hw.lesson.group else '',
                'created_at': hw.created_at.strftime('%d.%m.%Y'),
                'deadline': hw.deadline.strftime('%d.%m.%Y %H:%M') if hw.deadline else None,
                'status': hw_status,
                'status_display': hw_status_display,
                'is_overdue': is_overdue,
                'total_score': sub['total_score'] if sub else None,
                'submitted_at': sub['submitted_at'].strftime('%d.%m.%Y %H:%M') if sub and sub['submitted_at'] else None,
                'graded_at': sub['graded_at'].strftime('%d.%m.%Y %H:%M') if sub and sub['graded_at'] else None,
                # Новые поля
                'correct_count': sub['correct_count'] if sub else 0,
                'incorrect_count': sub['incorrect_count'] if sub else 0,
                'total_answers': sub['total_answers'] if sub else 0,
                'correct_rate': hw_correct_rate,
                'time_spent_seconds': sub['time_spent_seconds'] if sub else 0,
                'time_spent_minutes': round(sub['time_spent_seconds'] / 60, 1) if sub and sub['time_spent_seconds'] else 0,
                'on_time': sub['on_time'] if sub else None,
            })
        
        # Общая статистика
        total_answers = total_correct + total_incorrect
        error_rate = round((total_incorrect / total_answers) * 100, 1) if total_answers > 0 else None
        avg_time_minutes = round((total_time_seconds / time_data_count) / 60, 1) if time_data_count > 0 else None
        
        return Response({
            'student_id': student.id,
            'student_name': student.get_full_name(),
            'homeworks': result,
            'stats': {
                'total_hw': len(homework_qs),
                'completed': completed_count,
                'on_time': on_time_count,
                'late': late_count,
                'total_correct': total_correct,
                'total_incorrect': total_incorrect,
                'error_rate': error_rate,
                'avg_time_minutes': avg_time_minutes,
            }
        })


class GroupDetailAnalyticsViewSet(viewsets.ViewSet):
    """
    Детальная аналитика группы для преподавателя.
    
    Включает:
    - Общая посещаемость группы
    - Общий процент выполнения ДЗ
    - Общий процент ошибок в ДЗ
    - Список учеников с их метриками
    
    Endpoints:
    GET /api/analytics/group-detail/{group_id}/ - сводка группы
    GET /api/analytics/group-detail/{group_id}/homework/ - детали по ДЗ
    GET /api/analytics/group-detail/{group_id}/students/ - студенты с метриками
    """
    permission_classes = [IsAuthenticated]
    
    def _check_access(self, request, group_id):
        """Проверка доступа: только учитель группы или админ"""
        user = request.user
        if user.role not in ['teacher', 'admin']:
            return None, Response({'detail': 'Только для преподавателей'}, status=403)
        
        group = get_object_or_404(Group, id=group_id)
        
        # Проверяем что учитель владеет группой
        if user.role == 'teacher' and group.teacher != user:
            return None, Response({'detail': 'Нет доступа к этой группе'}, status=403)
        
        return group, None
    
    @action(detail=False, methods=['get'], url_path='(?P<group_id>[^/.]+)')
    def summary(self, request, group_id=None):
        """
        Сводная аналитика группы
        
        GET /api/analytics/group-detail/{group_id}/
        """
        group, error = self._check_access(request, group_id)
        if error:
            return error
        
        from homework.models import Homework, StudentSubmission, Answer
        from schedule.models import Lesson
        
        students = list(group.students.all())
        student_count = len(students)
        
        if student_count == 0:
            return Response({
                'group_id': group.id,
                'group_name': group.name,
                'students_count': 0,
                'attendance': {'present': 0, 'total': 0, 'percent': None},
                'homework': {'completed': 0, 'total': 0, 'percent': None},
                'errors': {'total_correct': 0, 'total_incorrect': 0, 'error_rate': None},
            })
        
        # === ПОСЕЩАЕМОСТЬ ===
        attendance_qs = Attendance.objects.filter(lesson__group=group)
        present = attendance_qs.filter(status='present').count()
        total_marked = attendance_qs.exclude(status__isnull=True).count()
        attendance_percent = round((present / total_marked) * 100, 1) if total_marked else None
        
        # === ДОМАШНИЕ ЗАДАНИЯ ===
        homework_qs = Homework.objects.filter(
            status='published',
            lesson__group=group
        )
        total_hw = homework_qs.count()
        
        # Всего возможных сдач = ДЗ × студентов
        total_possible = total_hw * student_count
        
        # Завершенные сабмишены
        completed_submissions = StudentSubmission.objects.filter(
            homework__in=homework_qs,
            status__in=['submitted', 'graded']
        ).count()
        
        hw_percent = round((completed_submissions / total_possible) * 100, 1) if total_possible else None
        
        # === ОШИБКИ ===
        # Если в группе нет опубликованных ДЗ, не трогаем таблицу Answer.
        total_correct = 0
        total_incorrect = 0
        if total_hw:
            # Считаем по всем ответам в группе
            answers_qs = Answer.objects.filter(
                submission__homework__in=homework_qs
            ).select_related('question')

            for ans in answers_qs:
                score = ans.teacher_score if ans.teacher_score is not None else ans.auto_score
                if score is not None:
                    max_points = ans.question.points if ans.question else 1
                    if score >= max_points:
                        total_correct += 1
                    else:
                        total_incorrect += 1

        total_answers = total_correct + total_incorrect
        error_rate = round((total_incorrect / total_answers) * 100, 1) if total_answers > 0 else None
        
        return Response({
            'group_id': group.id,
            'group_name': group.name,
            'teacher_name': group.teacher.get_full_name() if group.teacher else '',
            'students_count': student_count,
            'attendance': {
                'present': present,
                'total': total_marked,
                'percent': attendance_percent,
            },
            'homework': {
                'completed': completed_submissions,
                'total': total_possible,
                'percent': hw_percent,
                'hw_count': total_hw,
            },
            'errors': {
                'total_correct': total_correct,
                'total_incorrect': total_incorrect,
                'total_answers': total_answers,
                'error_rate': error_rate,
            },
        })
    
    @action(detail=False, methods=['get'], url_path='(?P<group_id>[^/.]+)/homework')
    def homework_detail(self, request, group_id=None):
        """
        Детальная аналитика по ДЗ группы
        
        GET /api/analytics/group-detail/{group_id}/homework/
        """
        group, error = self._check_access(request, group_id)
        if error:
            return error
        
        from homework.models import Homework, StudentSubmission, Answer
        
        students = list(group.students.all())
        student_count = len(students)
        
        homework_qs = Homework.objects.filter(
            status='published',
            lesson__group=group
        ).select_related('lesson').order_by('-created_at')[:30]
        
        result = []
        for hw in homework_qs:
            # Сабмишены для этого ДЗ
            submissions = StudentSubmission.objects.filter(homework=hw)
            submitted_count = submissions.filter(status__in=['submitted', 'graded']).count()
            
            # Ответы для этого ДЗ
            answers = Answer.objects.filter(submission__homework=hw).select_related('question')
            
            correct = 0
            incorrect = 0
            total_time = 0
            time_count = 0
            
            for ans in answers:
                score = ans.teacher_score if ans.teacher_score is not None else ans.auto_score
                if score is not None:
                    max_points = ans.question.points if ans.question else 1
                    if score >= max_points:
                        correct += 1
                    else:
                        incorrect += 1
                
                if ans.time_spent_seconds:
                    total_time += ans.time_spent_seconds
                    time_count += 1
            
            total_ans = correct + incorrect
            error_rate = round((incorrect / total_ans) * 100, 1) if total_ans > 0 else None
            avg_time = round((total_time / time_count) / 60, 1) if time_count > 0 else None
            
            result.append({
                'homework_id': hw.id,
                'title': hw.title,
                'created_at': hw.created_at.strftime('%d.%m.%Y'),
                'deadline': hw.deadline.strftime('%d.%m.%Y %H:%M') if hw.deadline else None,
                'submitted_count': submitted_count,
                'students_count': student_count,
                'submission_rate': round((submitted_count / student_count) * 100, 1) if student_count else None,
                'correct_count': correct,
                'incorrect_count': incorrect,
                'error_rate': error_rate,
                'avg_time_minutes': avg_time,
            })
        
        return Response({
            'group_id': group.id,
            'group_name': group.name,
            'homeworks': result,
        })
    
    @action(detail=False, methods=['get'], url_path='(?P<group_id>[^/.]+)/students')
    def students_detail(self, request, group_id=None):
        """
        Список студентов группы с их метриками
        
        GET /api/analytics/group-detail/{group_id}/students/
        """
        group, error = self._check_access(request, group_id)
        if error:
            return error
        
        from homework.models import Homework, StudentSubmission, Answer
        
        students = list(group.students.all())
        
        homework_qs = Homework.objects.filter(
            status='published',
            lesson__group=group
        )
        total_hw = homework_qs.count()
        
        result = []
        for student in students:
            # Посещаемость
            att_qs = Attendance.objects.filter(student=student, lesson__group=group)
            present = att_qs.filter(status='present').count()
            total_marked = att_qs.exclude(status__isnull=True).count()
            att_percent = round((present / total_marked) * 100, 1) if total_marked else None
            
            # ДЗ
            submissions = StudentSubmission.objects.filter(
                student=student,
                homework__in=homework_qs
            )
            completed = submissions.filter(status__in=['submitted', 'graded']).count()
            hw_percent = round((completed / total_hw) * 100, 1) if total_hw else None
            
            correct = 0
            incorrect = 0
            if total_hw:
                # Ошибки
                answers = Answer.objects.filter(
                    submission__student=student,
                    submission__homework__in=homework_qs
                ).select_related('question')

                for ans in answers:
                    score = ans.teacher_score if ans.teacher_score is not None else ans.auto_score
                    if score is not None:
                        max_points = ans.question.points if ans.question else 1
                        if score >= max_points:
                            correct += 1
                        else:
                            incorrect += 1
            
            total_ans = correct + incorrect
            error_rate = round((incorrect / total_ans) * 100, 1) if total_ans > 0 else None
            
            result.append({
                'student_id': student.id,
                'student_name': student.get_full_name(),
                'email': student.email,
                'attendance_percent': att_percent,
                'attendance_present': present,
                'attendance_total': total_marked,
                'homework_percent': hw_percent,
                'homework_completed': completed,
                'homework_total': total_hw,
                'correct_count': correct,
                'incorrect_count': incorrect,
                'error_rate': error_rate,
            })
        
        return Response({
            'group_id': group.id,
            'group_name': group.name,
            'students': result,
        })
