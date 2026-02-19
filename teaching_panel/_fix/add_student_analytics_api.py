#!/usr/bin/env python3
"""
Adds missing API endpoints:
- /api/attendance-alerts/          (GET)
- /api/attendance-alerts/mark-read/ (POST)
- /api/student-detail/<id>/        (GET)
- /api/student-detail/<id>/attendance/    (GET)
- /api/student-detail/<id>/participation/ (GET)
- /api/student-detail/<id>/homework/      (GET)
"""

import os

BASE = '/var/www/teaching_panel/teaching_panel'

# ── 1. Create analytics_api_views.py in the analytics app ──
views_code = r'''"""
Student analytics & attendance alerts API views.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.db.models import Count, Q, Avg, F, Case, When, IntegerField, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import timedelta

from schedule.models import Attendance, Lesson, Group
from homework.models import StudentSubmission, Homework, Answer
from accounts.models import CustomUser


class AttendanceAlertsView(APIView):
    """
    GET  /api/attendance-alerts/
    Returns students with consecutive absences (3+).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role not in ('teacher', 'admin'):
            return Response({'alerts': []})

        # Get teacher's groups
        if user.role == 'admin' and user.is_superuser:
            groups = Group.objects.all()
        else:
            groups = Group.objects.filter(teacher=user)

        alerts = []
        for group in groups.prefetch_related('students'):
            # Last N lessons in this group (up to 10)
            recent_lessons = Lesson.objects.filter(
                group=group,
                start_time__lte=timezone.now()
            ).order_by('-start_time')[:10]

            if not recent_lessons:
                continue

            for student in group.students.all():
                # Count consecutive absences from the most recent lesson back
                consecutive = 0
                for lesson in recent_lessons:
                    att = Attendance.objects.filter(
                        lesson=lesson, student=student
                    ).first()
                    if att and att.status == 'absent':
                        consecutive += 1
                    else:
                        break

                if consecutive >= 3:
                    severity = 'high' if consecutive >= 5 else 'medium' if consecutive >= 4 else 'low'
                    alerts.append({
                        'severity': severity,
                        'student_id': student.id,
                        'group_id': group.id,
                        'consecutive_absences': consecutive,
                        'student_name': student.get_full_name() or student.email,
                        'student_email': student.email,
                        'group_name': group.name,
                    })

        # Sort by severity (high first)
        severity_order = {'high': 0, 'medium': 1, 'low': 2}
        alerts.sort(key=lambda a: severity_order.get(a['severity'], 9))

        return Response({'alerts': alerts})


class AttendanceAlertsMarkReadView(APIView):
    """
    POST /api/attendance-alerts/mark-read/
    Body: { items: [{student_id, group_id, consecutive_absences}] }
    Currently just returns success (no persistent storage for read state).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Acknowledge — in the future could persist read state
        return Response({'status': 'ok'})


class StudentDetailSummaryView(APIView):
    """
    GET /api/student-detail/<student_id>/?group_id=<group_id>
    Returns summary stats for a student.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, student_id):
        student = self._get_student(student_id)
        if student is None:
            return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)

        group_id = request.query_params.get('group_id')
        lesson_filter = Q(attendances__student=student)
        if group_id:
            lesson_filter &= Q(group_id=group_id)

        # Attendance summary
        total_lessons = Attendance.objects.filter(
            student=student,
            **({"lesson__group_id": group_id} if group_id else {})
        ).count()
        present = Attendance.objects.filter(
            student=student, status='present',
            **({"lesson__group_id": group_id} if group_id else {})
        ).count()
        excused = Attendance.objects.filter(
            student=student, status='excused',
            **({"lesson__group_id": group_id} if group_id else {})
        ).count()
        absent = total_lessons - present - excused

        attendance_pct = round(((present + excused) / total_lessons * 100), 1) if total_lessons > 0 else 0

        # Homework summary
        hw_filter = {}
        if group_id:
            hw_filter['homework__lesson__group_id'] = group_id
        submissions = StudentSubmission.objects.filter(student=student, **hw_filter)
        total_hw = submissions.count()
        graded_hw = submissions.filter(status='graded').count()
        avg_score = submissions.filter(
            status='graded', total_score__isnull=False
        ).aggregate(avg=Avg('total_score'))['avg']

        return Response({
            'student': {
                'id': student.id,
                'first_name': student.first_name,
                'last_name': student.last_name,
                'email': student.email,
            },
            'attendance': {
                'total': total_lessons,
                'present': present,
                'excused': excused,
                'absent': absent,
                'percentage': attendance_pct,
            },
            'homework': {
                'total': total_hw,
                'graded': graded_hw,
                'average_score': round(avg_score, 1) if avg_score is not None else None,
            },
        })

    def _get_student(self, student_id):
        try:
            return CustomUser.objects.get(id=student_id, role='student')
        except CustomUser.DoesNotExist:
            return None


class StudentDetailAttendanceView(APIView):
    """
    GET /api/student-detail/<student_id>/attendance/?group_id=<group_id>
    Returns per-lesson attendance history.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, student_id):
        group_id = request.query_params.get('group_id')
        filters = {'student_id': student_id}
        if group_id:
            filters['lesson__group_id'] = group_id

        records = Attendance.objects.filter(**filters).select_related(
            'lesson', 'lesson__group'
        ).order_by('-lesson__start_time')[:50]

        data = []
        for r in records:
            data.append({
                'lesson_id': r.lesson_id,
                'lesson_title': r.lesson.title or f"Занятие {r.lesson_id}",
                'lesson_date': r.lesson.start_time.isoformat(),
                'group_id': r.lesson.group_id,
                'group_name': r.lesson.group.name if r.lesson.group else '',
                'status': r.status,
                'notes': r.notes,
            })

        return Response({'attendance': data})


class StudentDetailParticipationView(APIView):
    """
    GET /api/student-detail/<student_id>/participation/?group_id=<group_id>
    Returns participation metrics (based on attendance present + lessons).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, student_id):
        group_id = request.query_params.get('group_id')
        filters = {'student_id': student_id}
        if group_id:
            filters['lesson__group_id'] = group_id

        records = Attendance.objects.filter(**filters).select_related(
            'lesson', 'lesson__group'
        ).order_by('-lesson__start_time')[:50]

        data = []
        for r in records:
            data.append({
                'lesson_id': r.lesson_id,
                'lesson_title': r.lesson.title or f"Занятие {r.lesson_id}",
                'lesson_date': r.lesson.start_time.isoformat(),
                'group_id': r.lesson.group_id,
                'group_name': r.lesson.group.name if r.lesson.group else '',
                'was_present': r.status in ('present', 'excused'),
                'status': r.status,
            })

        total = len(data)
        present = sum(1 for d in data if d['was_present'])
        rate = round(present / total * 100, 1) if total > 0 else 0

        return Response({
            'participation': data,
            'summary': {
                'total_lessons': total,
                'attended': present,
                'rate': rate,
            }
        })


class StudentDetailHomeworkView(APIView):
    """
    GET /api/student-detail/<student_id>/homework/?group_id=<group_id>
    Returns homework submissions for the student.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, student_id):
        group_id = request.query_params.get('group_id')
        filters = {'student_id': student_id}
        if group_id:
            filters['homework__lesson__group_id'] = group_id

        submissions = StudentSubmission.objects.filter(**filters).select_related(
            'homework', 'homework__lesson', 'homework__lesson__group'
        ).order_by('-submitted_at')[:50]

        data = []
        for s in submissions:
            hw = s.homework
            lesson = hw.lesson
            data.append({
                'submission_id': s.id,
                'homework_id': hw.id,
                'homework_title': hw.title,
                'lesson_id': lesson.id if lesson else None,
                'lesson_title': (lesson.title if lesson else '') or '',
                'group_id': lesson.group_id if lesson else None,
                'group_name': lesson.group.name if lesson and lesson.group else '',
                'status': s.status,
                'total_score': s.total_score,
                'max_score': hw.max_score,
                'submitted_at': s.submitted_at.isoformat() if s.submitted_at else None,
                'graded_at': s.graded_at.isoformat() if s.graded_at else None,
            })

        total = len(data)
        graded = [d for d in data if d['status'] == 'graded']
        avg_score = None
        if graded:
            scores = [d['total_score'] for d in graded if d['total_score'] is not None]
            if scores:
                avg_score = round(sum(scores) / len(scores), 1)

        return Response({
            'homework': data,
            'summary': {
                'total': total,
                'graded': len(graded),
                'average_score': avg_score,
            }
        })
'''

views_path = os.path.join(BASE, 'analytics', 'analytics_api_views.py')
with open(views_path, 'w') as f:
    f.write(views_code)
print(f'[OK] Created {views_path}')

# ── 2. Add URL routes to main urls.py ──
urls_path = os.path.join(BASE, 'teaching_panel', 'urls.py')
with open(urls_path, 'r') as f:
    content = f.read()

# Check if already patched
if 'attendance-alerts' in content:
    print('[SKIP] attendance-alerts route already exists in urls.py')
else:
    # Add import
    import_line = (
        "from analytics.analytics_api_views import (\n"
        "    AttendanceAlertsView, AttendanceAlertsMarkReadView,\n"
        "    StudentDetailSummaryView, StudentDetailAttendanceView,\n"
        "    StudentDetailParticipationView, StudentDetailHomeworkView,\n"
        ")\n"
    )

    # Insert import after existing analytics import
    anchor = "from core.tenant_mixins import TenantViewSetMixin"
    if anchor not in content:
        # Try alternate anchor
        anchor = "from analytics.views import"
    
    # Find a good place to insert the import - after the existing imports block
    # We'll insert before "# Create a router"
    router_anchor = "# Create a router"
    if router_anchor in content:
        content = content.replace(router_anchor, import_line + "\n" + router_anchor)
    else:
        # fallback: insert after last from-import line before router
        lines = content.split('\n')
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.startswith('from ') or line.startswith('import '):
                insert_idx = i + 1
        lines.insert(insert_idx, import_line)
        content = '\n'.join(lines)

    # Add URL patterns before path('api/me/', ...)
    url_lines = """
    # Attendance alerts API
    path('api/attendance-alerts/', AttendanceAlertsView.as_view(), name='api-attendance-alerts'),
    path('api/attendance-alerts/mark-read/', AttendanceAlertsMarkReadView.as_view(), name='api-attendance-alerts-mark-read'),

    # Student detail analytics API
    path('api/student-detail/<int:student_id>/', StudentDetailSummaryView.as_view(), name='api-student-detail'),
    path('api/student-detail/<int:student_id>/attendance/', StudentDetailAttendanceView.as_view(), name='api-student-detail-attendance'),
    path('api/student-detail/<int:student_id>/participation/', StudentDetailParticipationView.as_view(), name='api-student-detail-participation'),
    path('api/student-detail/<int:student_id>/homework/', StudentDetailHomeworkView.as_view(), name='api-student-detail-homework'),
"""

    # Insert before api/me/
    me_anchor = "    path('api/me/',"
    if me_anchor in content:
        content = content.replace(me_anchor, url_lines + "\n" + me_anchor)
    else:
        # fallback: insert before the closing bracket of urlpatterns
        content = content.replace('\n]\n', url_lines + '\n]\n')

    with open(urls_path, 'w') as f:
        f.write(content)
    print(f'[OK] Updated {urls_path}')

print('\nDone! Restart the service to apply changes.')
