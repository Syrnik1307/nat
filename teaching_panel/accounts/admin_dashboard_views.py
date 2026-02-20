"""
Admin Dashboard API — метрики для владельца/администратора школы.

Эндпоинты:
  GET /accounts/api/admin/dashboard/student-risks/   — ученики с рисками ухода
  GET /accounts/api/admin/dashboard/teacher-quality/  — качество работы учителей
  GET /accounts/api/admin/dashboard/overview/          — сводная панель
"""

from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db.models import (
    Avg, Count, Q, F, Max, Min, Sum,
    Case, When, Value, IntegerField, FloatField,
    Subquery, OuterRef, ExpressionWrapper, DurationField,
)
from django.db.models.functions import Now, Coalesce
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


def _tenant_user_qs(request, base_qs=None):
    """Фильтрует queryset пользователей по текущему тенанту."""
    if base_qs is None:
        base_qs = User.objects.all()
    tenant = getattr(request, 'tenant', None)
    if tenant:
        from tenants.models import TenantMembership
        tenant_user_ids = TenantMembership.objects.filter(
            tenant=tenant, is_active=True
        ).values_list('user_id', flat=True)
        return base_qs.filter(id__in=tenant_user_ids)
    return base_qs


def _tenant_teacher_ids(request):
    """Возвращает ID учителей текущего тенанта."""
    return list(_tenant_user_qs(request).filter(role='teacher').values_list('id', flat=True))


def _require_admin(request):
    """Возвращает Response(403) если пользователь не admin, иначе None."""
    if getattr(request.user, 'role', None) != 'admin':
        return Response({'error': 'Доступ запрещен'}, status=status.HTTP_403_FORBIDDEN)
    return None


# ──────────────────────────────────────────────
#  1. Ученики с рисками
# ──────────────────────────────────────────────

class AdminStudentRisksView(APIView):
    """
    Ученики, которые могут уйти.

    Критерии риска:
    1. Пропустил ≥2 урока подряд (absent без excused после)
    2. Не заходил в систему >7 дней
    3. Не сдал ≥2 домашки (status != graded/submitted)
    4. Средний балл ДЗ упал >20% за последний месяц vs предыдущий
    5. Баланс ≤2 урока (из finance)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        denied = _require_admin(request)
        if denied:
            return denied

        now = timezone.now()
        students = _tenant_user_qs(request).filter(role='student', is_active=True)

        from schedule.models import Attendance, Lesson
        from homework.models import StudentSubmission, Homework
        from finance.models import StudentFinancialProfile

        risks = []

        for student in students.select_related().iterator():
            student_risks = []
            risk_score = 0  # чем больше — тем хуже

            # ── 1. Пропуски подряд ──
            recent_attendance = (
                Attendance.objects
                .filter(student=student)
                .select_related('lesson')
                .order_by('-lesson__start_time')[:10]
            )
            consecutive_absent = 0
            for att in recent_attendance:
                if att.status == 'absent':
                    consecutive_absent += 1
                else:
                    break
            if consecutive_absent >= 2:
                student_risks.append({
                    'type': 'consecutive_absences',
                    'label': f'Пропустил {consecutive_absent} уроков подряд',
                    'severity': 'high' if consecutive_absent >= 3 else 'medium',
                    'value': consecutive_absent,
                })
                risk_score += consecutive_absent * 2

            # ── 2. Давно не заходил ──
            if student.last_login:
                days_inactive = (now - student.last_login).days
                if days_inactive >= 7:
                    sev = 'high' if days_inactive >= 14 else 'medium'
                    student_risks.append({
                        'type': 'inactive',
                        'label': f'Не заходил {days_inactive} дней',
                        'severity': sev,
                        'value': days_inactive,
                    })
                    risk_score += min(days_inactive, 30)
            else:
                student_risks.append({
                    'type': 'inactive',
                    'label': 'Никогда не входил в систему',
                    'severity': 'high',
                    'value': None,
                })
                risk_score += 20

            # ── 3. Несданные ДЗ ──
            # ДЗ за последние 30 дней, которые ученик должен был сдать
            month_ago = now - timedelta(days=30)
            # Все ДЗ в группах ученика за последний месяц
            student_groups = student.enrolled_groups.all()
            available_hw = Homework.objects.filter(
                lesson__group__in=student_groups,
                created_at__gte=month_ago,
            )
            total_hw = available_hw.count()
            submitted_hw = StudentSubmission.objects.filter(
                student=student,
                homework__in=available_hw,
                status__in=['submitted', 'graded'],
            ).count()
            missing_hw = total_hw - submitted_hw
            if missing_hw >= 2:
                student_risks.append({
                    'type': 'missing_homework',
                    'label': f'Не сдал {missing_hw} из {total_hw} ДЗ за месяц',
                    'severity': 'high' if missing_hw >= 4 else 'medium',
                    'value': missing_hw,
                })
                risk_score += missing_hw * 2

            # ── 4. Падение оценок ──
            two_months_ago = now - timedelta(days=60)
            prev_avg = StudentSubmission.objects.filter(
                student=student,
                status='graded',
                graded_at__gte=two_months_ago,
                graded_at__lt=month_ago,
                total_score__isnull=False,
            ).aggregate(avg=Avg('total_score'))['avg']
            curr_avg = StudentSubmission.objects.filter(
                student=student,
                status='graded',
                graded_at__gte=month_ago,
                total_score__isnull=False,
            ).aggregate(avg=Avg('total_score'))['avg']
            if prev_avg and curr_avg and prev_avg > 0:
                drop_pct = round(((prev_avg - curr_avg) / prev_avg) * 100, 1)
                if drop_pct >= 20:
                    student_risks.append({
                        'type': 'grade_drop',
                        'label': f'Средний балл упал на {drop_pct}%',
                        'severity': 'high' if drop_pct >= 40 else 'medium',
                        'value': drop_pct,
                    })
                    risk_score += int(drop_pct / 5)

            # ── 5. Баланс ≤2 урока ──
            wallets = StudentFinancialProfile.objects.filter(student=student)
            for wallet in wallets:
                if wallet.default_lesson_price and wallet.default_lesson_price > 0:
                    lessons_left = int(wallet.balance / wallet.default_lesson_price)
                    if lessons_left <= 2:
                        student_risks.append({
                            'type': 'low_balance',
                            'label': f'Осталось {lessons_left} урок(ов) у {wallet.teacher.get_full_name()}',
                            'severity': 'high' if lessons_left <= 0 else 'medium',
                            'value': lessons_left,
                        })
                        risk_score += max(0, 3 - lessons_left) * 3

            if student_risks:
                risks.append({
                    'student_id': student.id,
                    'student_name': student.get_full_name(),
                    'student_email': student.email,
                    'risk_score': risk_score,
                    'risks': student_risks,
                })

        # Сортируем по risk_score — самые проблемные сверху
        risks.sort(key=lambda x: x['risk_score'], reverse=True)

        return Response({
            'total_students': students.count(),
            'at_risk': len(risks),
            'students': risks,
        })


# ──────────────────────────────────────────────
#  2. Качество работы учителей
# ──────────────────────────────────────────────

class AdminTeacherQualityView(APIView):
    """
    Метрики качества для каждого учителя:
    1. % проведённых уроков (без отмен)
    2. Пунктуальность запуска уроков (вовремя ли стартует)
    3. Скорость проверки ДЗ (среднее время graded_at - submitted_at)
    4. Посещаемость учеников (агрегат)
    5. Непроверенные ДЗ (висящие >3 дней)
    6. Нагрузка (уроков в неделю, учеников)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        denied = _require_admin(request)
        if denied:
            return denied

        now = timezone.now()
        month_ago = now - timedelta(days=30)
        week_ago = now - timedelta(days=7)
        teachers = _tenant_user_qs(request).filter(role='teacher', is_active=True)

        from schedule.models import Lesson, Attendance, Group, AuditLog
        from homework.models import StudentSubmission

        teacher_data = []

        for teacher in teachers.iterator():
            # ── Уроки за месяц ──
            lessons_month = Lesson.objects.filter(
                teacher=teacher,
                start_time__gte=month_ago,
                start_time__lte=now,
            )
            total_lessons = lessons_month.count()

            # Уроки, которые были запущены (есть zoom_meeting_id ИЛИ audit_log lesson_start)
            started_lessons = lessons_month.filter(
                zoom_meeting_id__isnull=False,
            ).exclude(zoom_meeting_id='').count()

            conduct_rate = round((started_lessons / total_lessons) * 100, 1) if total_lessons else None

            # ── Пунктуальность запуска ──
            # Берём AuditLog с action='lesson_start' и сравниваем timestamp с lesson.start_time
            lesson_ids = list(lessons_month.values_list('id', flat=True))
            start_logs = AuditLog.objects.filter(
                user=teacher,
                action='lesson_start',
                resource_type='Lesson',
                resource_id__in=lesson_ids,
            ).values('resource_id', 'timestamp')

            lesson_times = {l.id: l.start_time for l in lessons_month}
            punctuality_data = []
            late_count = 0
            on_time_count = 0
            early_count = 0

            for log in start_logs:
                lesson_id = log['resource_id']
                actual_start = log['timestamp']
                planned_start = lesson_times.get(lesson_id)
                if planned_start:
                    diff_minutes = (actual_start - planned_start).total_seconds() / 60
                    punctuality_data.append(diff_minutes)
                    if diff_minutes > 5:
                        late_count += 1
                    elif diff_minutes < -10:
                        early_count += 1
                    else:
                        on_time_count += 1

            avg_delay_minutes = round(sum(punctuality_data) / len(punctuality_data), 1) if punctuality_data else None
            total_tracked = late_count + on_time_count + early_count
            punctuality_rate = round((on_time_count / total_tracked) * 100, 1) if total_tracked else None

            # ── Скорость проверки ДЗ ──
            graded_submissions = StudentSubmission.objects.filter(
                homework__teacher=teacher,
                status='graded',
                graded_at__isnull=False,
                submitted_at__isnull=False,
                graded_at__gte=month_ago,
            )
            review_times = []
            for sub in graded_submissions.only('submitted_at', 'graded_at').iterator():
                delta = (sub.graded_at - sub.submitted_at).total_seconds() / 3600  # часы
                review_times.append(delta)
            avg_review_hours = round(sum(review_times) / len(review_times), 1) if review_times else None

            # ── Непроверенные ДЗ >3 дней ──
            three_days_ago = now - timedelta(days=3)
            unchecked_hw = StudentSubmission.objects.filter(
                homework__teacher=teacher,
                status='submitted',
                submitted_at__lte=three_days_ago,
            ).count()

            # ── Посещаемость учеников ──
            att_qs = Attendance.objects.filter(
                lesson__teacher=teacher,
                lesson__start_time__gte=month_ago,
            )
            att_total = att_qs.count()
            att_present = att_qs.filter(status='present').count()
            student_attendance_rate = round((att_present / att_total) * 100, 1) if att_total else None

            # ── Нагрузка ──
            lessons_per_week = Lesson.objects.filter(
                teacher=teacher,
                start_time__gte=week_ago,
                start_time__lte=now,
            ).count()
            groups = Group.objects.filter(teacher=teacher)
            total_groups = groups.count()
            total_students = 0
            for g in groups:
                total_students += g.students.count()

            teacher_data.append({
                'teacher_id': teacher.id,
                'teacher_name': teacher.get_full_name(),
                'teacher_email': teacher.email,

                # Проведение уроков
                'total_lessons_month': total_lessons,
                'started_lessons': started_lessons,
                'conduct_rate': conduct_rate,

                # Пунктуальность
                'punctuality_rate': punctuality_rate,
                'avg_delay_minutes': avg_delay_minutes,
                'late_starts': late_count,
                'on_time_starts': on_time_count,
                'early_starts': early_count,

                # Проверка ДЗ
                'avg_review_hours': avg_review_hours,
                'unchecked_hw_overdue': unchecked_hw,

                # Посещаемость учеников
                'student_attendance_rate': student_attendance_rate,

                # Нагрузка
                'lessons_per_week': lessons_per_week,
                'total_groups': total_groups,
                'total_students': total_students,
            })

        # Сортируем: сначала с проблемами (низкий conduct_rate, много unchecked)
        teacher_data.sort(
            key=lambda t: (
                -(t['unchecked_hw_overdue'] or 0),
                (t['punctuality_rate'] or 100),
                (t['conduct_rate'] or 100),
            )
        )

        return Response({
            'total_teachers': teachers.count(),
            'teachers': teacher_data,
        })


# ──────────────────────────────────────────────
#  3. Сводная панель (overview)
# ──────────────────────────────────────────────

class AdminDashboardOverviewView(APIView):
    """
    Краткая сводка для верхних карточек:
    - Всего учеников / с рисками
    - Пропуски за неделю
    - Непроверенные ДЗ
    - Учителя с опозданиями
    - Средняя посещаемость за месяц
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        denied = _require_admin(request)
        if denied:
            return denied

        now = timezone.now()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        from schedule.models import Attendance, Lesson, AuditLog
        from homework.models import StudentSubmission

        total_students = _tenant_user_qs(request).filter(role='student', is_active=True).count()
        total_teachers = _tenant_user_qs(request).filter(role='teacher', is_active=True).count()

        # Пропуски за неделю (только учителя тенанта)
        teacher_ids = _tenant_teacher_ids(request)
        absences_week = Attendance.objects.filter(
            lesson__start_time__gte=week_ago,
            lesson__teacher_id__in=teacher_ids,
            status='absent',
        ).count()

        total_attendance_week = Attendance.objects.filter(
            lesson__start_time__gte=week_ago,
            lesson__teacher_id__in=teacher_ids,
        ).count()

        attendance_rate_week = round(
            ((total_attendance_week - absences_week) / total_attendance_week) * 100, 1
        ) if total_attendance_week else None

        # Средняя посещаемость за месяц
        att_month = Attendance.objects.filter(
            lesson__start_time__gte=month_ago,
            lesson__teacher_id__in=teacher_ids,
        )
        att_month_total = att_month.count()
        att_month_present = att_month.filter(status='present').count()
        attendance_rate_month = round(
            (att_month_present / att_month_total) * 100, 1
        ) if att_month_total else None

        # Непроверенные ДЗ (>3 дней)
        three_days_ago = now - timedelta(days=3)
        unchecked_overdue = StudentSubmission.objects.filter(
            status='submitted',
            submitted_at__lte=three_days_ago,
            homework__teacher_id__in=teacher_ids,
        ).count()

        # Всего непроверенных
        unchecked_total = StudentSubmission.objects.filter(
            status='submitted',
            homework__teacher_id__in=teacher_ids,
        ).count()

        # Уроки за неделю
        lessons_week = Lesson.objects.filter(
            start_time__gte=week_ago,
            start_time__lte=now,
            teacher_id__in=teacher_ids,
        ).count()
        started_week = Lesson.objects.filter(
            start_time__gte=week_ago,
            start_time__lte=now,
            teacher_id__in=teacher_ids,
            zoom_meeting_id__isnull=False,
        ).exclude(zoom_meeting_id='').count()

        # Учителя с опозданиями за месяц
        lesson_starts = AuditLog.objects.filter(
            action='lesson_start',
            timestamp__gte=month_ago,
            user_id__in=teacher_ids,
        ).values('resource_id', 'timestamp', 'user_id')

        late_teacher_ids = set()
        for log in lesson_starts:
            try:
                lesson = Lesson.objects.only('start_time').get(id=log['resource_id'])
                diff = (log['timestamp'] - lesson.start_time).total_seconds() / 60
                if diff > 5:
                    late_teacher_ids.add(log['user_id'])
            except Lesson.DoesNotExist:
                pass

        # Ученики не заходившие >7 дней
        inactive_threshold = now - timedelta(days=7)
        inactive_students = _tenant_user_qs(request).filter(
            role='student',
            is_active=True,
        ).filter(
            Q(last_login__lt=inactive_threshold) | Q(last_login__isnull=True)
        ).count()

        return Response({
            'total_students': total_students,
            'total_teachers': total_teachers,
            'inactive_students': inactive_students,

            'absences_week': absences_week,
            'attendance_rate_week': attendance_rate_week,
            'attendance_rate_month': attendance_rate_month,

            'unchecked_total': unchecked_total,
            'unchecked_overdue': unchecked_overdue,

            'lessons_week': lessons_week,
            'lessons_started_week': started_week,

            'teachers_with_late_starts': len(late_teacher_ids),
        })
