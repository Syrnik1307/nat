from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from core.models import AuditLog
from accounts.notifications import send_telegram_notification
from .models import Homework, StudentSubmission, Answer
from .serializers import HomeworkSerializer, HomeworkStudentSerializer, StudentSubmissionSerializer
from .permissions import IsTeacherHomework, IsStudentSubmission
from .tasks import notify_student_graded


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

    def get_serializer_class(self):
        """Для учеников возвращаем урезанный сериализатор без баллов и is_correct."""
        user = getattr(self.request, 'user', None)
        if user and user.is_authenticated and getattr(user, 'role', None) == 'student':
            return HomeworkStudentSerializer
        return super().get_serializer_class()

    def perform_create(self, serializer):
        homework = serializer.save()
        self._notify_students_about_new_homework(homework)

    def _notify_students_about_new_homework(self, homework: Homework):
        lesson = getattr(homework, 'lesson', None)
        if not lesson or not getattr(lesson, 'group', None):
            return
        students = list(lesson.group.students.filter(is_active=True))
        if not students:
            return

        teacher_name = homework.teacher.get_full_name() or homework.teacher.email
        start_local = timezone.localtime(lesson.start_time) if lesson.start_time else None
        scheduled_line = ''
        if start_local:
            scheduled_line = f"\nСтарт урока: {start_local.strftime('%d.%m %H:%M')}"

        message = (
            f"📚 Новое домашнее задание: {homework.title}\n"
            f"Преподаватель: {teacher_name}\n"
            f"Группа: {lesson.group.name}" 
            f"{scheduled_line}\n"
            "Зайдите в Teaching Panel, чтобы посмотреть детали."
        )

        for student in students:
            send_telegram_notification(student, 'new_homework', message)


class StudentSubmissionViewSet(viewsets.ModelViewSet):
    queryset = StudentSubmission.objects.all().select_related('homework', 'student')
    serializer_class = StudentSubmissionSerializer
    permission_classes = [IsStudentSubmission]
    # Ограничиваем частоту сабмитов (см. DEFAULT_THROTTLE_RATES['submissions'])
    throttle_scope = 'submissions'

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

    def perform_create(self, serializer):
        submission = serializer.save()
        self._notify_teacher_submission(submission)

    @staticmethod
    def _format_display_name(user):
        if not user:
            return 'Неизвестный пользователь'
        full_name = ''
        if hasattr(user, 'get_full_name'):
            full_name = user.get_full_name()
        return full_name or user.email

    def _notify_teacher_submission(self, submission: StudentSubmission):
        teacher = getattr(submission.homework, 'teacher', None)
        if not teacher:
            return
        student_name = self._format_display_name(submission.student)
        hw_title = submission.homework.title
        message = (
            f"📘 Новая сдача ДЗ\n"
            f"{student_name} отправил(а) '{hw_title}'.\n"
            f"Откройте Teaching Panel, чтобы проверить работу."
        )
        send_telegram_notification(teacher, 'homework_submitted', message)
    
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
            self._notify_student_graded(submission)
        
        # Возвращаем обновленные данные
        serializer = self.get_serializer(submission)
        return Response(serializer.data)

    def _notify_student_graded(self, submission: StudentSubmission):
        student = submission.student
        teacher_name = self._format_display_name(submission.homework.teacher)
        score = submission.total_score or 0
        message = (
            f"✅ '{submission.homework.title}' проверено.\n"
            f"Преподаватель: {teacher_name}.\n"
            f"Итоговый балл: {score}."
        )
        send_telegram_notification(student, 'homework_graded', message)
