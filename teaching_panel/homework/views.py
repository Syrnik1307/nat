import json

from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q
from core.models import AuditLog
from accounts.notifications import send_telegram_notification
from .models import Homework, StudentSubmission, Answer
from .serializers import HomeworkSerializer, HomeworkStudentSerializer, StudentSubmissionSerializer
from .permissions import IsTeacherHomework, IsStudentSubmission


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
                # Студенты видят только опубликованные ДЗ из своих групп
                # .distinct() нужен т.к. студент может быть в нескольких группах,
                # что приводит к дубликатам при JOIN
                return (qs.filter(lesson__group__students=user) | qs.filter(teacher__teaching_groups__students=user)).filter(status='published').distinct()
        return qs.none()

    def get_serializer_class(self):
        """Для учеников возвращаем урезанный сериализатор без баллов и is_correct."""
        user = getattr(self.request, 'user', None)
        if user and user.is_authenticated and getattr(user, 'role', None) == 'student':
            return HomeworkStudentSerializer
        return super().get_serializer_class()

    def perform_create(self, serializer):
        # При создании ДЗ оно обычно в статусе draft.
        # Уведомления студентам должны уходить только при publish.
        serializer.save()

    @action(detail=True, methods=['post'], url_path='publish')
    def publish(self, request, pk=None):
        """Опубликовать домашнее задание"""
        homework = self.get_object()
        
        # Проверки
        if homework.status == 'published':
            return Response(
                {'detail': 'ДЗ уже опубликовано'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not homework.questions.exists():
            return Response(
                {'detail': 'Добавьте хотя бы один вопрос'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Публикация
        homework.status = 'published'
        homework.published_at = timezone.now()
        homework.save()
        
        # Отправить уведомления студентам
        self._notify_students_about_new_homework(homework)
        
        return Response({
            'status': 'success',
            'message': 'ДЗ опубликовано',
            'homework_id': homework.id,
            'published_at': homework.published_at,
        })

    @action(detail=False, methods=['post'], url_path='upload-file')
    def upload_file(self, request):
        """
        Загрузить файл (изображение или аудио) для вопроса домашки в Google Drive
        
        POST /api/homework/homeworks/upload-file/
        Body (multipart/form-data):
            - file: файл (изображение или аудио)
            - file_type: 'image' или 'audio'
        
        Returns:
            {
                'url': 'https://drive.google.com/...',
                'file_id': 'gdrive_file_id',
                'file_name': 'original_filename.jpg',
                'mime_type': 'image/jpeg'
            }
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Проверка прав: только учителя
        if not request.user.is_authenticated or getattr(request.user, 'role', None) != 'teacher':
            return Response(
                {'detail': 'Только учителя могут загружать файлы'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Получаем файл из request
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response(
                {'detail': 'Файл не найден в запросе'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        file_type = request.data.get('file_type', 'image')
        
        # Валидация MIME типа
        allowed_image_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        allowed_audio_types = ['audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/ogg', 'audio/mp4']
        
        mime_type = uploaded_file.content_type
        
        if file_type == 'image' and mime_type not in allowed_image_types:
            return Response(
                {'detail': f'Неподдерживаемый тип изображения: {mime_type}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if file_type == 'audio' and mime_type not in allowed_audio_types:
            return Response(
                {'detail': f'Неподдерживаемый тип аудио: {mime_type}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверка размера файла (макс 50 MB)
        max_size = 50 * 1024 * 1024
        if uploaded_file.size > max_size:
            return Response(
                {'detail': f'Файл слишком большой. Максимум: 50 MB'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Используем локальное хранение вместо Google Drive
            import os
            import time
            import uuid
            from django.conf import settings
            from django.utils.text import get_valid_filename
            
            # БЕЗОПАСНАЯ санитизация имени файла (защита от Path Traversal)
            timestamp = int(time.time())
            # 1. Убираем путь (../../../etc/passwd → passwd)
            original_name = os.path.basename(uploaded_file.name)
            # 2. Удаляем все опасные символы
            safe_name = get_valid_filename(original_name)
            # 3. Добавляем уникальный идентификатор для предотвращения коллизий
            file_name = f"homework_teacher{request.user.id}_{timestamp}_{uuid.uuid4().hex[:8]}_{safe_name}"
            
            # Создаём директорию для homework файлов
            homework_media_dir = os.path.join(settings.MEDIA_ROOT, 'homework_files')
            os.makedirs(homework_media_dir, exist_ok=True)
            
            # Путь к файлу
            file_path = os.path.join(homework_media_dir, file_name)
            
            # Сохраняем файл на диск
            with open(file_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            
            # Логирование
            logger.info(
                f"Teacher {request.user.email} uploaded homework file: "
                f"{file_name} ({mime_type}, {uploaded_file.size} bytes) to local storage"
            )
            
            # Генерируем URL для доступа
            file_url = f"{settings.MEDIA_URL}homework_files/{file_name}"
            
            # Возвращаем URL для встраивания в вопрос
            return Response({
                'status': 'success',
                'url': file_url,
                'download_url': file_url,
                'file_id': file_name,
                'file_name': uploaded_file.name,
                'mime_type': mime_type,
                'size': uploaded_file.size
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Failed to upload homework file: {e}", exc_info=True)
            return Response(
                {'detail': f'Ошибка загрузки файла: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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
    queryset = StudentSubmission.objects.all().select_related(
        'homework', 'homework__lesson', 'homework__lesson__group', 'student'
    ).prefetch_related('student__enrolled_groups')
    serializer_class = StudentSubmissionSerializer
    permission_classes = [IsStudentSubmission]
    # Ограничиваем частоту сабмитов (см. DEFAULT_THROTTLE_RATES['submissions'])
    throttle_scope = 'submissions'

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_authenticated:
            if getattr(user, 'role', None) == 'student':
                qs = qs.filter(student=user)
            elif getattr(user, 'role', None) == 'teacher':
                qs = qs.filter(homework__teacher=user)
        else:
            return qs.none()
        
        # Фильтрация по query параметрам
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        homework_filter = self.request.query_params.get('homework')
        if homework_filter:
            try:
                qs = qs.filter(homework_id=int(homework_filter))
            except (TypeError, ValueError):
                pass
        
        # Фильтрация по индивидуальным/групповым
        individual = self.request.query_params.get('individual')
        group_filter = self.request.query_params.get('group_id')
        if individual == '1':
            qs = qs.filter(homework__lesson__group__isnull=True)
            if getattr(user, 'role', None) == 'teacher':
                qs = qs.exclude(student__enrolled_groups__teacher=user)
        elif group_filter:
            qs = qs.filter(
                Q(homework__lesson__group__id=group_filter) |
                Q(
                    homework__lesson__group__isnull=True,
                    student__enrolled_groups__id=group_filter,
                    student__enrolled_groups__teacher=user
                )
            ).distinct()
        
        # Для детального просмотра (retrieve) подгружаем ответы
        if self.action == 'retrieve':
            qs = qs.prefetch_related(
                'answers', 'answers__question', 'answers__selected_choices'
            )
        
        # Стабильная сортировка: сначала по группе, затем по студенту и дате
        return qs.order_by('homework__lesson__group__name', 'student__last_name', 'student__first_name', '-created_at')

    # --- Student flows -------------------------------------------------
    def _upsert_answers(self, submission: StudentSubmission, answers_payload: dict):
        """Создать или обновить ответы студента в зависимости от типа вопроса."""
        if not answers_payload:
            return

        homework = submission.homework
        use_ai = homework.ai_grading_enabled  # Проверяем настройку AI

        questions_map = {
            q.id: q for q in homework.questions.all().prefetch_related('choices')
        }

        for question_id, raw_value in answers_payload.items():
            try:
                qid = int(question_id)
            except (TypeError, ValueError):
                continue

            question = questions_map.get(qid)
            if not question:
                continue

            answer_obj, _ = Answer.objects.get_or_create(submission=submission, question=question)

            qtype = question.question_type
            config = question.config or {}
            
            # Helper function to resolve choice ID (handles both numeric and legacy 'opt-X' format)
            def resolve_choice_id(val, question_obj):
                """Convert frontend choice value to database Choice ID."""
                # Try direct integer conversion first
                try:
                    return int(val)
                except (TypeError, ValueError):
                    pass
                
                # Fallback: handle legacy 'opt-X' format by matching position in options
                if isinstance(val, str) and val.startswith('opt-'):
                    options = config.get('options', [])
                    for idx, opt in enumerate(options):
                        if opt.get('id') == val:
                            # Find the corresponding Choice by position
                            db_choices = list(question_obj.choices.all().order_by('id'))
                            if idx < len(db_choices):
                                return db_choices[idx].id
                return None
            
            # Нормализуем фронтовые значения
            if qtype == 'SINGLE_CHOICE':
                answer_obj.text_answer = ''
                choices = []
                if raw_value:
                    resolved = resolve_choice_id(raw_value, question)
                    if resolved:
                        choices = [resolved]
                answer_obj.selected_choices.set(choices)
            elif qtype == 'MULTI_CHOICE':
                answer_obj.text_answer = ''
                base_list = raw_value if isinstance(raw_value, (list, tuple)) else []
                choices = []
                for val in base_list:
                    resolved = resolve_choice_id(val, question)
                    if resolved:
                        choices.append(resolved)
                answer_obj.selected_choices.set(choices)
            elif qtype in {'TEXT'}:
                answer_obj.selected_choices.clear()
                answer_obj.text_answer = raw_value or ''
            else:
                # Сложные типы храним в text_answer как JSON
                answer_obj.selected_choices.clear()
                try:
                    answer_obj.text_answer = json.dumps(raw_value)
                except TypeError:
                    answer_obj.text_answer = ''

            answer_obj.evaluate(use_ai=use_ai)
            answer_obj.save()

        submission.compute_auto_score()

    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated])
    def answer(self, request, pk=None):
        """Сохранить промежуточные ответы ученика (автосохранение)."""
        submission = self.get_object()
        if request.user != submission.student:
            return Response({'error': 'Доступ только для автора попытки'}, status=status.HTTP_403_FORBIDDEN)
        if submission.status != 'in_progress':
            return Response({'error': 'Работа уже отправлена или проверена'}, status=status.HTTP_400_BAD_REQUEST)

        answers_payload = request.data.get('answers', {})
        self._upsert_answers(submission, answers_payload)
        return Response({'status': 'saved', 'total_score': submission.total_score})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def submit(self, request, pk=None):
        """Финальная отправка работы учеником."""
        submission = self.get_object()
        if request.user != submission.student:
            return Response({'error': 'Доступ только для автора попытки'}, status=status.HTTP_403_FORBIDDEN)
        if submission.status in ('submitted', 'graded'):
            return Response({'error': 'Работа уже отправлена'}, status=status.HTTP_400_BAD_REQUEST)

        # Если ответы переданы вместе с submit — сначала сохраним их
        answers_payload = request.data.get('answers')
        if answers_payload:
            self._upsert_answers(submission, answers_payload)

        submission.submitted_at = timezone.now()
        
        # Проверяем, есть ли ответы требующие ручной проверки
        needs_manual = submission.answers.filter(needs_manual_review=True).exists()
        
        if needs_manual:
            # Есть ответы для ручной проверки — статус submitted
            submission.status = 'submitted'
            submission.save(update_fields=['status', 'submitted_at', 'total_score'])
            # Уведомляем учителя о необходимости проверки
            self._notify_teacher_submission(submission)
        else:
            # Все ответы проверены автоматически — сразу graded
            submission.status = 'graded'
            submission.graded_at = timezone.now()
            submission.save(update_fields=['status', 'submitted_at', 'graded_at', 'total_score'])
            # Уведомляем ученика о результате
            self._notify_student_graded(submission)
            # Уведомляем учителя что работа автоматически проверена
            self._notify_teacher_auto_graded(submission)

        serializer = self.get_serializer(submission)
        return Response(serializer.data)

    def perform_create(self, serializer):
        # Просто создаём submission без уведомления.
        # Уведомление учителю отправляется только при финальном submit.
        serializer.save()

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

    def _notify_teacher_auto_graded(self, submission: StudentSubmission):
        """Уведомить учителя что работа автоматически проверена."""
        teacher = getattr(submission.homework, 'teacher', None)
        if not teacher:
            return
        student_name = self._format_display_name(submission.student)
        hw_title = submission.homework.title
        score = submission.total_score or 0
        max_score = sum(q.points for q in submission.homework.questions.all()) or 100
        percent = round((score / max_score) * 100) if max_score > 0 else 0
        message = (
            f"✅ Авто-проверка ДЗ\n"
            f"{student_name} сдал(а) '{hw_title}'.\n"
            f"Результат: {score}/{max_score} ({percent}%).\n"
            f"Работа проверена автоматически."
        )
        send_telegram_notification(teacher, 'homework_submitted', message)
    
    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated])
    def feedback(self, request, pk=None):
        """
        Добавить общий комментарий преподавателя к работе (не к отдельному ответу).
        
        PATCH /api/homework/submissions/{id}/feedback/
        {
            "score": 85,  // optional: итоговый балл
            "comment": "Хорошая работа! Обратите внимание на пункт 3.",
            "attachments": []  // optional: список вложений
        }
        """
        submission = self.get_object()

        status_before = submission.status
        
        # Проверяем права: только учитель этого задания
        if request.user != submission.homework.teacher:
            return Response(
                {'error': 'Только учитель, создавший задание, может оставлять комментарии'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        comment = request.data.get('comment', '')
        attachments = request.data.get('attachments', [])
        score = request.data.get('score')
        
        # Сохраняем комментарий
        submission.teacher_feedback_summary = {
            'text': comment,
            'attachments': attachments,
            'updated_at': timezone.now().isoformat()
        }
        
        # Обновляем балл если передан
        if score is not None:
            try:
                submission.total_score = int(score)
            except (ValueError, TypeError):
                return Response(
                    {'error': 'Некорректное значение score'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Обновляем статус на "проверено"
        if submission.status == 'submitted':
            submission.status = 'graded'
            submission.graded_at = timezone.now()
        
        submission.save()
        
        # Логируем действие
        AuditLog.log(
            user=request.user,
            action='feedback',
            content_object=submission,
            description=f'Оставлен комментарий к работе {submission.id}',
            metadata={
                'comment_length': len(comment),
                'attachments_count': len(attachments),
                'score': score,
            },
            request=request
        )
        
        # Уведомляем ученика только при первом переводе в graded
        if status_before == 'submitted' and submission.status == 'graded':
            self._notify_student_graded(submission)
        
        serializer = self.get_serializer(submission)
        return Response(serializer.data)
    
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
            submission.graded_at = timezone.now()
            submission.save(update_fields=['status', 'graded_at'])
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

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def complete_review(self, request, pk=None):
        """
        Завершить проверку работы: перевести в статус 'graded' если еще не проверена.
        
        POST /api/submissions/{id}/complete_review/
        """
        submission = self.get_object()
        
        # Проверяем права: только учитель этого задания
        if request.user != submission.homework.teacher:
            return Response(
                {'error': 'Только учитель, создавший задание, может завершить проверку'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Переводим в статус 'graded' если еще не переведена
        if submission.status != 'graded':
            submission.status = 'graded'
            submission.graded_at = timezone.now()
            submission.save(update_fields=['status', 'graded_at'])
            
            # Уведомляем ученика
            self._notify_student_graded(submission)
        
        serializer = self.get_serializer(submission)
        return Response(serializer.data)
