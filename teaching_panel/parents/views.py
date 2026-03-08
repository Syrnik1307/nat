from datetime import date, timedelta
from collections import defaultdict

from django.db.models import Q, Avg, Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from .models import ParentAccess, ParentAccessGrant, ParentComment
from .serializers import (
    ParentAccessSerializer,
    ParentAccessGrantSerializer,
    CreateParentAccessSerializer,
    UpdateGrantSerializer,
    ParentCommentSerializer,
    ParentCommentCreateSerializer,
)

from schedule.models import Group, Lesson, Attendance
from homework.models import Homework, StudentSubmission, HomeworkGroupAssignment
from analytics.models import ControlPoint, ControlPointResult


# =============================================================================
# Teacher-facing views (auth required)
# =============================================================================

class TeacherGrantListView(APIView):
    """GET /api/parents/grants/ — список грантов текущего учителя."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role != 'teacher':
            return Response({'detail': 'Только для учителей'}, status=status.HTTP_403_FORBIDDEN)
        grants = ParentAccessGrant.objects.filter(
            teacher=request.user, is_active=True
        ).select_related('parent_access__student', 'group').prefetch_related('comments')
        data = ParentAccessGrantSerializer(grants, many=True).data
        return Response(data)


class TeacherCreateAccessView(APIView):
    """POST /api/parents/access/ — создать доступ для родителя.
    Создаёт ParentAccess (если нет) + ParentAccessGrant.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.role != 'teacher':
            return Response({'detail': 'Только для учителей'}, status=status.HTTP_403_FORBIDDEN)

        ser = CreateParentAccessSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        # Проверяем что группа принадлежит учителю и ученик в ней
        group = get_object_or_404(Group, id=d['group_id'], teacher=request.user)
        if not group.students.filter(id=d['student_id'], role='student').exists():
            return Response(
                {'detail': 'Ученик не найден в этой группе'},
                status=status.HTTP_400_BAD_REQUEST
            )

        student_user = group.students.get(id=d['student_id'])

        # Создаём или получаем ParentAccess
        parent_access, _ = ParentAccess.objects.get_or_create(
            student=student_user,
            defaults={
                'parent_name': d.get('parent_name', ''),
                'parent_contact': d.get('parent_contact', ''),
            }
        )

        # Создаём грант (или возвращаем существующий)
        grant, created = ParentAccessGrant.objects.get_or_create(
            parent_access=parent_access,
            teacher=request.user,
            group=group,
            defaults={'subject_label': d['subject_label']}
        )
        if not created and not grant.is_active:
            grant.is_active = True
            grant.subject_label = d['subject_label']
            grant.save(update_fields=['is_active', 'subject_label'])

        return Response(
            ParentAccessSerializer(parent_access, context={'request': request}).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class TeacherGrantDetailView(APIView):
    """PATCH/DELETE /api/parents/grants/{id}/ — обновить/деактивировать грант."""
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, grant_id):
        grant = get_object_or_404(
            ParentAccessGrant, id=grant_id, teacher=request.user, is_active=True
        )
        ser = UpdateGrantSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        for field, value in ser.validated_data.items():
            setattr(grant, field, value)
        grant.save()
        return Response(ParentAccessGrantSerializer(grant).data)

    def delete(self, request, grant_id):
        grant = get_object_or_404(
            ParentAccessGrant, id=grant_id, teacher=request.user
        )
        grant.is_active = False
        grant.save(update_fields=['is_active'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class TeacherGetStudentAccessView(APIView):
    """GET /api/parents/access/student/{student_id}/group/{group_id}/
    Получить информацию о доступе для конкретного ученика (для модалки).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, student_id, group_id):
        if request.user.role != 'teacher':
            return Response({'detail': 'Только для учителей'}, status=status.HTTP_403_FORBIDDEN)

        try:
            parent_access = ParentAccess.objects.get(student_id=student_id)
            grant = ParentAccessGrant.objects.filter(
                parent_access=parent_access,
                teacher=request.user,
                group_id=group_id,
            ).first()
            data = ParentAccessSerializer(parent_access, context={'request': request}).data
            data['my_grant'] = ParentAccessGrantSerializer(grant).data if grant else None
            return Response(data)
        except ParentAccess.DoesNotExist:
            return Response({'exists': False})


class TeacherCommentView(APIView):
    """POST /api/parents/grants/{grant_id}/comments/ — добавить комментарий.
    GET — список комментариев для этого гранта.
    DELETE /api/parents/grants/{grant_id}/comments/{comment_id}/ — удалить.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, grant_id):
        grant = get_object_or_404(
            ParentAccessGrant, id=grant_id, teacher=request.user
        )
        comments = grant.comments.all()[:20]
        return Response(ParentCommentSerializer(comments, many=True).data)

    def post(self, request, grant_id):
        grant = get_object_or_404(
            ParentAccessGrant, id=grant_id, teacher=request.user, is_active=True
        )
        ser = ParentCommentCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        comment = ParentComment.objects.create(
            grant=grant,
            teacher=request.user,
            text=ser.validated_data['text'],
        )
        return Response(ParentCommentSerializer(comment).data, status=status.HTTP_201_CREATED)


class TeacherCommentDeleteView(APIView):
    """DELETE /api/parents/grants/{grant_id}/comments/{comment_id}/"""
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, grant_id, comment_id):
        comment = get_object_or_404(
            ParentComment, id=comment_id, grant_id=grant_id, teacher=request.user
        )
        comment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# =============================================================================
# Parent-facing dashboard (NO auth, token-based)
# =============================================================================

class ParentDashboardThrottle(AnonRateThrottle):
    rate = '30/min'


class ParentDashboardView(APIView):
    """GET /api/parents/dashboard/{token}/ — полный дашборд для родителя.
    Без авторизации — доступ по UUID токену.
    Query params: ?month=2026-03 (фильтр ДЗ)
    """
    permission_classes = []
    authentication_classes = []
    throttle_classes = [ParentDashboardThrottle]

    def get(self, request, token):
        parent_access = get_object_or_404(
            ParentAccess, token=token, is_active=True
        )
        student = parent_access.student

        # Обновляем счётчик просмотров
        parent_access.last_viewed_at = timezone.now()
        parent_access.view_count += 1
        parent_access.save(update_fields=['last_viewed_at', 'view_count'])

        # Парсим фильтр по месяцу
        month_str = request.query_params.get('month')
        if month_str:
            try:
                year, month = month_str.split('-')
                month_start = date(int(year), int(month), 1)
            except (ValueError, IndexError):
                month_start = date.today().replace(day=1)
        else:
            month_start = date.today().replace(day=1)

        if month_start.month == 12:
            month_end = date(month_start.year + 1, 1, 1)
        else:
            month_end = date(month_start.year, month_start.month + 1, 1)

        # Собираем данные по каждому активному гранту
        grants = parent_access.grants.filter(is_active=True).select_related(
            'teacher', 'group'
        ).prefetch_related('comments')

        subjects = []
        for grant in grants:
            subject_data = self._build_subject_data(
                grant, student, month_start, month_end
            )
            subjects.append(subject_data)

        result = {
            'student_name': student.get_full_name(),
            'last_viewed_at': parent_access.last_viewed_at,
            'telegram_connected': parent_access.telegram_connected,
            'telegram_bot_link': f"https://t.me/lectio_parent_bot?start={parent_access.token}",
            'subjects': subjects,
        }

        return Response(result)

    def _build_subject_data(self, grant, student, month_start, month_end):
        group = grant.group

        # --- Посещаемость ---
        lessons = Lesson.objects.filter(group=group).order_by('start_time')
        total_lessons = lessons.count()
        attendances = Attendance.objects.filter(
            lesson__group=group, student=student
        )
        attended = attendances.filter(status='present').count()
        attendance_pct = round((attended / total_lessons * 100), 1) if total_lessons > 0 else 0

        # --- ДЗ: общая статистика ---
        # Находим все ДЗ назначенные на эту группу
        hw_ids = HomeworkGroupAssignment.objects.filter(
            group=group
        ).values_list('homework_id', flat=True)
        all_hw = Homework.objects.filter(
            Q(id__in=hw_ids) | Q(lesson__group=group),
            status='published',
        ).distinct()
        hw_total = all_hw.count()

        submissions = StudentSubmission.objects.filter(
            homework__in=all_hw, student=student
        ).exclude(status='in_progress')
        hw_done = submissions.count()
        hw_avg = submissions.aggregate(avg=Avg('total_score'))['avg']

        # --- ДЗ: список за выбранный месяц ---
        month_hw = all_hw.filter(
            created_at__date__gte=month_start,
            created_at__date__lt=month_end,
        ).order_by('-created_at')

        homework_list = []
        for hw in month_hw:
            sub = submissions.filter(homework=hw).first()
            hw_status = self._hw_status(hw, sub)
            homework_list.append({
                'title': hw.title,
                'assigned_date': hw.created_at.date(),
                'deadline': hw.deadline,
                'submitted_date': sub.submitted_at if sub else None,
                'score': sub.total_score if sub else None,
                'max_score': hw.max_score,
                'status': hw_status,
            })

        # --- Контрольные точки ---
        cp_results = ControlPointResult.objects.filter(
            student=student,
            control_point__group=group,
        ).select_related('control_point').order_by('-control_point__date')[:10]

        control_points = [{
            'title': r.control_point.title,
            'date': r.control_point.date,
            'points': r.points,
            'max_points': r.control_point.max_points,
        } for r in cp_results]

        # --- График динамики ДЗ (по месяцам) ---
        hw_chart_data = self._build_chart_data(all_hw, student)

        # --- Комментарии ---
        comments = ParentCommentSerializer(
            grant.comments.filter()[:5], many=True
        ).data

        return {
            'grant_id': grant.id,
            'subject_label': grant.subject_label,
            'teacher_name': grant.teacher.get_full_name(),
            'total_lessons': total_lessons,
            'attended_lessons': attended,
            'attendance_pct': attendance_pct,
            'hw_total': hw_total,
            'hw_done': hw_done,
            'hw_avg_score': round(hw_avg, 1) if hw_avg is not None else None,
            'homework_list': homework_list,
            'control_points': control_points,
            'hw_chart_data': hw_chart_data,
            'comments': comments,
            # Заглушки
            'knowledge_map': None,
            'finance': None,
        }

    def _hw_status(self, hw, submission):
        if submission:
            if submission.status == 'graded':
                return 'done'
            if submission.status == 'submitted':
                return 'pending'
            if submission.status == 'revision':
                return 'revision'
        # Нет сабмишена — проверяем дедлайн
        if hw.deadline and timezone.now() > hw.deadline:
            return 'overdue'
        return 'not_submitted'

    def _build_chart_data(self, all_hw, student):
        """Строим данные для recharts: avg_score и done_pct по месяцам."""
        # Группируем ДЗ по месяцам
        monthly = defaultdict(lambda: {'total': 0, 'done': 0, 'scores': []})

        for hw in all_hw:
            m_key = hw.created_at.strftime('%Y-%m')
            monthly[m_key]['total'] += 1

            sub = StudentSubmission.objects.filter(
                homework=hw, student=student
            ).exclude(status='in_progress').first()

            if sub:
                monthly[m_key]['done'] += 1
                if sub.total_score is not None:
                    monthly[m_key]['scores'].append(sub.total_score)

        chart_data = []
        for m_key in sorted(monthly.keys()):
            d = monthly[m_key]
            avg_score = (
                sum(d['scores']) / len(d['scores']) if d['scores'] else 0
            )
            done_pct = (
                round(d['done'] / d['total'] * 100, 1) if d['total'] > 0 else 0
            )
            chart_data.append({
                'month': m_key,
                'avg_score': round(avg_score, 1),
                'done_pct': done_pct,
            })

        return chart_data
