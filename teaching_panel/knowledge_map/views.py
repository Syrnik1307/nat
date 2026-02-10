from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404

from .models import (
    ExamType, Subject, Section, Topic,
    StudentExamAssignment, StudentTopicMastery,
)
from .serializers import (
    ExamTypeSerializer, SubjectSerializer, SubjectBriefSerializer,
    TopicBriefSerializer, TopicMasterySerializer,
    StudentExamAssignmentSerializer,
)


class ExamTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """Типы экзаменов (ЕГЭ / ОГЭ)."""
    queryset = ExamType.objects.all()
    serializer_class = ExamTypeSerializer
    permission_classes = [IsAuthenticated]


class SubjectViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Предметы экзамена.
    GET /api/knowledge-map/subjects/?exam_type=ege
    GET /api/knowledge-map/subjects/{id}/ — с деревом секций и тем
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Subject.objects.select_related('exam_type')
        exam_type = self.request.query_params.get('exam_type')
        if exam_type:
            qs = qs.filter(exam_type__code=exam_type)
        return qs

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return SubjectSerializer
        return SubjectBriefSerializer


class TopicViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Темы/задания экзамена.
    GET /api/knowledge-map/topics/?subject_id=1
    GET /api/knowledge-map/topics/?subject_id=1&search=уравнение
    """
    serializer_class = TopicBriefSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Topic.objects.select_related(
            'section', 'section__subject', 'section__subject__exam_type'
        )
        subject_id = self.request.query_params.get('subject_id')
        if subject_id:
            qs = qs.filter(section__subject_id=subject_id)

        section_id = self.request.query_params.get('section_id')
        if section_id:
            qs = qs.filter(section_id=section_id)

        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search) |
                Q(keywords__contains=search)
            )

        exam_type = self.request.query_params.get('exam_type')
        if exam_type:
            qs = qs.filter(section__subject__exam_type__code=exam_type)

        return qs


class StudentExamAssignmentViewSet(viewsets.ModelViewSet):
    """Назначение экзаменов ученикам."""
    serializer_class = StudentExamAssignmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'student':
            return StudentExamAssignment.objects.filter(student=user)
        return StudentExamAssignment.objects.select_related(
            'student', 'subject', 'subject__exam_type'
        )

    def perform_create(self, serializer):
        serializer.save(assigned_by=self.request.user)

    @action(detail=False, methods=['post'])
    def bulk_assign(self, request):
        """POST {student_ids: [1,2,3], subject_id: 5}"""
        student_ids = request.data.get('student_ids', [])
        subject_id = request.data.get('subject_id')

        if not student_ids or not subject_id:
            return Response(
                {'detail': 'student_ids и subject_id обязательны'},
                status=status.HTTP_400_BAD_REQUEST
            )

        subject = get_object_or_404(Subject, id=subject_id)
        created = 0
        for sid in student_ids:
            _, was_created = StudentExamAssignment.objects.get_or_create(
                student_id=sid,
                subject=subject,
                defaults={'assigned_by': request.user}
            )
            if was_created:
                created += 1

        return Response({'created': created, 'total': len(student_ids)})


class KnowledgeMapViewSet(viewsets.ViewSet):
    """
    Карта знаний — прогресс по темам.
    GET /api/knowledge-map/progress/student/?student_id=5&subject_id=1
    GET /api/knowledge-map/progress/group/?group_id=3&subject_id=1
    GET /api/knowledge-map/progress/summary/?student_id=5
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='student')
    def student_progress(self, request):
        """Карта знаний ученика по предмету — дерево: sections → topics → mastery."""
        student_id = request.query_params.get('student_id')
        subject_id = request.query_params.get('subject_id')

        if not subject_id:
            return Response(
                {'detail': 'subject_id обязателен'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not student_id and request.user.role == 'student':
            student_id = request.user.id
        elif not student_id:
            return Response(
                {'detail': 'student_id обязателен для учителя'},
                status=status.HTTP_400_BAD_REQUEST
            )

        subject = get_object_or_404(
            Subject.objects.select_related('exam_type'), id=subject_id
        )

        mastery_map = {}
        masteries = StudentTopicMastery.objects.filter(
            student_id=student_id,
            topic__section__subject=subject,
        ).select_related('topic', 'topic__section')

        for m in masteries:
            mastery_map[m.topic_id] = TopicMasterySerializer(m).data

        sections_data = []
        sections = Section.objects.filter(subject=subject).prefetch_related('topics')

        total_topics = 0
        mastered_count = 0
        in_progress_count = 0
        needs_review_count = 0
        mastery_sum = 0
        stability_sum = 0
        topics_with_data = 0

        for section in sections:
            topics_data = []
            for topic in section.topics.all():
                total_topics += 1
                mastery_data = mastery_map.get(topic.id)
                if mastery_data:
                    topics_with_data += 1
                    mastery_sum += mastery_data['mastery_level']
                    stability_sum += mastery_data.get('stability', 0)
                    s = mastery_data.get('status', 'not_started')
                    if s == 'mastered':
                        mastered_count += 1
                    elif s in ('learning', 'practiced'):
                        in_progress_count += 1
                    elif s == 'needs_review':
                        needs_review_count += 1

                topics_data.append({
                    'id': topic.id,
                    'code': topic.code,
                    'name': topic.name,
                    'task_number': topic.task_number,
                    'max_score': topic.max_score,
                    'difficulty': topic.difficulty,
                    'mastery': mastery_data,
                })

            section_mastery_vals = [
                t['mastery']['mastery_level']
                for t in topics_data if t['mastery']
            ]
            sections_data.append({
                'id': section.id,
                'code': section.code,
                'name': section.name,
                'topics': topics_data,
                'avg_mastery': (
                    round(sum(section_mastery_vals) / len(section_mastery_vals), 1)
                    if section_mastery_vals else 0
                ),
                'topics_count': len(topics_data),
                'topics_with_data': len(section_mastery_vals),
            })

        return Response({
            'subject': SubjectBriefSerializer(subject).data,
            'sections': sections_data,
            'overall_mastery': (
                round(mastery_sum / topics_with_data, 1)
                if topics_with_data else 0
            ),
            'overall_stability': (
                round(stability_sum / topics_with_data, 1)
                if topics_with_data else 0
            ),
            'topics_total': total_topics,
            'topics_mastered': mastered_count,
            'topics_in_progress': in_progress_count,
            'topics_needs_review': needs_review_count,
            'topics_not_started': (
                total_topics - mastered_count - in_progress_count - needs_review_count
            ),
        })

    @action(detail=False, methods=['get'], url_path='group')
    def group_progress(self, request):
        """Агрегированная карта знаний группы по предмету."""
        from schedule.models import Group
        from django.contrib.auth import get_user_model
        User = get_user_model()

        group_id = request.query_params.get('group_id')
        subject_id = request.query_params.get('subject_id')

        if not group_id or not subject_id:
            return Response(
                {'detail': 'group_id и subject_id обязательны'},
                status=status.HTTP_400_BAD_REQUEST
            )

        group = get_object_or_404(Group, id=group_id)
        subject = get_object_or_404(
            Subject.objects.select_related('exam_type'), id=subject_id
        )

        student_ids = list(group.students.values_list('id', flat=True))

        mastery_agg = StudentTopicMastery.objects.filter(
            student_id__in=student_ids,
            topic__section__subject=subject,
        ).values('topic_id').annotate(
            avg_mastery=Avg('mastery_level'),
            avg_stability=Avg('stability'),
            students_attempted=Count('student', distinct=True),
        )
        mastery_lookup = {m['topic_id']: m for m in mastery_agg}

        student_summaries = []
        for sid in student_ids:
            try:
                user = User.objects.get(id=sid)
            except User.DoesNotExist:
                continue
            sm = StudentTopicMastery.objects.filter(
                student_id=sid, topic__section__subject=subject,
            )
            avg = sm.aggregate(avg=Avg('mastery_level'))['avg'] or 0
            student_summaries.append({
                'id': sid,
                'name': f'{user.last_name} {user.first_name}'.strip() or user.email,
                'avg_mastery': round(avg, 1),
                'topics_attempted': sm.filter(attempted_count__gt=0).count(),
            })

        sections_data = []
        sections = Section.objects.filter(subject=subject).prefetch_related('topics')
        all_mastery_values = []

        for section in sections:
            topics_data = []
            for topic in section.topics.all():
                agg = mastery_lookup.get(topic.id, {})
                avg_m = round(agg.get('avg_mastery', 0), 1)
                if avg_m > 0:
                    all_mastery_values.append(avg_m)
                topics_data.append({
                    'id': topic.id,
                    'code': topic.code,
                    'name': topic.name,
                    'task_number': topic.task_number,
                    'avg_mastery': avg_m,
                    'avg_stability': round(agg.get('avg_stability', 0), 1),
                    'students_attempted': agg.get('students_attempted', 0),
                    'total_students': len(student_ids),
                })
            sections_data.append({
                'id': section.id,
                'code': section.code,
                'name': section.name,
                'topics': topics_data,
            })

        return Response({
            'subject': SubjectBriefSerializer(subject).data,
            'group': {'id': group.id, 'name': group.name},
            'students': sorted(student_summaries, key=lambda s: -s['avg_mastery']),
            'sections': sections_data,
            'overall_mastery': (
                round(sum(all_mastery_values) / len(all_mastery_values), 1)
                if all_mastery_values else 0
            ),
            'total_students': len(student_ids),
        })

    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        """Краткая сводка по ученику: все предметы и общий прогресс."""
        student_id = request.query_params.get('student_id')
        if not student_id and request.user.role == 'student':
            student_id = request.user.id
        elif not student_id:
            return Response(
                {'detail': 'student_id обязателен'},
                status=status.HTTP_400_BAD_REQUEST
            )

        assignments = StudentExamAssignment.objects.filter(
            student_id=student_id
        ).select_related('subject', 'subject__exam_type')

        results = []
        for assignment in assignments:
            subject = assignment.subject
            masteries = StudentTopicMastery.objects.filter(
                student_id=student_id,
                topic__section__subject=subject,
            )
            total_topics = Topic.objects.filter(section__subject=subject).count()
            avg = masteries.aggregate(avg=Avg('mastery_level'))['avg'] or 0

            status_counts = {}
            for m in masteries:
                status_counts[m.status] = status_counts.get(m.status, 0) + 1

            results.append({
                'subject': SubjectBriefSerializer(subject).data,
                'avg_mastery': round(avg, 1),
                'topics_total': total_topics,
                'topics_attempted': masteries.filter(attempted_count__gt=0).count(),
                'status_counts': status_counts,
            })

        return Response(results)
