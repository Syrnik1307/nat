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
                is_template = self.request.query_params.get('is_template')
                if is_template == '1':
                    return qs.filter(teacher=user, is_template=True)
                if is_template == '0':
                    return qs.filter(teacher=user, is_template=False)
                # default: показываем обычные ДЗ
                return qs.filter(teacher=user, is_template=False)
            elif getattr(user, 'role', None) == 'student':
                # Студенты видят только опубликованные ДЗ из своих групп
                # .distinct() нужен т.к. студент может быть в нескольких группах,
                # что приводит к дубликатам при JOIN
                # 
                # Логика видимости:
                # 1. lesson__group__students=user - старый способ через урок
                # 2. assigned_groups__students=user - назначено всей группе
                # 3. assigned_students=user - назначено индивидуально
                # 4. group_assignments__group__students=user + нет ограничения по ученикам
                # 5. group_assignments__students=user - назначено конкретному ученику в группе
                # 6. submissions__student=user - уже есть попытка (для истории)
                return (
                    qs.filter(status='published', is_template=False).filter(
                        Q(lesson__group__students=user) |
                        Q(assigned_groups__students=user) |
                        Q(assigned_students=user) |
                        # Новая логика: через HomeworkGroupAssignment
                        # Ученик в группе И (нет ограничений ИЛИ ученик в списке students)
                        Q(group_assignments__group__students=user, group_assignments__students__isnull=True) |
                        Q(group_assignments__students=user) |
                        Q(submissions__student=user)
                    )
                ).distinct()
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
        Быстрая загрузка файла для вопроса домашки.
        
        Логика:
        1. Сохраняем файл локально (быстро)
        2. Возвращаем прокси-URL сразу
        3. В фоне мигрируем на Google Drive
        
        POST /api/homework/homeworks/upload-file/
        Body (multipart/form-data):
            - file: файл (изображение или аудио)
            - file_type: 'image' или 'audio'
        
        Returns:
            {
                'url': '/api/homework/file/<file_id>/',
                'file_id': 'unique_file_id',
                'file_name': 'original_filename.jpg',
                'mime_type': 'image/jpeg'
            }
        """
        import logging
        import os
        import uuid
        from django.conf import settings as django_settings
        from .models import HomeworkFile
        
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
            # Генерируем уникальный ID
            file_id = uuid.uuid4().hex
            
            # Сохраняем локально (быстро!)
            homework_media_dir = os.path.join(django_settings.MEDIA_ROOT, 'homework_files')
            os.makedirs(homework_media_dir, exist_ok=True)
            
            # Расширение из оригинального имени
            ext = os.path.splitext(uploaded_file.name)[1].lower() or '.bin'
            local_filename = f"{file_id}{ext}"
            local_path = os.path.join(homework_media_dir, local_filename)
            
            with open(local_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            
            # Создаём запись в БД
            hw_file = HomeworkFile.objects.create(
                id=file_id,
                teacher=request.user,
                original_name=uploaded_file.name,
                mime_type=mime_type,
                size=uploaded_file.size,
                storage=HomeworkFile.STORAGE_LOCAL,
                local_path=local_path,
            )
            
            proxy_url = hw_file.get_proxy_url()
            
            logger.info(
                f"Teacher {request.user.email} uploaded homework file locally: "
                f"{uploaded_file.name} -> {file_id} ({uploaded_file.size} bytes)"
            )
            
            # НЕ запускаем фоновую миграцию здесь!
            # Миграция выполняется cron job (management command) для масштабируемости.
            # При 1000 одновременных загрузках threading.Thread создаст 1000 потоков.
            # Вместо этого файлы остаются в storage=LOCAL и migrate_homework_files
            # обрабатывает их пачками с rate limiting.
            
            return Response({
                'status': 'success',
                'url': proxy_url,
                'download_url': proxy_url,
                'file_id': file_id,
                'file_name': uploaded_file.name,
                'mime_type': mime_type,
                'size': uploaded_file.size
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Failed to upload homework file: {e}", exc_info=True)
            return Response({'detail': f'Ошибка загрузки файла: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='upload-document-direct')
    def upload_document_direct(self, request):
        """
        Прямая загрузка документа на Google Drive.
        
        Для документов (PDF, DOCX, и т.д.) загрузка идёт сразу на GDrive,
        чтобы не занимать место на сервере и не создавать нагрузку при
        массовых загрузках.
        
        POST /api/homework/homeworks/upload-document-direct/
        Body (multipart/form-data):
            - file: файл документа
        
        Returns:
            {
                'url': 'https://drive.google.com/...',
                'file_id': 'unique_file_id',
                'file_name': 'document.pdf',
                'mime_type': 'application/pdf',
                'size': 12345
            }
        """
        import logging
        import os
        import uuid
        import tempfile
        from django.conf import settings as django_settings
        from django.core.cache import cache
        from .models import HomeworkFile
        
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
        
        mime_type = uploaded_file.content_type
        
        # Разрешённые типы документов
        allowed_document_types = [
            # PDF
            'application/pdf',
            # Word
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            # Excel
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            # PowerPoint
            'application/vnd.ms-powerpoint',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            # Text
            'text/plain',
            'text/csv',
            # Archives (для материалов)
            'application/zip',
            'application/x-rar-compressed',
            'application/x-7z-compressed',
        ]
        
        if mime_type not in allowed_document_types:
            return Response(
                {'detail': f'Неподдерживаемый тип документа: {mime_type}. '
                           f'Разрешены: PDF, Word, Excel, PowerPoint, TXT, CSV, ZIP'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверка размера файла (макс 100 MB для документов)
        max_size = 100 * 1024 * 1024
        if uploaded_file.size > max_size:
            return Response(
                {'detail': 'Файл слишком большой. Максимум: 100 MB'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from schedule.gdrive_utils import get_gdrive_manager
            
            # Генерируем уникальный ID
            file_id = uuid.uuid4().hex
            
            # Получаем GDrive manager
            gdrive = get_gdrive_manager()
            
            # Получаем/создаём папку Uploads учителя
            teacher_folders = gdrive.get_or_create_teacher_folder(request.user)
            homework_root_folder_id = teacher_folders.get('homework')
            
            # Кешируем uploads folder ID
            uploads_cache_key = f"gdrive_uploads_folder_{request.user.id}"
            uploads_folder_id = cache.get(uploads_cache_key)
            
            if not uploads_folder_id:
                try:
                    query = (
                        f"name='Uploads' and mimeType='application/vnd.google-apps.folder' "
                        f"and trashed=false and '{homework_root_folder_id}' in parents"
                    )
                    results = gdrive.service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
                    items = results.get('files', [])
                    if items:
                        uploads_folder_id = items[0]['id']
                    else:
                        uploads_folder_id = gdrive.create_folder('Uploads', homework_root_folder_id)
                except Exception:
                    uploads_folder_id = gdrive.create_folder('Uploads', homework_root_folder_id)
                
                cache.set(uploads_cache_key, uploads_folder_id, 86400)
            
            # Сохраняем во временный файл для загрузки
            ext = os.path.splitext(uploaded_file.name)[1].lower() or '.bin'
            storage_name = f"hw_{file_id}_{uploaded_file.name}"
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                for chunk in uploaded_file.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name
            
            try:
                # Загружаем на GDrive
                with open(tmp_path, 'rb') as f:
                    result = gdrive.upload_file(
                        f,
                        storage_name,
                        folder_id=uploads_folder_id,
                        mime_type=mime_type,
                        teacher=request.user
                    )
                
                gdrive_file_id = result['file_id']
                gdrive_url = gdrive.get_direct_download_link(gdrive_file_id)
                
                # Создаём запись в БД (сразу на GDrive)
                hw_file = HomeworkFile.objects.create(
                    id=file_id,
                    teacher=request.user,
                    original_name=uploaded_file.name,
                    mime_type=mime_type,
                    size=uploaded_file.size,
                    storage=HomeworkFile.STORAGE_GDRIVE,
                    gdrive_file_id=gdrive_file_id,
                    gdrive_url=gdrive_url,
                )
                
                logger.info(
                    f"Teacher {request.user.email} uploaded document directly to GDrive: "
                    f"{uploaded_file.name} -> {gdrive_file_id} ({uploaded_file.size} bytes)"
                )
                
                return Response({
                    'status': 'success',
                    'url': gdrive_url,
                    'download_url': gdrive_url,
                    'file_id': file_id,
                    'gdrive_file_id': gdrive_file_id,
                    'file_name': uploaded_file.name,
                    'mime_type': mime_type,
                    'size': uploaded_file.size
                }, status=status.HTTP_201_CREATED)
                
            finally:
                # Удаляем временный файл
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        
        except Exception as e:
            logger.error(f"Failed to upload document to GDrive: {e}", exc_info=True)
            return Response(
                {'detail': f'Ошибка загрузки документа: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='upload-student-answer', permission_classes=[IsAuthenticated])
    def upload_student_answer(self, request):
        """
        Загрузка файла студентом в качестве ответа на вопрос типа FILE_UPLOAD.
        
        POST /api/homework/upload-student-answer/
        Body (multipart/form-data):
            - file: файл (изображение или документ)
        
        Returns:
            {
                'url': '/api/homework/file/<file_id>/',
                'file_id': 'unique_file_id',
                'file_name': 'original_filename.jpg',
                'mime_type': 'image/jpeg',
                'size': 12345
            }
        """
        import logging
        import os
        import uuid
        from django.conf import settings as django_settings
        from .models import HomeworkFile
        
        logger = logging.getLogger(__name__)
        
        # Проверка прав: только аутентифицированные пользователи (студенты и учителя)
        if not request.user.is_authenticated:
            return Response(
                {'detail': 'Требуется авторизация'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Получаем файл из request
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response(
                {'detail': 'Файл не найден в запросе'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Валидация MIME типа - разрешаем изображения и документы
        allowed_types = [
            # Изображения
            'image/jpeg', 'image/png', 'image/gif', 'image/webp',
            # PDF
            'application/pdf',
            # Word
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            # Excel
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            # Text
            'text/plain',
        ]
        
        mime_type = uploaded_file.content_type
        
        if mime_type not in allowed_types:
            return Response(
                {'detail': f'Неподдерживаемый тип файла: {mime_type}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверка размера файла (макс 10 MB для студенческих ответов)
        max_size = 10 * 1024 * 1024
        if uploaded_file.size > max_size:
            return Response(
                {'detail': 'Файл слишком большой. Максимум: 10 MB'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Генерируем уникальный ID
            file_id = uuid.uuid4().hex
            
            # Сохраняем локально
            homework_media_dir = os.path.join(django_settings.MEDIA_ROOT, 'student_uploads')
            os.makedirs(homework_media_dir, exist_ok=True)
            
            # Расширение из оригинального имени
            ext = os.path.splitext(uploaded_file.name)[1].lower() or '.bin'
            local_filename = f"{file_id}{ext}"
            local_path = os.path.join(homework_media_dir, local_filename)
            
            with open(local_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            
            # Создаём запись в БД (студент может быть None для teacher - указываем как student)
            hw_file = HomeworkFile.objects.create(
                id=file_id,
                teacher=None,  # Для студентов teacher=None
                original_name=uploaded_file.name,
                mime_type=mime_type,
                size=uploaded_file.size,
                storage=HomeworkFile.STORAGE_LOCAL,
                local_path=local_path,
            )
            
            proxy_url = hw_file.get_proxy_url()
            
            logger.info(
                f"User {request.user.email} uploaded student answer file: "
                f"{uploaded_file.name} -> {file_id} ({uploaded_file.size} bytes)"
            )
            
            return Response({
                'status': 'success',
                'url': proxy_url,
                'file_id': file_id,
                'file_name': uploaded_file.name,
                'mime_type': mime_type,
                'size': uploaded_file.size
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Failed to upload student answer file: {e}", exc_info=True)
            return Response({'detail': f'Ошибка загрузки файла: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _notify_students_about_new_homework(self, homework: Homework):
        # Получатели: группы (assigned_groups) + индивидуальные ученики (assigned_students)
        students = set()
        try:
            for group in homework.assigned_groups.all():
                for st in group.students.filter(is_active=True):
                    students.add(st)
        except Exception:
            pass
        try:
            for st in homework.assigned_students.filter(is_active=True):
                students.add(st)
        except Exception:
            pass

        # Backward compat: если ДЗ привязано к уроку/группе — тоже уведомляем
        lesson = getattr(homework, 'lesson', None)
        if lesson and getattr(lesson, 'group', None):
            for st in lesson.group.students.filter(is_active=True):
                students.add(st)

        students = list(students)
        if not students:
            return

        teacher_name = homework.teacher.get_full_name() or homework.teacher.email
        start_local = timezone.localtime(lesson.start_time) if (lesson and lesson.start_time) else None
        scheduled_line = ''
        if start_local:
            scheduled_line = f"\nСтарт урока: {start_local.strftime('%d.%m %H:%M')}"

        group_label = ''
        try:
            group_names = list(homework.assigned_groups.values_list('name', flat=True)[:3])
            if group_names:
                group_label = f"\nГруппы: {', '.join(group_names)}"
        except Exception:
            pass
        if not group_label and lesson and getattr(lesson, 'group', None):
            group_label = f"\nГруппа: {lesson.group.name}"

        message = (
            f"📚 Новое домашнее задание: {homework.title}\n"
            f"Преподаватель: {teacher_name}\n"
            f"{group_label}"
            f"{scheduled_line}\n"
            "Зайдите в Teaching Panel, чтобы посмотреть детали."
        )

        for student in students:
            send_telegram_notification(student, 'new_homework', message)

    @action(detail=True, methods=['post'], url_path='save-as-template')
    def save_as_template(self, request, pk=None):
        """Создать шаблон (архив) на основе существующего ДЗ (с копией вложений)."""
        from django.db import transaction
        import copy as pycopy
        from django.conf import settings

        source = self.get_object()
        if source.is_template:
            return Response({'detail': 'Это уже шаблон'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            template = Homework.objects.create(
                teacher=source.teacher,
                lesson=None,
                title=source.title,
                description=source.description,
                status='archived',
                deadline=None,
                max_score=source.max_score,
                is_template=True,
                ai_grading_enabled=source.ai_grading_enabled,
                ai_provider=source.ai_provider,
                ai_grading_prompt=source.ai_grading_prompt,
            )

            # Создаём папку шаблона на Drive и копируем вложения
            gdrive = None
            assets_folder_id = None
            if getattr(settings, 'USE_GDRIVE_STORAGE', False):
                try:
                    from schedule.gdrive_utils import get_gdrive_manager
                    gdrive = get_gdrive_manager()
                    teacher_folders = gdrive.get_or_create_teacher_folder(request.user)
                    homework_root = teacher_folders.get('homework')

                    def get_or_create_subfolder(folder_name, parent_id):
                        query = (
                            f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' "
                            f"and trashed=false and '{parent_id}' in parents"
                        )
                        res = gdrive.service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
                        items = res.get('files', [])
                        if items:
                            return items[0]['id']
                        return gdrive.create_folder(folder_name, parent_id)

                    templates_root = get_or_create_subfolder('Templates', homework_root)
                    template_folder = gdrive.create_folder(f"Template_{template.id}", templates_root)
                    assets_folder_id = get_or_create_subfolder('Assets', template_folder)
                    template.gdrive_folder_id = template_folder
                    template.save(update_fields=['gdrive_folder_id'])
                except Exception:
                    gdrive = None
                    assets_folder_id = None

            from .models import Question as QModel, Choice as CModel

            for q in source.questions.all().prefetch_related('choices'):
                cfg = pycopy.deepcopy(q.config) if isinstance(q.config, dict) else {}

                if gdrive and assets_folder_id:
                    for key_url, key_id in (('imageUrl', 'imageFileId'), ('audioUrl', 'audioFileId')):
                        file_id = cfg.get(key_id)
                        if file_id:
                            try:
                                copied = gdrive.copy_file(file_id, parent_folder_id=assets_folder_id)
                                new_id = copied.get('file_id')
                                if new_id:
                                    cfg[key_id] = new_id
                                    cfg[key_url] = gdrive.get_direct_download_link(new_id)
                            except Exception:
                                pass

                created_q = QModel.objects.create(
                    homework=template,
                    prompt=q.prompt,
                    question_type=q.question_type,
                    points=q.points,
                    order=q.order,
                    config=cfg,
                )
                for c in q.choices.all():
                    CModel.objects.create(question=created_q, text=c.text, is_correct=c.is_correct)

        return Response({'status': 'success', 'template_id': template.id}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='instantiate')
    def instantiate(self, request, pk=None):
        """Создать копию ДЗ из шаблона и назначить группам/ученикам (с копией вложений)."""
        from django.db import transaction
        import copy as pycopy
        from django.conf import settings

        template = self.get_object()
        if not template.is_template:
            return Response({'detail': 'instantiate доступен только для шаблонов'}, status=status.HTTP_400_BAD_REQUEST)

        title = request.data.get('title') or template.title
        description = request.data.get('description') or template.description
        from django.utils.dateparse import parse_datetime
        deadline_raw = request.data.get('deadline')
        deadline = parse_datetime(deadline_raw) if deadline_raw else None
        max_score = request.data.get('max_score')
        group_ids = request.data.get('group_ids') or []
        student_ids = request.data.get('student_ids') or []
        publish_now = bool(request.data.get('publish', True))

        with transaction.atomic():
            new_hw = Homework.objects.create(
                teacher=request.user,
                lesson=None,
                title=title,
                description=description,
                status='draft',
                deadline=deadline,
                max_score=int(max_score) if max_score is not None else template.max_score,
                is_template=False,
                ai_grading_enabled=template.ai_grading_enabled,
                ai_provider=template.ai_provider,
                ai_grading_prompt=template.ai_grading_prompt,
            )
            if group_ids:
                new_hw.assigned_groups.set(group_ids)
            if student_ids:
                new_hw.assigned_students.set(student_ids)

            gdrive = None
            assets_folder_id = None
            if getattr(settings, 'USE_GDRIVE_STORAGE', False):
                try:
                    from schedule.gdrive_utils import get_gdrive_manager
                    gdrive = get_gdrive_manager()
                    teacher_folders = gdrive.get_or_create_teacher_folder(request.user)
                    homework_root = teacher_folders.get('homework')

                    def get_or_create_subfolder(folder_name, parent_id):
                        query = (
                            f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' "
                            f"and trashed=false and '{parent_id}' in parents"
                        )
                        res = gdrive.service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
                        items = res.get('files', [])
                        if items:
                            return items[0]['id']
                        return gdrive.create_folder(folder_name, parent_id)

                    assignments_root = get_or_create_subfolder('Assignments', homework_root)
                    hw_folder = gdrive.create_folder(f"HW_{new_hw.id}", assignments_root)
                    assets_folder_id = get_or_create_subfolder('Assets', hw_folder)
                    new_hw.gdrive_folder_id = hw_folder
                    new_hw.save(update_fields=['gdrive_folder_id'])
                except Exception:
                    gdrive = None
                    assets_folder_id = None

            from .models import Question as QModel, Choice as CModel
            for q in template.questions.all().prefetch_related('choices'):
                cfg = pycopy.deepcopy(q.config) if isinstance(q.config, dict) else {}
                if gdrive and assets_folder_id:
                    for key_url, key_id in (('imageUrl', 'imageFileId'), ('audioUrl', 'audioFileId')):
                        file_id = cfg.get(key_id)
                        if file_id:
                            try:
                                copied = gdrive.copy_file(file_id, parent_folder_id=assets_folder_id)
                                new_id = copied.get('file_id')
                                if new_id:
                                    cfg[key_id] = new_id
                                    cfg[key_url] = gdrive.get_direct_download_link(new_id)
                            except Exception:
                                pass
                created_q = QModel.objects.create(
                    homework=new_hw,
                    prompt=q.prompt,
                    question_type=q.question_type,
                    points=q.points,
                    order=q.order,
                    config=cfg,
                )
                for c in q.choices.all():
                    CModel.objects.create(question=created_q, text=c.text, is_correct=c.is_correct)

            if publish_now:
                new_hw.status = 'published'
                new_hw.published_at = timezone.now()
                new_hw.save(update_fields=['status', 'published_at'])
                self._notify_students_about_new_homework(new_hw)

        return Response({'status': 'success', 'homework_id': new_hw.id}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='duplicate-and-assign')
    def duplicate_and_assign(self, request, pk=None):
        """
        Дублировать или перенести ДЗ в другие группы/ученикам.
        
        POST /api/homework/{id}/duplicate-and-assign/
        Body:
        {
            "mode": "duplicate" | "move",  // дублировать или перенести
            "group_assignments": [
                {
                    "group_id": 1,
                    "student_ids": [5, 7],  // [] = все ученики группы
                    "deadline": "2025-02-01T23:59:00Z"  // опционально
                }
            ],
            "individual_student_ids": [10, 11],  // индивидуальные ученики без группы
            "deadline": "2025-02-01T23:59:00Z",  // общий дедлайн (если не указан персональный)
            "publish": true  // опубликовать сразу
        }
        """
        from django.db import transaction
        import copy as pycopy
        from django.conf import settings
        from .models import HomeworkGroupAssignment

        source = self.get_object()
        if source.is_template:
            return Response(
                {'detail': 'Для шаблонов используйте /instantiate/'},
                status=status.HTTP_400_BAD_REQUEST
            )

        mode = request.data.get('mode', 'duplicate')
        group_assignments_data = request.data.get('group_assignments', [])
        individual_student_ids = request.data.get('individual_student_ids', [])
        global_deadline = request.data.get('deadline')
        publish_now = bool(request.data.get('publish', False))

        from django.utils.dateparse import parse_datetime
        parsed_deadline = parse_datetime(global_deadline) if global_deadline else source.deadline

        with transaction.atomic():
            if mode == 'move':
                # Перенос: обновляем существующее ДЗ
                homework = source
                # Очищаем старые назначения
                homework.assigned_groups.clear()
                homework.assigned_students.clear()
                homework.group_assignments.all().delete()
                
                if parsed_deadline:
                    homework.deadline = parsed_deadline
                    homework.save(update_fields=['deadline'])
            else:
                # Дублирование: создаём копию
                homework = Homework.objects.create(
                    teacher=request.user,
                    lesson=None,
                    title=source.title,
                    description=source.description,
                    status='draft',
                    deadline=parsed_deadline,
                    max_score=source.max_score,
                    is_template=False,
                    ai_grading_enabled=source.ai_grading_enabled,
                    ai_provider=source.ai_provider,
                    ai_grading_prompt=source.ai_grading_prompt,
                )

                # Копируем вопросы с вложениями
                gdrive = None
                assets_folder_id = None
                if getattr(settings, 'USE_GDRIVE_STORAGE', False):
                    try:
                        from schedule.gdrive_utils import get_gdrive_manager
                        gdrive = get_gdrive_manager()
                        teacher_folders = gdrive.get_or_create_teacher_folder(request.user)
                        homework_root = teacher_folders.get('homework')

                        def get_or_create_subfolder(folder_name, parent_id):
                            query = (
                                f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' "
                                f"and trashed=false and '{parent_id}' in parents"
                            )
                            res = gdrive.service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
                            items = res.get('files', [])
                            if items:
                                return items[0]['id']
                            return gdrive.create_folder(folder_name, parent_id)

                        assignments_root = get_or_create_subfolder('Assignments', homework_root)
                        hw_folder = gdrive.create_folder(f"HW_{homework.id}", assignments_root)
                        assets_folder_id = get_or_create_subfolder('Assets', hw_folder)
                        homework.gdrive_folder_id = hw_folder
                        homework.save(update_fields=['gdrive_folder_id'])
                    except Exception:
                        gdrive = None
                        assets_folder_id = None

                from .models import Question as QModel, Choice as CModel
                for q in source.questions.all().prefetch_related('choices'):
                    cfg = pycopy.deepcopy(q.config) if isinstance(q.config, dict) else {}
                    if gdrive and assets_folder_id:
                        for key_url, key_id in (('imageUrl', 'imageFileId'), ('audioUrl', 'audioFileId')):
                            file_id = cfg.get(key_id)
                            if file_id:
                                try:
                                    copied = gdrive.copy_file(file_id, parent_folder_id=assets_folder_id)
                                    new_id = copied.get('file_id')
                                    if new_id:
                                        cfg[key_id] = new_id
                                        cfg[key_url] = gdrive.get_direct_download_link(new_id)
                                except Exception:
                                    pass
                    created_q = QModel.objects.create(
                        homework=homework,
                        prompt=q.prompt,
                        question_type=q.question_type,
                        points=q.points,
                        order=q.order,
                        config=cfg,
                    )
                    for c in q.choices.all():
                        CModel.objects.create(question=created_q, text=c.text, is_correct=c.is_correct)

            # Создаём назначения группам с конкретными учениками
            for ga_data in group_assignments_data:
                group_id = ga_data.get('group_id')
                student_ids = ga_data.get('student_ids', [])
                ga_deadline = ga_data.get('deadline')
                
                if not group_id:
                    continue
                
                parsed_ga_deadline = parse_datetime(ga_deadline) if ga_deadline else None
                
                assignment = HomeworkGroupAssignment.objects.create(
                    homework=homework,
                    group_id=group_id,
                    deadline=parsed_ga_deadline
                )
                if student_ids:
                    assignment.students.set(student_ids)
                
                # Также добавляем группу в assigned_groups для обратной совместимости
                homework.assigned_groups.add(group_id)

            # Добавляем индивидуальных учеников
            if individual_student_ids:
                homework.assigned_students.set(individual_student_ids)

            if publish_now:
                homework.status = 'published'
                homework.published_at = timezone.now()
                homework.save(update_fields=['status', 'published_at'])
                self._notify_students_about_new_homework(homework)

        action_label = 'перенесено' if mode == 'move' else 'продублировано'
        return Response({
            'status': 'success',
            'message': f'ДЗ успешно {action_label}',
            'homework_id': homework.id,
            'mode': mode,
            'groups_assigned': len(group_assignments_data),
            'individual_students': len(individual_student_ids),
        }, status=status.HTTP_200_OK if mode == 'move' else status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='assignment-details')
    def assignment_details(self, request, pk=None):
        """
        Получить детали назначений ДЗ: группы с учениками.
        GET /api/homework/{id}/assignment-details/
        """
        from .models import HomeworkGroupAssignment
        
        homework = self.get_object()
        
        # Собираем информацию о назначениях
        group_assignments = []
        for ga in homework.group_assignments.select_related('group').prefetch_related('students', 'group__students'):
            assigned_students = list(ga.students.values('id', 'email', 'first_name', 'last_name'))
            all_group_students = list(ga.group.students.filter(is_active=True).values('id', 'email', 'first_name', 'last_name'))
            
            group_assignments.append({
                'group_id': ga.group.id,
                'group_name': ga.group.name,
                'deadline': ga.deadline.isoformat() if ga.deadline else None,
                'all_students': len(assigned_students) == 0,  # True если назначено всем
                'assigned_students': assigned_students if assigned_students else all_group_students,
                'students_in_group': all_group_students,
            })
        
        # Группы через старый механизм (assigned_groups без HomeworkGroupAssignment)
        existing_ga_group_ids = set(ga['group_id'] for ga in group_assignments)
        for group in homework.assigned_groups.prefetch_related('students'):
            if group.id not in existing_ga_group_ids:
                all_students = list(group.students.filter(is_active=True).values('id', 'email', 'first_name', 'last_name'))
                group_assignments.append({
                    'group_id': group.id,
                    'group_name': group.name,
                    'deadline': homework.deadline.isoformat() if homework.deadline else None,
                    'all_students': True,
                    'assigned_students': all_students,
                    'students_in_group': all_students,
                })
        
        # Индивидуальные ученики
        individual_students = list(homework.assigned_students.values('id', 'email', 'first_name', 'last_name'))
        
        return Response({
            'homework_id': homework.id,
            'title': homework.title,
            'deadline': homework.deadline.isoformat() if homework.deadline else None,
            'group_assignments': group_assignments,
            'individual_students': individual_students,
        })

    @action(detail=True, methods=['get'], url_path='my-answers', permission_classes=[IsAuthenticated])
    def my_answers(self, request, pk=None):
        """
        Получить свои ответы на ДЗ (для студента).
        GET /api/homework/{id}/my-answers/
        
        Возвращает ответы только если:
        1. У ученика есть сабмит
        2. Сабмит в статусе submitted или graded  
        3. allow_view_answers=True на ДЗ
        """
        homework = self.get_object()
        user = request.user
        
        # Проверяем что это студент
        if getattr(user, 'role', None) != 'student':
            return Response({'error': 'Доступно только для учеников'}, status=status.HTTP_403_FORBIDDEN)
        
        # Проверяем allow_view_answers
        if not getattr(homework, 'allow_view_answers', True):
            return Response({'error': 'Преподаватель запретил просмотр ответов для этого задания'}, status=status.HTTP_403_FORBIDDEN)
        
        # Находим submission ученика
        try:
            submission = StudentSubmission.objects.get(homework=homework, student=user)
        except StudentSubmission.DoesNotExist:
            return Response({'error': 'У вас нет попытки для этого задания'}, status=status.HTTP_404_NOT_FOUND)
        
        # Проверяем статус - можно смотреть только после сдачи
        if submission.status == 'in_progress':
            return Response({'error': 'Сначала завершите и сдайте работу'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Собираем вопросы
        questions = []
        for q in homework.questions.all().order_by('order'):
            questions.append({
                'id': q.id,
                'prompt': q.prompt,
                'question_type': 'MULTIPLE_CHOICE' if q.question_type == 'MULTI_CHOICE' else q.question_type,
                'points': q.points,
                'order': q.order,
                'config': q.config or {},
            })
        
        # Собираем ответы
        answers = []
        for answer in submission.answers.select_related('question').prefetch_related('selected_choices'):
            # Определяем правильность
            q = answer.question
            is_correct = None
            score = answer.auto_score if answer.auto_score is not None else answer.teacher_score
            
            # Для авто-проверяемых вопросов определяем правильность
            if q.question_type in ('SINGLE_CHOICE', 'MULTI_CHOICE'):
                if score is not None and q.points > 0:
                    is_correct = score >= q.points
            elif answer.teacher_score is not None:
                # Если есть оценка учителя
                is_correct = answer.teacher_score >= q.points if q.points > 0 else None
            
            # Получаем текст выбранных вариантов
            selected_choices_text = [c.text for c in answer.selected_choices.all()]
            
            answers.append({
                'question_id': q.id,
                'text_answer': answer.text_answer,
                'selected_choices': list(answer.selected_choices.values_list('id', flat=True)),
                'selected_choices_text': selected_choices_text,
                'score': score,
                'is_correct': is_correct,
                'teacher_feedback': answer.teacher_feedback,
            })
        
        # Вычисляем время
        time_spent_seconds = None
        if submission.submitted_at and submission.created_at:
            delta = submission.submitted_at - submission.created_at
            time_spent_seconds = int(delta.total_seconds())
        
        return Response({
            'homework_id': homework.id,
            'homework_title': homework.title,
            'status': submission.status,
            'total_score': submission.total_score,
            'max_score': sum(q.points for q in homework.questions.all()),
            'time_spent_seconds': time_spent_seconds,
            'submitted_at': submission.submitted_at.isoformat() if submission.submitted_at else None,
            'graded_at': submission.graded_at.isoformat() if submission.graded_at else None,
            'questions': questions,
            'answers': answers,
        })


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
        
        # Проверяем mutes
        from accounts.notifications import is_notification_muted
        student = submission.student
        
        # Получаем группу из homework (если есть)
        groups = submission.homework.assigned_groups.all()
        group = groups.first() if groups.exists() else None
        
        if is_notification_muted(teacher, 'homework_submitted', group=group, student=student):
            return
        
        student_name = self._format_display_name(submission.student)
        hw_title = submission.homework.title
        message = (
            f"Новая сдача ДЗ\n"
            f"{student_name} отправил(а) '{hw_title}'.\n"
            f"Откройте Lectio Space, чтобы проверить работу."
        )
        send_telegram_notification(teacher, 'homework_submitted', message)

    def _notify_teacher_auto_graded(self, submission: StudentSubmission):
        """Уведомить учителя что работа автоматически проверена."""
        teacher = getattr(submission.homework, 'teacher', None)
        if not teacher:
            return
        
        # Проверяем mutes
        from accounts.notifications import is_notification_muted
        student = submission.student
        
        # Получаем группу из homework (если есть)
        groups = submission.homework.assigned_groups.all()
        group = groups.first() if groups.exists() else None
        
        if is_notification_muted(teacher, 'homework_submitted', group=group, student=student):
            return
        
        student_name = self._format_display_name(submission.student)
        hw_title = submission.homework.title
        score = submission.total_score or 0
        max_score = sum(q.points for q in submission.homework.questions.all()) or 100
        percent = round((score / max_score) * 100) if max_score > 0 else 0
        message = (
            f"Авто-проверка ДЗ\n"
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


# ============================================================
# Прокси-endpoint для доступа к файлам домашек
# ============================================================

from django.http import HttpResponse, FileResponse, HttpResponseRedirect
from django.views import View


class HomeworkFileProxyView(View):
    """
    Прокси для доступа к файлам домашек.
    Отдаёт файл из локального хранилища или проксирует с GDrive.
    
    GET /api/homework/file/<file_id>/
    """
    
    def get(self, request, file_id):
        from .models import HomeworkFile
        import os
        import requests
        import re
        
        try:
            hw_file = HomeworkFile.objects.get(id=file_id)
        except HomeworkFile.DoesNotExist:
            return HttpResponse("File not found", status=404)
        
        # Если на GDrive - проксируем через lh3.googleusercontent.com
        if hw_file.storage == HomeworkFile.STORAGE_GDRIVE and hw_file.gdrive_url:
            gdrive_url = hw_file.gdrive_url
            file_id_match = None
            
            # Извлекаем file ID из разных форматов Google Drive URL
            patterns = [
                r'[?&]id=([a-zA-Z0-9_-]+)',  # /uc?id=FILE_ID
                r'/file/d/([a-zA-Z0-9_-]+)',  # /file/d/FILE_ID/view
                r'/open\?id=([a-zA-Z0-9_-]+)',  # /open?id=FILE_ID
            ]
            for pattern in patterns:
                match = re.search(pattern, gdrive_url)
                if match:
                    file_id_match = match.group(1)
                    break
            
            if file_id_match:
                # Используем lh3.googleusercontent.com для прямого доступа
                proxy_url = f'https://lh3.googleusercontent.com/d/{file_id_match}'
                try:
                    resp = requests.get(proxy_url, timeout=10, stream=True)
                    if resp.status_code == 200:
                        content_type = resp.headers.get('Content-Type', hw_file.mime_type or 'application/octet-stream')
                        response = HttpResponse(resp.content, content_type=content_type)
                        response['Content-Disposition'] = f'inline; filename="{hw_file.original_name}"'
                        response['Cache-Control'] = 'public, max-age=31536000'
                        return response
                except Exception as e:
                    print(f"[HomeworkFileProxyView] GDrive proxy error: {e}")
            
            # Fallback: редирект если проксирование не удалось
            return HttpResponseRedirect(gdrive_url)
        
        # Если локально - отдаём файл
        if hw_file.local_path and os.path.exists(hw_file.local_path):
            response = FileResponse(
                open(hw_file.local_path, 'rb'),
                content_type=hw_file.mime_type
            )
            response['Content-Disposition'] = f'inline; filename="{hw_file.original_name}"'
            # Кеширование на 1 год (файлы не меняются)
            response['Cache-Control'] = 'public, max-age=31536000'
            return response
        
        return HttpResponse("File not found", status=404)
