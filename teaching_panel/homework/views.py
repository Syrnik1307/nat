import os
import logging

from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from core.models import AuditLog
from .models import Homework, StudentSubmission, Answer
from .serializers import HomeworkSerializer, StudentSubmissionSerializer
from .permissions import IsTeacherHomework, IsStudentSubmission
from .tasks import notify_student_graded

logger = logging.getLogger(__name__)


class HomeworkViewSet(viewsets.ModelViewSet):
    queryset = Homework.objects.all().select_related('teacher', 'lesson')
    serializer_class = HomeworkSerializer
    permission_classes = [IsTeacherHomework]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_authenticated:
            if getattr(user, 'role', None) == 'teacher':
                return qs.filter(teacher=user)
            elif getattr(user, 'role', None) == 'student':
                return qs.filter(lesson__group__students=user) | qs.filter(teacher__teaching_groups__students=user)
        return qs.none()


class StudentSubmissionViewSet(viewsets.ModelViewSet):
    queryset = StudentSubmission.objects.all().select_related('homework', 'student')
    serializer_class = StudentSubmissionSerializer
    permission_classes = [IsStudentSubmission]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_authenticated:
            if getattr(user, 'role', None) == 'student':
                return qs.filter(student=user)
            elif getattr(user, 'role', None) == 'teacher':
                return qs.filter(homework__teacher=user)
        return qs.none()
    
    def retrieve(self, request, *args, **kwargs):
        # Детальный просмотр: подтянем ответы и связанные объекты, чтобы избежать N+1
        self.queryset = self.get_queryset().prefetch_related(
            'answers', 'answers__question', 'answers__selected_choices'
        )
        return super().retrieve(request, *args, **kwargs)
    
    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated])
    def update_answer(self, request, pk=None):
        """
        Обновить оценку и комментарий учителя для конкретного ответа.
        Доступно только учителю, который создал задание.
        
        Запрос:
        PATCH /api/submissions/{submission_id}/update_answer/
        {
            "answer_id": 123,
            "teacher_score": 5,
            "teacher_feedback": "Хорошая работа!"
        }
        """
        submission = self.get_object()
        
        # Проверяем, что пользователь - учитель этого задания
        if request.user != submission.homework.teacher:
            return Response(
                {'error': 'Только учитель, создавший задание, может редактировать ответы'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        answer_id = request.data.get('answer_id')
        if not answer_id:
            return Response(
                {'error': 'Требуется answer_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            answer = Answer.objects.get(id=answer_id, submission=submission)
        except Answer.DoesNotExist:
            return Response(
                {'error': 'Ответ не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Обновляем поля
        teacher_score = request.data.get('teacher_score')
        teacher_feedback = request.data.get('teacher_feedback', '')
        
        if teacher_score is not None:
            try:
                teacher_score = int(teacher_score)
                max_points = answer.question.points
                if teacher_score < 0 or teacher_score > max_points:
                    return Response(
                        {'error': f'Оценка должна быть от 0 до {max_points}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                answer.teacher_score = teacher_score
            except (ValueError, TypeError):
                return Response(
                    {'error': 'Некорректное значение teacher_score'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        answer.teacher_feedback = teacher_feedback
        answer.save(update_fields=['teacher_score', 'teacher_feedback'])
        
        # Аудит-лог: выставление оценки
        AuditLog.log(
            user=request.user,
            action='grade',
            content_object=answer,
            description=f'Выставлена оценка {teacher_score} за вопрос {answer.question.id}',
            metadata={
                'submission_id': submission.id,
                'question_id': answer.question.id,
                'teacher_score': teacher_score,
                'feedback_length': len(teacher_feedback),
            },
            request=request
        )
        
        # Пересчитываем общий балл
        submission.compute_auto_score()
        
        # Обновляем статус на "проверено", если это была ручная проверка
        if submission.status == 'submitted':
            submission.status = 'graded'
            submission.save(update_fields=['status'])
            # Уведомим ученика в фоне (Celery)
            try:
                notify_student_graded.delay(submission.id)
            except Exception:
                # В случае отсутствия брокера/воркера тихо игнорируем
                pass
        
        # Возвращаем обновленные данные
        serializer = self.get_serializer(submission)
        return Response(serializer.data)


class HomeworkViewSetUploadMixin:
    """upload_student_answer action added to HomeworkViewSet on prod."""
    pass


# ── upload-student-answer action (added to HomeworkViewSet on prod) ──
# This action is defined here for local reference; on production it lives
# inside HomeworkViewSet directly.
#
# @action(detail=False, methods=['post'], url_path='upload-student-answer',
#         permission_classes=[IsAuthenticated],
#         parser_classes=[MultiPartParser, FormParser])
# def upload_student_answer(self, request):
#     ...
#
# The action saves uploaded files to media/homework_files/ and returns
# { url, file_id, file_name, mime_type, size }.
# Nginx serves them via /media/ location.
