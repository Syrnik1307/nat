from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Q, Avg

from .models import ExamType, Subject, Topic, ExamAssignment, StudentTopicScore
from .serializers import (
    ExamTypeSerializer, SubjectListSerializer, SubjectDetailSerializer,
    TopicSerializer, ExamAssignmentSerializer, StudentTopicScoreSerializer,
)


class ExamTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """Типы экзаменов. Пресеты видны всем, кастомные — только автору."""
    serializer_class = ExamTypeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = ExamType.objects.annotate(subjects_count=Count('subjects'))
        if user.role == 'teacher':
            return qs.filter(Q(is_preset=True) | Q(created_by=user))
        return qs.filter(is_preset=True)


class SubjectViewSet(viewsets.ReadOnlyModelViewSet):
    """Предметы экзамена с фильтрацией по exam_type."""
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return SubjectDetailSerializer
        return SubjectListSerializer

    def get_queryset(self):
        qs = Subject.objects.annotate(topics_count=Count('topics'))
        exam_type = self.request.query_params.get('exam_type')
        if exam_type:
            qs = qs.filter(exam_type_id=exam_type)
        return qs.select_related('exam_type')


class TopicViewSet(viewsets.ReadOnlyModelViewSet):
    """Темы предмета."""
    serializer_class = TopicSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Topic.objects.all()
        subject = self.request.query_params.get('subject')
        if subject:
            qs = qs.filter(subject_id=subject)
        return qs


class ExamAssignmentViewSet(viewsets.ModelViewSet):
    """Назначения экзаменов ученикам/группам (CRUD для учителя)."""
    serializer_class = ExamAssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'teacher':
            return ExamAssignment.objects.filter(teacher=user).select_related(
                'subject', 'subject__exam_type', 'group', 'student'
            )
        elif user.role == 'student':
            return ExamAssignment.objects.filter(
                Q(student=user) | Q(group__students=user)
            ).select_related('subject', 'subject__exam_type').distinct()
        return ExamAssignment.objects.none()

    def perform_create(self, serializer):
        serializer.save(teacher=self.request.user)

    @action(detail=False, methods=['post'])
    def bulk_assign(self, request):
        """Массовое назначение экзамена нескольким группам/ученикам."""
        subject_id = request.data.get('subject')
        group_ids = request.data.get('groups', [])
        student_ids = request.data.get('students', [])

        if not subject_id:
            return Response({'detail': 'subject is required'}, status=status.HTTP_400_BAD_REQUEST)

        created = []
        for gid in group_ids:
            obj, was_created = ExamAssignment.objects.get_or_create(
                teacher=request.user, subject_id=subject_id, group_id=gid,
                defaults={'student': None}
            )
            if was_created:
                created.append(obj.id)

        for sid in student_ids:
            obj, was_created = ExamAssignment.objects.get_or_create(
                teacher=request.user, subject_id=subject_id, student_id=sid,
                defaults={'group': None}
            )
            if was_created:
                created.append(obj.id)

        return Response({'created': len(created)}, status=status.HTTP_201_CREATED)


class ProgressViewSet(viewsets.ViewSet):
    """Прогресс ученика по карте знаний."""
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='student')
    def student_progress(self, request):
        """GET /api/knowledge-map/progress/student/?student=<id>&subject=<id>"""
        student_id = request.query_params.get('student')
        subject_id = request.query_params.get('subject')

        if not student_id or not subject_id:
            return Response(
                {'detail': 'student and subject query params required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return self._build_progress_response(int(student_id), int(subject_id))

    @action(detail=False, methods=['get'], url_path='my')
    def my_progress(self, request):
        """GET /api/knowledge-map/progress/my/?subject=<id> — для ученика."""
        if request.user.role != 'student':
            return Response({'detail': 'Only students'}, status=status.HTTP_403_FORBIDDEN)

        subject_id = request.query_params.get('subject')
        if not subject_id:
            return Response({'detail': 'subject query param required'}, status=status.HTTP_400_BAD_REQUEST)

        return self._build_progress_response(request.user.id, int(subject_id))

    @action(detail=False, methods=['get'], url_path='summary')
    def student_summary(self, request):
        """GET /api/knowledge-map/progress/summary/?student=<id>"""
        student_id = request.query_params.get('student')
        if not student_id:
            if request.user.role == 'student':
                student_id = request.user.id
            else:
                return Response({'detail': 'student param required'}, status=status.HTTP_400_BAD_REQUEST)

        student_id = int(student_id)

        assignments = ExamAssignment.objects.filter(
            Q(student_id=student_id) | Q(group__students__id=student_id)
        ).values_list('subject_id', flat=True).distinct()

        subjects = Subject.objects.filter(id__in=assignments).select_related('exam_type')

        result = []
        for subj in subjects:
            scores = StudentTopicScore.objects.filter(
                student_id=student_id, topic__subject=subj
            )
            topics_count = subj.topics.count()
            topics_with_data = scores.filter(attempts_count__gt=0).count()
            total_attempts = sum(s.attempts_count for s in scores)

            if scores.exists():
                overall = scores.aggregate(avg=Avg('score_percent'))['avg'] or 0
            else:
                overall = 0

            result.append({
                'subject_id': subj.id,
                'subject_name': subj.name,
                'exam_type_name': subj.exam_type.name,
                'icon': subj.icon,
                'overall_percent': round(overall, 1),
                'topics_count': topics_count,
                'topics_with_data': topics_with_data,
                'total_attempts': total_attempts,
            })

        return Response(result)

    def _build_progress_response(self, student_id, subject_id):
        """Build radar-ready progress response."""
        try:
            subject = Subject.objects.prefetch_related('topics').select_related('exam_type').get(id=subject_id)
        except Subject.DoesNotExist:
            return Response({'detail': 'Subject not found'}, status=status.HTTP_404_NOT_FOUND)

        scores = StudentTopicScore.objects.filter(
            student_id=student_id, topic__subject=subject
        ).select_related('topic')

        scores_by_topic = {s.topic_id: s for s in scores}

        topic_data = []
        for topic in subject.topics.all():
            score = scores_by_topic.get(topic.id)
            topic_data.append({
                'topic_id': topic.id,
                'topic_number': topic.number,
                'topic_title': topic.title,
                'topic_max_points': topic.max_points,
                'score_percent': score.score_percent if score else 0,
                'attempts_count': score.attempts_count if score else 0,
                'trend': score.trend if score else 'stable',
                'total_points_earned': score.total_points_earned if score else 0,
                'total_points_possible': score.total_points_possible if score else 0,
            })

        total_attempts = sum(t['attempts_count'] for t in topic_data)
        if topic_data:
            overall = sum(t['score_percent'] for t in topic_data) / len(topic_data)
        else:
            overall = 0

        from .serializers import SubjectDetailSerializer
        return Response({
            'subject': SubjectDetailSerializer(subject).data,
            'scores': topic_data,
            'overall_percent': round(overall, 1),
            'total_attempts': total_attempts,
        })
