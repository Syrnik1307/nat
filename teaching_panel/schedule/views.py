from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.utils.dateparse import parse_datetime
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
from django.core.cache import cache
import hashlib
import logging
from datetime import datetime, timedelta
from .models import Group, Lesson, Attendance, RecurringLesson, LessonRecording, AuditLog, IndividualInviteCode, LessonTranscriptStats
from zoom_pool.models import ZoomAccount
from django.db.models import F
from .permissions import IsLessonOwnerOrReadOnly, IsGroupOwnerOrReadOnly, IsTeacherOrReadOnly
from .serializers import (
    GroupSerializer, 
    LessonSerializer, 
    LessonCalendarSerializer,
    LessonDetailSerializer,
    AttendanceSerializer,
    ZoomAccountSerializer,
    RecurringLessonSerializer,
    IndividualInviteCodeSerializer
)
# my_zoom_api_client удалён - каждый учитель использует свои credentials
from accounts.subscriptions_utils import require_active_subscription
from accounts.models import CustomUser

logger = logging.getLogger(__name__)


def _parse_ids_list(raw_value):
    """Парсим список идентификаторов из строки или массива."""
    if raw_value in (None, ''):
        return []
    if isinstance(raw_value, (list, tuple)):
        iterable = raw_value
    else:
        try:
            iterable = json.loads(raw_value)
        except (TypeError, ValueError, json.JSONDecodeError):
            iterable = [raw_value]

    ids = []
    for item in iterable:
        try:
            ids.append(int(item))
        except (TypeError, ValueError):
            continue
    return ids


def _get_video_duration(file_obj):
    """
    Извлекает длительность видео в секундах с помощью ffprobe.
    Возвращает None если не удалось определить.
    """
    import subprocess
    import tempfile
    import os
    
    try:
        # Сохраняем файл во временную директорию
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
            for chunk in file_obj.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name
        
        # Сбрасываем позицию чтения файла для дальнейшего использования
        file_obj.seek(0)
        
        # Запускаем ffprobe
        result = subprocess.run(
            [
                'ffprobe', '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                tmp_path
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Удаляем временный файл
        os.unlink(tmp_path)
        
        if result.returncode == 0 and result.stdout.strip():
            duration = float(result.stdout.strip())
            return int(duration)
        
        return None
    except Exception as e:
        logger.warning(f"Failed to get video duration: {e}")
        return None


def _user_has_recording_access(user, recording):
    role = getattr(user, 'role', None)
    if role == 'admin':
        return True
    if role == 'teacher':
        # Для записей с уроком: проверяем teacher урока
        # Для standalone записей: проверяем поле teacher записи
        if recording.lesson_id and recording.lesson:
            return recording.lesson.teacher_id == user.id
        return recording.teacher_id == user.id
    if role != 'student':
        return False

    # Для студентов: проверяем видимость
    if recording.visibility == LessonRecording.Visibility.ALL_TEACHER_GROUPS:
        # Для standalone записей teacher может быть в поле teacher
        teacher = recording.lesson.teacher if recording.lesson_id and recording.lesson else recording.teacher
        if teacher:
            return Group.objects.filter(teacher=teacher, students=user).exists()
        return False

    if recording.allowed_students.filter(id=user.id).exists():
        return True

    return recording.allowed_groups.filter(students=user).exists()


def log_audit(user, action, resource_type, resource_id=None, request=None, details=None):
    """Создать запись аудита.
    
    Args:
        user: Пользователь, выполняющий действие
        action: Тип действия (lesson_start, lesson_create и т.д.)
        resource_type: Тип ресурса (Lesson, ZoomAccount и т.д.)
        resource_id: ID ресурса
        request: HTTP request для извлечения IP и User-Agent
        details: Дополнительные детали (dict)
    """
    ip_address = None
    user_agent = ''
    
    if request:
        # Получить реальный IP (учитывая proxy)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]  # Ограничение длины
    
    AuditLog.objects.create(
        user=user,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        user_agent=user_agent,
        details=details or {}
    )


class GroupViewSet(viewsets.ModelViewSet):
    """
    ViewSet для работы с группами.
    Преподаватели могут создавать и управлять своими группами.
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    # Требуем аутентификацию + проверку владельца для мутаций
    permission_classes = [IsAuthenticated, IsGroupOwnerOrReadOnly]
    
    def get_queryset(self):
        """Фильтруем группы по преподавателю для аутентифицированных пользователей"""
        # ОПТИМИЗАЦИЯ: prefetch students и select_related teacher для избежания N+1
        queryset = super().get_queryset().select_related('teacher').prefetch_related('students')
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()
        if getattr(user, 'role', None) == 'teacher':
            return queryset.filter(teacher=user)
        if getattr(user, 'role', None) == 'student':
            return queryset.filter(students=user)
        return queryset.none()
    
    @action(detail=True, methods=['post'])
    def add_students(self, request, pk=None):
        """Добавить студентов в группу"""
        group = self.get_object()
        student_ids = request.data.get('student_ids', [])
        
        for student_id in student_ids:
            try:
                student = CustomUser.objects.get(id=student_id, role='student')
                group.students.add(student)
            except CustomUser.DoesNotExist:
                pass
        
        group.save()
        serializer = self.get_serializer(group)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def remove_students(self, request, pk=None):
        """Удалить студентов из группы"""
        group = self.get_object()
        student_ids = request.data.get('student_ids', [])
        
        for student_id in student_ids:
            try:
                student = CustomUser.objects.get(id=student_id, role='student')
                group.students.remove(student)
            except CustomUser.DoesNotExist:
                pass
        
        group.save()
        serializer = self.get_serializer(group)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def regenerate_code(self, request, pk=None):
        """Перегенерировать код приглашения для группы"""
        group = self.get_object()
        new_code = group.generate_invite_code()
        return Response({
            'invite_code': new_code,
            'message': 'Новый код приглашения создан'
        })
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def preview_by_code(self, request):
        """Получить информацию о группе по коду приглашения (без присоединения)"""
        invite_code = request.query_params.get('code', '').strip().upper()
        if not invite_code:
            return Response(
                {'error': 'Код приглашения не указан'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            group = Group.objects.select_related('teacher').get(invite_code=invite_code)
        except Group.DoesNotExist:
            return Response(
                {'error': 'Группа с таким кодом не найдена'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(group)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def join_by_code(self, request):
        """Присоединиться к группе по коду приглашения"""
        invite_code = request.data.get('invite_code', '').strip().upper()
        if not invite_code:
            return Response(
                {'error': 'Код приглашения не указан'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            group = Group.objects.get(invite_code=invite_code)
        except Group.DoesNotExist:
            return Response(
                {'error': 'Группа с таким кодом не найдена'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        user = request.user
        if user.role != 'student':
            return Response(
                {'error': 'Только ученики могут присоединяться к группам'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if group.students.filter(id=user.id).exists():
            return Response(
                {'message': 'Вы уже состоите в этой группе'},
                status=status.HTTP_200_OK
            )
        
        group.students.add(user)
        serializer = self.get_serializer(group)
        
        return Response({
            'message': f'Вы успешно присоединились к группе "{group.name}"',
            'group': serializer.data
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def transfer_student(self, request, pk=None):
        """
        Перенести ученика из одной группы в другую.
        Используется для перевода между индивидуальными и групповыми занятиями.
        """
        from_group = self.get_object()
        student_id = request.data.get('student_id')
        to_group_id = request.data.get('to_group_id')
        
        if not student_id or not to_group_id:
            return Response(
                {'error': 'Необходимо указать student_id и to_group_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            student = CustomUser.objects.get(id=student_id, role='student')
        except CustomUser.DoesNotExist:
            return Response(
                {'error': 'Ученик не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            to_group = Group.objects.get(id=to_group_id, teacher=request.user)
        except Group.DoesNotExist:
            return Response(
                {'error': 'Целевая группа не найдена или не принадлежит вам'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Проверяем что ученик в исходной группе
        if not from_group.students.filter(id=student_id).exists():
            return Response(
                {'error': 'Ученик не состоит в исходной группе'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Переносим
        from_group.students.remove(student)
        to_group.students.add(student)
        
        return Response({
            'message': f'Ученик успешно перенесён из "{from_group.name}" в "{to_group.name}"',
            'from_group': GroupSerializer(from_group).data,
            'to_group': GroupSerializer(to_group).data
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def all_students(self, request):
        """
        Получить всех студентов из групп учителя.
        Используется для выбора индивидуальной видимости материалов.
        """
        if request.user.role != 'teacher':
            return Response(
                {'error': 'Только для учителей'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        teacher_groups = Group.objects.filter(teacher=request.user).prefetch_related('students')
        students_dict = {}
        
        for group in teacher_groups:
            for student in group.students.all():
                if student.id not in students_dict:
                    students_dict[student.id] = {
                        'id': student.id,
                        'email': student.email,
                        'full_name': student.get_full_name() or student.email,
                        'group_name': group.name,
                        'group_id': group.id
                    }
        
        return Response(list(students_dict.values()))


class LessonViewSet(viewsets.ModelViewSet):
    """
    ViewSet для работы с занятиями.
    Поддерживает создание, редактирование, удаление занятий.
    """
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated, IsLessonOwnerOrReadOnly]

    def _include_recurring(self, request):
        flag = request.query_params.get('include_recurring')
        if flag is None:
            return False
        # Поддерживаем различные формы boolean из query params
        return str(flag).lower() in ('1', 'true', 'yes', 'on', '1.0')

    def _safe_parse_datetime(self, raw):
        """Парсим datetime/даты из query params, поддерживаем пробел вместо +."""
        from django.utils.dateparse import parse_date
        if not raw:
            return None
        raw_str = str(raw).replace(' ', '+')
        dt = parse_datetime(raw_str)
        if dt:
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt, timezone.get_current_timezone())
            return dt
        d = parse_date(raw_str)
        if d:
            tz = timezone.get_current_timezone()
            return timezone.make_aware(datetime.combine(d, datetime.min.time()), tz)
        if '+' in raw_str:
            head, tz_part = raw_str.rsplit('+', 1)
            tz_compact = tz_part.replace(':', '')
            dt = parse_datetime(f"{head}+{tz_compact}")
            if dt and timezone.is_naive(dt):
                dt = timezone.make_aware(dt, timezone.get_current_timezone())
            return dt
        return None

    def _resolve_list_range(self, request):
        """Определяем диапазон дат для разворачивания регулярных уроков."""
        from django.utils.dateparse import parse_date

        date_param = request.query_params.get('date')
        if date_param:
            parsed = parse_date(date_param)
            if parsed:
                tz = timezone.get_current_timezone()
                start_dt = timezone.make_aware(datetime.combine(parsed, datetime.min.time()), tz)
                end_dt = timezone.make_aware(datetime.combine(parsed, datetime.max.time()), tz)
                return start_dt, end_dt

        start_dt = self._safe_parse_datetime(request.query_params.get('start'))
        end_dt = self._safe_parse_datetime(request.query_params.get('end'))

        # Если указана только одна граница, задаём вторую по умолчанию
        if start_dt and not end_dt:
            end_dt = start_dt + timedelta(days=30)
        if end_dt and not start_dt:
            start_dt = end_dt - timedelta(days=30)

        # Полный дефолт: от сейчас на 30 дней вперёд
        if not start_dt and not end_dt:
            start_dt = timezone.now()
            end_dt = start_dt + timedelta(days=30)

        return start_dt, end_dt

    def _build_recurring_virtual_lessons(self, request, start_dt, end_dt, existing_queryset):
        """Разворачиваем RecurringLesson в виртуальные занятия в заданном диапазоне."""
        if not start_dt or not end_dt:
            return []

        recurring_qs = RecurringLesson.objects.all()
        user = request.user
        if user.is_authenticated:
            role = getattr(user, 'role', None)
            if role == 'teacher':
                recurring_qs = recurring_qs.filter(teacher=user)
            elif role == 'student':
                recurring_qs = recurring_qs.filter(group__students=user)

        teacher_id = request.query_params.get('teacher')
        group_id = request.query_params.get('group')
        if teacher_id:
            recurring_qs = recurring_qs.filter(teacher_id=teacher_id)
        if group_id:
            recurring_qs = recurring_qs.filter(group_id=group_id)

        def matches_week_type(week_type, date):
            if week_type == 'ALL':
                return True
            iso_week = date.isocalendar()[1]
            if week_type == 'UPPER':
                return iso_week % 2 == 0
            if week_type == 'LOWER':
                return iso_week % 2 == 1
            return True

        virtual_lessons = []
        current_date = start_dt.date()
        while current_date <= end_dt.date():
            for rl in recurring_qs:
                if not (rl.start_date <= current_date <= rl.end_date):
                    continue
                if current_date.weekday() != rl.day_of_week:
                    continue
                if not matches_week_type(rl.week_type, current_date):
                    continue

                start_local = timezone.make_aware(
                    datetime.combine(current_date, rl.start_time),
                    timezone.get_current_timezone()
                )
                end_local = timezone.make_aware(
                    datetime.combine(current_date, rl.end_time),
                    timezone.get_current_timezone()
                )

                # Пропускаем, если уже есть реальный урок группы на это время
                overlap = existing_queryset.filter(
                    group=rl.group,
                    start_time__lt=end_local,
                    end_time__gt=start_local
                ).exists()
                if overlap:
                    continue

                virtual_lessons.append({
                    'id': f'recurring-{rl.id}-{current_date.isoformat()}',
                    'recurring_lesson_id': rl.id,
                    'is_recurring': True,
                    'title': rl.title,
                    'group': rl.group_id,
                    'group_name': rl.group.name,
                    'teacher': rl.teacher_id,
                    'teacher_name': rl.teacher.get_full_name(),
                    'start_time': start_local.isoformat(),
                    'end_time': end_local.isoformat(),
                    'duration_minutes': int((end_local - start_local).total_seconds() / 60),
                    'topics': rl.topics,
                    'location': rl.location,
                    'zoom_meeting_id': None,
                    'zoom_join_url': None,
                    'zoom_start_url': None,
                    'zoom_password': None,
                    'record_lesson': False,
                    'recording_available_for_days': None,
                })
            current_date += timedelta(days=1)

        return virtual_lessons

    def list(self, request, *args, **kwargs):
        include_recurring = self._include_recurring(request)
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        lessons = list(serializer.data)

        if include_recurring:
            start_dt, end_dt = self._resolve_list_range(request)
            virtual_lessons = self._build_recurring_virtual_lessons(request, start_dt, end_dt, queryset)
            lessons.extend(virtual_lessons)
            lessons.sort(key=lambda x: x.get('start_time') or '')
            # Возвращаем как обычный массив без пагинации, так как регулярные уроки генерируются на лету
            return Response(lessons)
        else:
            # Для обычных уроков используем пагинацию
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            return Response(lessons)

    @action(detail=True, methods=['post'], url_path='join', permission_classes=[IsAuthenticated])
    def join(self, request, pk=None):
        """Вернуть ссылку для входа в Zoom для участника урока.

        POST /api/schedule/lessons/{id}/join/
        Доступ:
        - student: только если состоит в группе урока
        - teacher: только если он преподаватель урока
        - admin: всегда
        """
        lesson = self.get_object()
        user = request.user
        role = getattr(user, 'role', None)

        if role == 'admin':
            allowed = True
        elif role == 'teacher':
            allowed = (lesson.teacher_id == user.id)
        elif role == 'student':
            allowed = lesson.group.students.filter(id=user.id).exists()
        else:
            allowed = False

        if not allowed:
            return Response({'detail': 'Нет доступа к этому уроку'}, status=status.HTTP_403_FORBIDDEN)

        if not lesson.zoom_join_url:
            return Response(
                {'detail': 'Ссылка появится, когда преподаватель начнёт занятие'},
                status=status.HTTP_409_CONFLICT
            )

        return Response(
            {
                'zoom_join_url': lesson.zoom_join_url,
                'zoom_meeting_id': lesson.zoom_meeting_id,
                'zoom_password': lesson.zoom_password,
            },
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['post'], url_path='delete_recurring')
    def delete_recurring(self, request):
        """Удалить все уроки с одинаковым названием в одной группе"""
        title = request.data.get('title')
        group_id = request.data.get('group_id')
        
        if not title or not group_id:
            return Response({'detail': 'title и group_id обязательны'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Проверяем права: только учитель может удалять уроки своих групп
        if request.user.role != 'teacher':
            return Response({'detail': 'Только преподаватели могут удалять уроки'}, status=status.HTTP_403_FORBIDDEN)
        
        # Находим все похожие уроки
        lessons_to_delete = Lesson.objects.filter(
            title=title,
            group_id=group_id,
            teacher=request.user
        )
        
        count = lessons_to_delete.count()
        if count == 0:
            return Response({'detail': 'Уроки не найдены'}, status=status.HTTP_404_NOT_FOUND)
        
        # Удаляем все найденные уроки
        lessons_to_delete.delete()
        
        return Response({
            'status': 'deleted',
            'count': count,
            'message': f'Удалено уроков: {count}'
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'], url_path='upload_standalone_recording')
    def upload_standalone_recording(self, request):
        """Загрузить самостоятельное видео без привязки к уроку — напрямую в Google Drive"""
        # Требуем активную подписку
        try:
            require_active_subscription(request.user)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)
        
        if getattr(request.user, 'role', None) != 'teacher':
            return Response({'detail': 'Только преподаватели могут загружать видео'}, status=status.HTTP_403_FORBIDDEN)
        
        video_file = request.FILES.get('video')
        title = request.data.get('title', '').strip()
        
        if not video_file:
            return Response({'detail': 'Видео файл обязателен'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not title:
            return Response({'detail': 'Название обязательно для самостоятельного видео'}, status=status.HTTP_400_BAD_REQUEST)
        
        # БЕЗОПАСНОСТЬ: Проверка MIME-типа видео
        allowed_video_types = ['video/mp4', 'video/webm', 'video/mpeg', 'video/quicktime', 'video/x-msvideo', 'video/x-matroska']
        if video_file.content_type not in allowed_video_types:
            return Response(
                {'detail': f'Неподдерживаемый тип файла: {video_file.content_type}. Разрешены: MP4, WebM, MPEG, MOV, AVI, MKV'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверка лимита хранилища учителя
        from accounts.models import Subscription
        from accounts.gdrive_folder_service import check_storage_limit
        
        try:
            subscription = Subscription.objects.get(user=request.user)
        except Subscription.DoesNotExist:
            return Response({'detail': 'Подписка не найдена'}, status=status.HTTP_403_FORBIDDEN)
        
        allowed, message = check_storage_limit(subscription, video_file.size)
        if not allowed:
            return Response({'detail': message}, status=status.HTTP_400_BAD_REQUEST)
        
        privacy_type = request.data.get('privacy_type', 'all')
        allowed_groups = _parse_ids_list(request.data.get('allowed_groups'))
        allowed_students = _parse_ids_list(request.data.get('allowed_students'))
        
        # БЕЗОПАСНОСТЬ: Валидация что группы принадлежат учителю
        if allowed_groups:
            valid_group_ids = set(Group.objects.filter(
                id__in=allowed_groups, 
                teacher=request.user
            ).values_list('id', flat=True))
            invalid_groups = set(allowed_groups) - valid_group_ids
            if invalid_groups:
                return Response(
                    {'detail': f'Нет доступа к группам: {list(invalid_groups)}'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # БЕЗОПАСНОСТЬ: Валидация что студенты в группах учителя
        if allowed_students:
            from accounts.models import CustomUser
            teacher_student_ids = set(CustomUser.objects.filter(
                enrolled_groups__teacher=request.user,
                id__in=allowed_students
            ).values_list('id', flat=True))
            invalid_students = set(allowed_students) - teacher_student_ids
            if invalid_students:
                return Response(
                    {'detail': f'Нет доступа к студентам: {list(invalid_students)}'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        from django.conf import settings
        from django.utils.text import slugify, get_valid_filename
        import os
        import uuid
        from datetime import datetime
        
        # БЕЗОПАСНОСТЬ: Безопасное имя файла
        original_name = os.path.basename(video_file.name)
        safe_original = get_valid_filename(original_name)
        date_prefix = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_filename = f'{date_prefix}_{slugify(title)}_{uuid.uuid4().hex[:6]}_{safe_original}'
        
        # Загрузка в Google Drive
        gdrive_file_id = None
        play_url = None
        download_url = None
        storage_provider = 'local'
        
        if settings.USE_GDRIVE_STORAGE:
            try:
                from .gdrive_utils import get_gdrive_manager
                gdrive = get_gdrive_manager()
                
                # Получаем папку Recordings учителя
                teacher_folders = gdrive.get_or_create_teacher_folder(request.user)
                recordings_folder_id = teacher_folders.get('recordings', teacher_folders.get('root'))
                
                # Загружаем файл в Google Drive
                result = gdrive.upload_file(
                    file_path_or_object=video_file,
                    file_name=safe_filename,
                    folder_id=recordings_folder_id,
                    mime_type=video_file.content_type,
                    teacher=request.user
                )
                
                gdrive_file_id = result['file_id']
                play_url = gdrive.get_embed_link(gdrive_file_id)
                download_url = gdrive.get_direct_download_link(gdrive_file_id)
                storage_provider = 'gdrive'
                
                logger.info(f"Uploaded standalone video to GDrive: {safe_filename} -> {gdrive_file_id}")
                
            except Exception as e:
                logger.exception(f"Failed to upload to GDrive, falling back to local: {e}")
                # Fallback на локальное хранение при ошибке GDrive
                storage_provider = 'local'
        
        # Fallback: локальное хранение если GDrive выключен или ошибка
        if storage_provider == 'local':
            from django.core.files.storage import default_storage
            
            upload_dir = 'lesson_recordings'
            media_root = getattr(settings, 'MEDIA_ROOT', '/tmp')
            if not os.path.exists(os.path.join(media_root, upload_dir)):
                os.makedirs(os.path.join(media_root, upload_dir))
            
            file_path = os.path.join(upload_dir, safe_filename)
            saved_path = default_storage.save(file_path, video_file)
            play_url = f'/media/{saved_path}'
            download_url = f'/media/{saved_path}'
        
        # Извлекаем длительность видео
        video_file.seek(0)  # Сбрасываем позицию после загрузки в GDrive
        video_duration = _get_video_duration(video_file)
        
        # Создаём запись БЕЗ урока (standalone recording)
        recording = LessonRecording.objects.create(
            lesson=None,
            teacher=request.user,  # Владелец standalone записи
            title=title,
            play_url=play_url,
            download_url=download_url,
            gdrive_file_id=gdrive_file_id,
            status='ready',
            file_size=video_file.size,
            duration=video_duration,  # Реальная длительность видео
            storage_provider=storage_provider
        )
        
        recording.apply_privacy(
            privacy_type=privacy_type,
            group_ids=allowed_groups,
            student_ids=allowed_students,
            teacher=request.user
        )

        logger.info(f"Standalone video uploaded by {request.user.email}: {safe_filename}, storage: {storage_provider}, privacy: {privacy_type}")
        
        return Response({
            'status': 'success',
            'recording': {
                'id': recording.id,
                'title': recording.title,
                'play_url': recording.play_url,
                'file_size': recording.file_size,
                'storage_provider': storage_provider,
                'created_at': recording.created_at
            }
        }, status=status.HTTP_201_CREATED)
    
    def get_queryset(self):
        """Фильтрация по параметрам запроса"""
        # ОПТИМИЗАЦИЯ: select_related для избежания N+1 на group/teacher
        queryset = super().get_queryset().select_related('group', 'teacher', 'zoom_account')
        
        # Исключаем быстрые уроки из расписания по умолчанию
        queryset = queryset.filter(is_quick_lesson=False)
        
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()
        if getattr(user, 'role', None) == 'teacher':
            queryset = queryset.filter(teacher=user)
        elif getattr(user, 'role', None) == 'student':
            queryset = queryset.filter(group__students=user)
        
        # Фильтр по группе
        group_id = self.request.query_params.get('group')
        if group_id:
            queryset = queryset.filter(group_id=group_id)
        
        # Фильтр по преподавателю
        teacher_id = self.request.query_params.get('teacher')
        if teacher_id:
            queryset = queryset.filter(teacher_id=teacher_id)
        
        # Фильтр по конкретной дате (для сегодняшнего расписания)
        date_param = self.request.query_params.get('date')
        if date_param:
            from django.utils.dateparse import parse_date
            parsed_date = parse_date(date_param)
            if parsed_date:
                # Используем __date для фильтрации по дате независимо от часового пояса
                queryset = queryset.filter(start_time__date=parsed_date)
        
        # Фильтр по датам (для календаря)
        start_date = self.request.query_params.get('start')
        end_date = self.request.query_params.get('end')
        
        if start_date:
            start_dt = parse_datetime(start_date)
            if start_dt:
                queryset = queryset.filter(start_time__gte=start_dt)
        
        if end_date:
            end_dt = parse_datetime(end_date)
            if end_dt:
                queryset = queryset.filter(end_time__lte=end_dt)
        
        return queryset
    
    def get_serializer_class(self):
        """Используем разные сериализаторы для разных действий"""
        if self.action == 'retrieve':
            return LessonDetailSerializer
        elif self.action == 'calendar_feed':
            return LessonCalendarSerializer
        return LessonSerializer

    def perform_create(self, serializer):
        # serializer create already validates teacher/group ownership
        serializer.save()
    
    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        """Возвращает статистику по транскрипту урока"""
        lesson = self.get_object()
        
        # Проверяем права: учитель этой группы или студент этой группы
        user = request.user
        if not user.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
            
        group = lesson.group
        if not group:
             # Если группа удалена или не привязана, проверяем только владельца-учителя
             if user.id != lesson.teacher_id:
                  return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            is_teacher = (user.id == group.teacher_id) or (getattr(user, 'role', '') == 'admin')
            is_student = group.students.filter(id=user.id).exists()
            
            if not (is_teacher or is_student):
                return Response(status=status.HTTP_403_FORBIDDEN)

        try:
            stats = lesson.transcript_stats
            data = {
                'stats': stats.stats_json,
                'summary': {
                    'teacher_percent': stats.teacher_talk_time_percent,
                    'student_percent': stats.student_talk_time_percent
                }
            }
            return Response(data)
        except LessonTranscriptStats.DoesNotExist:
             return Response({'error': 'No analytics available'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['get'])
    def calendar_feed(self, request):
        """
        Эндпоинт для FullCalendar.js
        Возвращает события в формате FullCalendar
        """
        queryset = self.filter_queryset(self.get_queryset())
        start_param = request.query_params.get('start')
        end_param = request.query_params.get('end')
        teacher_id = request.query_params.get('teacher') or ''
        group_id = request.query_params.get('group') or ''
        raw_key = f"calendar:{teacher_id}:{group_id}:{start_param}:{end_param}"
        # Убираем пробелы, если ключ слишком длинный или содержит запрещенные символы — хэшируем
        safe_key = raw_key.replace(' ', '_')
        if len(safe_key) > 200:
            safe_key = 'calendar:' + hashlib.md5(raw_key.encode('utf-8')).hexdigest()
        cache_key = safe_key
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)
        serializer = LessonCalendarSerializer(queryset, many=True)
        events = serializer.data

        # Расширяем регулярные занятия в виртуальные события
        start_date_param = start_param
        end_date_param = end_param
        from django.utils.dateparse import parse_datetime, parse_date
        from datetime import datetime, timedelta

        def safe_parse(param):
            if not param:
                return None
            # Replace space (decoded '+') back to '+' for timezone offsets
            raw = param.replace(' ', '+')
            dt = parse_datetime(raw)
            if dt:
                return dt
            # Try pure date
            d = parse_date(raw)
            if d:
                return datetime.combine(d, datetime.min.time()).replace(tzinfo=timezone.utc)
            # Try trimming timezone colon (e.g. +00:00 -> +0000)
            if '+' in raw:
                head, tz = raw.rsplit('+', 1)
                tz_compact = tz.replace(':', '')
                dt = parse_datetime(f"{head}+{tz_compact}")
                if dt:
                    return dt
            return None

        start_dt = safe_parse(start_date_param)
        end_dt = safe_parse(end_date_param)
        if start_dt and end_dt:
            # Берем регулярные уроки преподавателя/групп из контекста запроса
            recurring_qs = RecurringLesson.objects.all()
            teacher_id = request.query_params.get('teacher')
            group_id = request.query_params.get('group')
            if teacher_id:
                recurring_qs = recurring_qs.filter(teacher_id=teacher_id)
            if group_id:
                recurring_qs = recurring_qs.filter(group_id=group_id)

            # Функция проверки типа недели
            def matches_week_type(week_type, date):
                if week_type == 'ALL':
                    return True
                iso_week = date.isocalendar()[1]
                # Допущение: UPPER = четная неделя, LOWER = нечетная
                if week_type == 'UPPER':
                    return iso_week % 2 == 0
                if week_type == 'LOWER':
                    return iso_week % 2 == 1
                return True

            current_date = start_dt.date()
            while current_date <= end_dt.date():
                for rl in recurring_qs:
                    if (current_date >= rl.start_date and current_date <= rl.end_date
                        and current_date.weekday() == rl.day_of_week
                        and matches_week_type(rl.week_type, current_date)):
                        # Формируем виртуальное событие
                        start_time = datetime.combine(current_date, rl.start_time)
                        end_time = datetime.combine(current_date, rl.end_time)
                        # Пропускаем если уже существует реальный Lesson перекрывающий этот интервал
                        if queryset.filter(start_time__lte=start_time, end_time__gte=end_time, group=rl.group).exists():
                            continue
                        events.append({
                            'id': f'recurring-{rl.id}-{current_date.isoformat()}',
                            'title': f"{rl.title} - {rl.group.name}",
                            'start': start_time.isoformat(),
                            'end': end_time.isoformat(),
                            'color': '#6b7280',
                            'extendedProps': {
                                'groupId': rl.group.id,
                                'groupName': rl.group.name,
                                'teacherId': rl.teacher.id,
                                'teacherName': rl.teacher.get_full_name(),
                                'location': rl.location,
                                'topics': rl.topics,
                                'recurring': True,
                                'weekType': rl.week_type,
                            }
                        })
                current_date += timedelta(days=1)

        cache.set(cache_key, events, timeout=60)  # 1 минута кэширования
        return Response(events)

    def _start_zoom_with_teacher_credentials(self, lesson, user, request):
        """Создать Zoom встречу используя персональные credentials учителя."""
        from .zoom_client import ZoomAPIClient
        
        try:
            zoom_client = ZoomAPIClient(
                account_id=user.zoom_account_id,
                client_id=user.zoom_client_id,
                client_secret=user.zoom_client_secret
            )
            
            zoom_user_id = user.zoom_user_id or 'me'
            meeting_data = zoom_client.create_meeting(
                user_id=zoom_user_id,
                topic=f"{lesson.group.name} - {lesson.title}",
                start_time=lesson.start_time,
                duration=lesson.duration(),
                auto_record=lesson.record_lesson
            )
            
            lesson.zoom_meeting_id = meeting_data['id']
            lesson.zoom_join_url = meeting_data['join_url']
            lesson.zoom_start_url = meeting_data['start_url']
            lesson.zoom_password = meeting_data.get('password', '')
            lesson.zoom_account = None  # Персональные credentials, не из пула
            lesson.save()
            
            log_audit(
                user=user,
                action='lesson_start',
                resource_type='Lesson',
                resource_id=lesson.id,
                request=request,
                details={
                    'lesson_title': lesson.title,
                    'group_name': lesson.group.name,
                    'zoom_meeting_id': meeting_data['id'],
                    'start_time': lesson.start_time.isoformat(),
                    'using_personal_credentials': True,
                }
            )
            
            payload = {
                'zoom_join_url': lesson.zoom_join_url,
                'zoom_start_url': lesson.zoom_start_url,
                'zoom_meeting_id': lesson.zoom_meeting_id,
                'zoom_password': lesson.zoom_password,
                'account_email': user.email,
            }
            return payload, None
        except Exception as e:
            logger.exception(f"Failed to create Zoom meeting with teacher credentials for lesson {lesson.id}: {e}")
            return None, Response(
                {'detail': f'Ошибка при создании встречи: {e}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _start_zoom_via_pool(self, lesson, user, request):
        """
        Создать Zoom встречу используя credentials учителя.
        
        ВАЖНО: Глобальный пул удалён. У каждого учителя должны быть свои Zoom credentials.
        Если credentials не настроены - возвращаем ошибку.
        """
        from .zoom_client import ZoomAPIClient
        
        # Проверяем, есть ли у учителя персональные Zoom credentials
        if user.zoom_account_id and user.zoom_client_id and user.zoom_client_secret:
            logger.info(f"Using personal Zoom credentials for teacher {user.email}")
            return self._start_zoom_with_teacher_credentials(lesson, user, request)
        
        # НЕТ персональных credentials = нельзя создать встречу
        logger.warning(f"Teacher {user.email} has no Zoom credentials configured")
        return None, Response(
            {
                'detail': 'Zoom не настроен. Обратитесь к администратору для настройки Zoom credentials.',
                'error_code': 'zoom_not_configured'
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=True, methods=['post'])
    def mark_attendance(self, request, pk=None):
        """Отметить посещаемость для занятия"""
        lesson = self.get_object()
        attendances = request.data.get('attendances', [])
        
        # БЕЗОПАСНОСТЬ: Получаем список валидных student_id из группы урока
        valid_student_ids = set(lesson.group.students.values_list('id', flat=True))
        
        marked_count = 0
        skipped_ids = []
        
        for attendance_data in attendances:
            student_id = attendance_data.get('student_id')
            status_value = attendance_data.get('status', 'absent')
            notes = attendance_data.get('notes', '')
            
            if student_id:
                # БЕЗОПАСНОСТЬ: Проверяем что студент в группе этого урока
                if student_id not in valid_student_ids:
                    skipped_ids.append(student_id)
                    continue
                    
                Attendance.objects.update_or_create(
                    lesson=lesson,
                    student_id=student_id,
                    defaults={
                        'status': status_value,
                        'notes': notes
                    }
                )
                marked_count += 1
        
        if skipped_ids:
            logger.warning(f"mark_attendance: skipped invalid student_ids {skipped_ids} for lesson {lesson.id}")
        
        serializer = LessonDetailSerializer(lesson)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_recording(self, request, pk=None):
        """Добавить запись урока (URL)"""
        lesson = self.get_object()
        url = request.data.get('url')
        available_days = request.data.get('available_days', 90)
        
        if not url:
            return Response({'detail': 'url обязателен'}, status=status.HTTP_400_BAD_REQUEST)
        # Требуем активную подписку
        try:
            require_active_subscription(request.user)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)
        
        # Проверка прав: только преподаватель своего урока
        if lesson.teacher != request.user:
            return Response({'detail': 'Только преподаватель урока может добавлять записи'}, status=status.HTTP_403_FORBIDDEN)
        
        # Вычисляем available_until
        from django.utils import timezone
        from datetime import timedelta
        available_until = None
        if available_days and available_days > 0:
            available_until = timezone.now() + timedelta(days=available_days)
        
        recording = LessonRecording.objects.create(
            lesson=lesson,
            play_url=url,
            download_url=url,
            status='ready',
            available_until=available_until
        )
        recording.apply_privacy(
            privacy_type=LessonRecording.Visibility.LESSON_GROUP,
            teacher=lesson.teacher
        )
        return Response({
            'status': 'created',
            'recording': {
                'id': recording.id,
                'play_url': recording.play_url,
                'created_at': recording.created_at,
                'available_until': recording.available_until
            }
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='upload_recording')
    def upload_recording(self, request, pk=None):
        """Загрузить видео файл урока с настройками приватности — напрямую в Google Drive"""
        lesson = self.get_object()
        
        # Требуем активную подписку
        try:
            require_active_subscription(request.user)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)
        
        # Проверка прав: только преподаватель своего урока
        if lesson.teacher != request.user:
            return Response({'detail': 'Только преподаватель урока может добавлять записи'}, status=status.HTTP_403_FORBIDDEN)
        
        video_file = request.FILES.get('video')
        if not video_file:
            return Response({'detail': 'Видео файл обязателен'}, status=status.HTTP_400_BAD_REQUEST)
        
        # БЕЗОПАСНОСТЬ: Проверка MIME-типа видео
        allowed_video_types = ['video/mp4', 'video/webm', 'video/mpeg', 'video/quicktime', 'video/x-msvideo', 'video/x-matroska']
        if video_file.content_type not in allowed_video_types:
            return Response(
                {'detail': f'Неподдерживаемый тип файла: {video_file.content_type}. Разрешены: MP4, WebM, MPEG, MOV, AVI, MKV'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверка лимита хранилища учителя
        from accounts.models import Subscription
        from accounts.gdrive_folder_service import check_storage_limit
        
        try:
            subscription = Subscription.objects.get(user=request.user)
        except Subscription.DoesNotExist:
            return Response({'detail': 'Подписка не найдена'}, status=status.HTTP_403_FORBIDDEN)
        
        allowed, message = check_storage_limit(subscription, video_file.size)
        if not allowed:
            return Response({'detail': message}, status=status.HTTP_400_BAD_REQUEST)
        
        privacy_type = request.data.get('privacy_type', 'all')
        allowed_groups = _parse_ids_list(request.data.get('allowed_groups'))
        allowed_students = _parse_ids_list(request.data.get('allowed_students'))
        
        from django.conf import settings
        from django.utils.text import slugify, get_valid_filename
        import os
        import uuid
        from datetime import datetime
        
        # БЕЗОПАСНОСТЬ: Безопасное имя файла
        original_name = os.path.basename(video_file.name)
        safe_original = get_valid_filename(original_name)
        lesson_title = slugify(lesson.title or lesson.subject or 'lesson')
        group_name = slugify(lesson.group.name if lesson.group else 'nogroup')
        date_str = lesson.start_time.strftime('%Y%m%d') if lesson.start_time else datetime.now().strftime('%Y%m%d')
        safe_filename = f'{date_str}_{lesson_title}_{group_name}_{uuid.uuid4().hex[:6]}_{safe_original}'
        
        # Загрузка в Google Drive
        gdrive_file_id = None
        play_url = None
        download_url = None
        storage_provider = 'local'
        
        if settings.USE_GDRIVE_STORAGE:
            try:
                from .gdrive_utils import get_gdrive_manager
                gdrive = get_gdrive_manager()
                
                # Получаем папку Recordings учителя
                teacher_folders = gdrive.get_or_create_teacher_folder(request.user)
                recordings_folder_id = teacher_folders.get('recordings', teacher_folders.get('root'))
                
                # Загружаем файл в Google Drive
                result = gdrive.upload_file(
                    file_path_or_object=video_file,
                    file_name=safe_filename,
                    folder_id=recordings_folder_id,
                    mime_type=video_file.content_type,
                    teacher=request.user
                )
                
                gdrive_file_id = result['file_id']
                play_url = gdrive.get_embed_link(gdrive_file_id)
                download_url = gdrive.get_direct_download_link(gdrive_file_id)
                storage_provider = 'gdrive'
                
                logger.info(f"Uploaded lesson {lesson.id} video to GDrive: {safe_filename} -> {gdrive_file_id}")
                
            except Exception as e:
                logger.exception(f"Failed to upload to GDrive, falling back to local: {e}")
                storage_provider = 'local'
        
        # Fallback: локальное хранение если GDrive выключен или ошибка
        if storage_provider == 'local':
            from django.core.files.storage import default_storage
            
            upload_dir = 'lesson_recordings'
            media_root = getattr(settings, 'MEDIA_ROOT', '/tmp')
            if not os.path.exists(os.path.join(media_root, upload_dir)):
                os.makedirs(os.path.join(media_root, upload_dir))
            
            file_path = os.path.join(upload_dir, safe_filename)
            saved_path = default_storage.save(file_path, video_file)
            play_url = f'/media/{saved_path}'
            download_url = f'/media/{saved_path}'
        
        # Создаём запись привязанную к уроку
        recording = LessonRecording.objects.create(
            lesson=lesson,
            play_url=play_url,
            download_url=download_url,
            gdrive_file_id=gdrive_file_id,
            status='ready',
            file_size=video_file.size,
            storage_provider=storage_provider
        )
        recording.apply_privacy(
            privacy_type=privacy_type,
            group_ids=allowed_groups,
            student_ids=allowed_students,
            teacher=request.user
        )
        
        logger.info(f"Video uploaded for lesson {lesson.id}: {safe_filename}, storage: {storage_provider}, privacy: {privacy_type}")
        
        return Response({
            'status': 'success',
            'recording': {
                'id': recording.id,
                'play_url': recording.play_url,
                'file_size': recording.file_size,
                'storage_provider': storage_provider,
                'created_at': recording.created_at
            }
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='start')
    def start(self, request, pk=None):
        """
        Запуск урока с использованием Zoom credentials учителя.
        POST /api/schedule/lessons/{id}/start/
        """
        lesson = self.get_object()
        user = request.user
        # Требуем активную подписку
        try:
            require_active_subscription(user)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)
        
        # Проверка прав доступа
        if lesson.teacher != user:
            return Response({
                'detail': 'Только учитель урока может его запустить'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Проверка наличия Zoom credentials у учителя
        if not user.zoom_account_id or not user.zoom_client_id or not user.zoom_client_secret:
            return Response({
                'detail': 'У вас не настроены Zoom credentials. Обратитесь к администратору.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Если встреча уже создана - вернуть существующие данные
        if lesson.zoom_meeting_id:
            return Response({
                'zoom_join_url': lesson.zoom_join_url,
                'zoom_start_url': lesson.zoom_start_url,
                'zoom_meeting_id': lesson.zoom_meeting_id,
                'zoom_password': lesson.zoom_password,
            }, status=status.HTTP_200_OK)
        
        # Rate limiting - 3 попытки в минуту
        throttle_key = f"lesson_start_throttle:{user.id}"
        attempts = cache.get(throttle_key, 0)
        if attempts >= 3:
            return Response({
                'detail': 'Слишком много попыток запуска. Подождите минуту.'
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        cache.set(throttle_key, attempts + 1, 60)
        
        try:
            # Создаем Zoom клиент с credentials учителя
            from .zoom_client import ZoomAPIClient
            zoom_client = ZoomAPIClient(
                account_id=user.zoom_account_id,
                client_id=user.zoom_client_id,
                client_secret=user.zoom_client_secret
            )
            
            # Создание встречи Zoom
            zoom_user_id = user.zoom_user_id or 'me'
            meeting_data = zoom_client.create_meeting(
                user_id=zoom_user_id,
                topic=f"{lesson.group.name} - {lesson.title}",
                start_time=lesson.start_time,
                duration=lesson.duration()
            )
            
            # Сохраняем результат
            lesson.zoom_meeting_id = meeting_data['id']
            lesson.zoom_start_url = meeting_data['start_url']
            lesson.zoom_join_url = meeting_data['join_url']
            lesson.zoom_password = meeting_data.get('password', '')
            lesson.save()
            
            # Логирование
            log_audit(
                user=user,
                action='lesson_start',
                resource_type='Lesson',
                resource_id=lesson.id,
                request=request,
                details={'meeting_id': meeting_data['id'], 'teacher': user.email}
            )
            
            return Response({
                'zoom_join_url': meeting_data['join_url'],
                'zoom_start_url': meeting_data['start_url'],
                'zoom_meeting_id': meeting_data['id'],
                'zoom_password': meeting_data.get('password', ''),
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Failed to start lesson for teacher {user.email}: {e}")
            return Response({
                'detail': f'Ошибка при создании встречи: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='start-new')
    def start_new(self, request, pk=None):
        """
        Новый старт урока с выбором платформы (Zoom или Google Meet).
        POST /api/schedule/lessons/{id}/start-new/

        Параметры:
            - provider: 'zoom_pool' (default) | 'google_meet'
            - record_lesson: bool (только для Zoom)
            - force_new_meeting: bool

        Возвращает 503 если все Zoom аккаунты заняты.
        Ограничение: запускать можно за 15 минут до начала.
        Если встреча уже создана – возвращаем существующие данные.
        Rate limit: 3 попытки в минуту на пользователя.
        """
        lesson = self.get_object()
        user = request.user
        
        # Требуем активную подписку
        try:
            require_active_subscription(user)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)

        # Определяем провайдера (по умолчанию zoom_pool для backward compatibility)
        provider = request.data.get('provider', 'zoom_pool')
        if provider not in ('zoom_pool', 'zoom_personal', 'google_meet'):
            provider = 'zoom_pool'

        # Позволяем передать флаг записи вместе с запросом
        record_flag_raw = request.data.get('record_lesson')
        force_new_meeting = str(request.data.get('force_new_meeting', '')).lower() in (
            '1', 'true', 'yes', 'on', 'y', 't'
        )
        record_flag_changed = False
        if record_flag_raw is not None:
            desired_record_flag = str(record_flag_raw).lower() in ('1', 'true', 'yes', 'on', 'y', 't')
            if desired_record_flag != lesson.record_lesson:
                lesson.record_lesson = desired_record_flag
                lesson.save(update_fields=['record_lesson'])
                record_flag_changed = True

        # Если просили включить запись и встреча уже есть — пересоздаём её
        force_new_meeting = force_new_meeting or (record_flag_changed and lesson.record_lesson)

        # Rate limiting - 3 попытки в минуту на пользователя
        rate_limit_key = f"start_lesson_rate_limit:{user.id}"
        attempts = cache.get(rate_limit_key, 0)
        if attempts >= 3:
            return Response(
                {'detail': 'Слишком много попыток запуска урока. Подождите минуту.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        cache.set(rate_limit_key, attempts + 1, 60)  # TTL 60 секунд

        # Проверка прав доступа
        if lesson.teacher != user:
            return Response({'detail': 'Только преподаватель урока может его запустить'}, status=status.HTTP_403_FORBIDDEN)

        # Проверка времени (за 15 минут до начала)
        now = timezone.now()
        if lesson.start_time - timezone.timedelta(minutes=15) > now:
            return Response({'detail': 'Урок можно начать за 15 минут до начала'}, status=status.HTTP_400_BAD_REQUEST)

        # ========== Google Meet ==========
        if provider == 'google_meet':
            return self._start_via_google_meet(lesson, user, request)

        # ========== Zoom (legacy path - не трогаем) ==========
        # Если уже есть Zoom встреча и не требуется пересоздание – вернуть её
        if lesson.zoom_meeting_id and not force_new_meeting:
            return Response({
                'zoom_join_url': lesson.zoom_join_url,
                'zoom_start_url': lesson.zoom_start_url,
                'zoom_meeting_id': lesson.zoom_meeting_id,
                'zoom_password': lesson.zoom_password,
                'account_email': getattr(lesson.zoom_account, 'email', 'уже назначен'),
                'provider': 'zoom',
            }, status=status.HTTP_200_OK)

        # Пересоздаём встречу, если нужно включить запись
        if lesson.zoom_meeting_id and force_new_meeting:
            old_account = lesson.zoom_account
            lesson.zoom_meeting_id = None
            lesson.zoom_join_url = None
            lesson.zoom_start_url = None
            lesson.zoom_password = None
            lesson.zoom_account = None
            lesson.save(update_fields=[
                'zoom_meeting_id', 'zoom_join_url', 'zoom_start_url', 'zoom_password', 'zoom_account'
            ])

            if old_account:
                try:
                    old_account.release()
                except Exception:
                    logger.exception('Не удалось освободить Zoom аккаунт при пересоздании встречи')

        # Поиск свободного аккаунта из пула
        payload, error_response = self._start_zoom_via_pool(lesson, user, request)
        if error_response:
            return error_response
        payload['provider'] = 'zoom'
        return Response(payload, status=status.HTTP_200_OK)

    def _start_via_google_meet(self, lesson, user, request):
        """
        Вспомогательный метод для старта урока через Google Meet.
        Создаёт событие в Google Calendar с Meet conferencing.
        """
        from django.conf import settings
        
        # Проверяем, включена ли интеграция Google Meet
        if not getattr(settings, 'GOOGLE_MEET_ENABLED', False):
            return Response(
                {'detail': 'Google Meet интеграция не включена на сервере'},
                status=status.HTTP_501_NOT_IMPLEMENTED
            )
        
        # Проверяем, подключён ли Google Meet у пользователя
        if not user.is_google_meet_connected():
            return Response(
                {'detail': 'Google Meet не подключён. Подключите его в профиле.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем, есть ли уже Google Meet ссылка для этого урока
        if lesson.google_meet_link:
            return Response({
                'meet_link': lesson.google_meet_link,
                'start_url': lesson.google_meet_link,
                'join_url': lesson.google_meet_link,
                'google_calendar_event_id': lesson.google_calendar_event_id,
                'provider': 'google_meet',
            }, status=status.HTTP_200_OK)
        
        try:
            from integrations.google_meet_service import GoogleMeetService, GoogleMeetError
            
            service = GoogleMeetService(user=user)
            
            # Создаём встречу
            group_name = lesson.group.name if lesson.group else 'Урок'
            title = f"{group_name} - {lesson.title}"
            
            meeting_data = service.create_meeting(
                title=title,
                start_time=lesson.start_time,
                duration_minutes=lesson.duration(),
                description=f"Урок на платформе Teaching Panel\nПреподаватель: {user.get_full_name()}",
            )
            
            # Сохраняем данные в урок
            lesson.google_meet_link = meeting_data.get('meet_link', '')
            lesson.google_calendar_event_id = meeting_data.get('event_id', '')
            lesson.save(update_fields=['google_meet_link', 'google_calendar_event_id'])
            
            logger.info(f"Google Meet created for lesson {lesson.id}: {lesson.google_meet_link}")
            
            # Логирование
            log_audit(
                user=user,
                action='lesson_start_google_meet',
                resource_type='Lesson',
                resource_id=lesson.id,
                request=request,
                details={'meet_link': lesson.google_meet_link, 'teacher': user.email}
            )
            
            return Response({
                'meet_link': lesson.google_meet_link,
                'start_url': lesson.google_meet_link,
                'join_url': lesson.google_meet_link,
                'google_calendar_event_id': lesson.google_calendar_event_id,
                'provider': 'google_meet',
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.exception(f"Failed to create Google Meet for lesson {lesson.id}: {e}")
            return Response(
                {'detail': f'Ошибка при создании Google Meet: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='quick-start')
    def quick_start(self, request):
        """Создать урок без расписания и сразу запустить Zoom встречу."""
        user = request.user
        if getattr(user, 'role', None) != 'teacher':
            return Response(
                {'detail': 'Только преподаватели могут создавать экспресс-уроки'},
                status=status.HTTP_403_FORBIDDEN
            )
        # Требуем активную подписку
        try:
            require_active_subscription(user)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)

        duration_raw = request.data.get('duration')
        try:
            duration = int(duration_raw)
        except (TypeError, ValueError):
            duration = 60
        duration = max(15, min(180, duration))

        title = (request.data.get('title') or '').strip()
        if not title:
            local_time = timezone.localtime()
            title = f"Экспресс урок {local_time.strftime('%H:%M')}"

        group_id = request.data.get('group_id')
        group = None
        if group_id:
            try:
                group = Group.objects.get(id=group_id, teacher=user)
            except Group.DoesNotExist:
                return Response({'detail': 'Группа не найдена'}, status=status.HTTP_404_NOT_FOUND)
        else:
            group = Group.objects.filter(teacher=user).order_by('created_at').first()
            if not group:
                group = Group.objects.create(
                    name=f"Без расписания • {user.get_full_name() or user.email}",
                    teacher=user,
                    description='Автогенерированная группа для уроков без расписания'
                )

        start_time = timezone.now()
        end_time = start_time + timezone.timedelta(minutes=duration)

        # Получаем настройки записи
        record_lesson = request.data.get('record_lesson', False)

        lesson = Lesson.objects.create(
            title=title,
            group=group,
            teacher=user,
            start_time=start_time,
            end_time=end_time,
            record_lesson=record_lesson,
            is_quick_lesson=True,  # Помечаем как быстрый урок
            notes='Создано кнопкой "Быстрый урок"'
        )

        payload, error_response = self._start_zoom_via_pool(lesson, user, request)
        if error_response:
            lesson.delete()
            return error_response

        # Если урок записывается, применяем настройки приватности к будущей записи
        if record_lesson:
            privacy_type = request.data.get('privacy_type', 'all')
            allowed_groups = request.data.get('allowed_groups', [])
            allowed_students = request.data.get('allowed_students', [])
            
            # Сохраняем настройки приватности в метаданных урока для применения при создании записи
            # Это будет использовано в webhook обработчике когда запись будет готова
            lesson.privacy_settings = {
                'privacy_type': privacy_type,
                'allowed_groups': allowed_groups,
                'allowed_students': allowed_students,
            }
            # Сохраняем в поле notes временно (или можно добавить JSONField в модель)
            import json
            lesson.notes = f"Создано кнопкой \"Быстрый урок\"\nPrivacy: {json.dumps(lesson.privacy_settings)}"
            lesson.save(update_fields=['notes'])

        payload.update({
            'lesson_id': lesson.id,
            'title': lesson.title,
            'group_name': group.name,
        })
        return Response(payload, status=status.HTTP_201_CREATED)


class AttendanceViewSet(viewsets.ModelViewSet):
    """
    ViewSet для работы с посещаемостью.
    Требует аутентификации для всех операций.
    """
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated]  # ✅ FIXED: Restored authentication
    
    def get_queryset(self):
        """Фильтрация посещаемости"""
        queryset = super().get_queryset()

        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()

        role = getattr(user, 'role', None)
        if role == 'teacher':
            queryset = queryset.filter(lesson__teacher=user)
        elif role == 'student':
            queryset = queryset.filter(lesson__group__students=user)
        elif role != 'admin':
            return queryset.none()
        
        # Фильтр по занятию
        lesson_id = self.request.query_params.get('lesson')
        if lesson_id:
            queryset = queryset.filter(lesson_id=lesson_id)
        
        # Фильтр по студенту
        student_id = self.request.query_params.get('student')
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        
        # Фильтр по статусу
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset


class ZoomAccountViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для просмотра состояния Zoom аккаунтов
    Только для чтения (создание/редактирование через админку)
    """
    queryset = ZoomAccount.objects.all()
    serializer_class = ZoomAccountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = getattr(self.request, 'user', None)
        if not (user and user.is_authenticated and getattr(user, 'role', None) == 'admin'):
            raise PermissionDenied('Только администратор')
        return super().get_queryset()
    
    @action(detail=False, methods=['get'])
    def status_summary(self, request):
        """Сводка по занятости аккаунтов"""
        user = getattr(request, 'user', None)
        if not (user and user.is_authenticated and getattr(user, 'role', None) == 'admin'):
            raise PermissionDenied('Только администратор')

        total = ZoomAccount.objects.count()
        active = ZoomAccount.objects.filter(is_active=True).count()
        inactive = total - active

        in_use = ZoomAccount.objects.filter(is_active=True, current_meetings__gt=0).count()
        available = ZoomAccount.objects.filter(
            is_active=True,
            current_meetings__lt=F('max_concurrent_meetings'),
        ).count()

        busy_accounts = ZoomAccount.objects.filter(is_active=True, current_meetings__gt=0)

        return Response({
            'total': total,
            'active': active,
            'inactive': inactive,
            'busy': in_use,
            'free': available,
            'busy_accounts': ZoomAccountSerializer(busy_accounts, many=True, context={'request': request}).data,
        })


class RecurringLessonViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления регулярными уроками
    """
    queryset = RecurringLesson.objects.all()
    serializer_class = RecurringLessonSerializer
    permission_classes = [IsAuthenticated, IsTeacherOrReadOnly]
    
    def get_queryset(self):
        """Фильтрация регулярных уроков"""
        queryset = super().get_queryset()
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()
        if getattr(user, 'role', None) == 'teacher':
            queryset = queryset.filter(teacher=user)
        elif getattr(user, 'role', None) == 'student':
            queryset = queryset.filter(group__students=user)
        else:
            return queryset.none()
        
        # Фильтр по преподавателю
        teacher_id = self.request.query_params.get('teacher')
        if teacher_id:
            queryset = queryset.filter(teacher_id=teacher_id)
        
        # Фильтр по группе
        group_id = self.request.query_params.get('group')
        if group_id:
            queryset = queryset.filter(group_id=group_id)
        
        # Фильтр по дню недели
        day = self.request.query_params.get('day_of_week')
        if day is not None:
            queryset = queryset.filter(day_of_week=int(day))
        
        return queryset

    @action(detail=True, methods=['post'], url_path='generate_lessons')
    def generate_lessons(self, request, pk=None):
        """Сгенерировать конкретные занятия (Lesson) из регулярного до указанной даты.

        Body:
          until_date (YYYY-MM-DD) - обязательный.
          start_date (YYYY-MM-DD) - необязательный, по умолчанию сегодня.
          override_title (str) - необязательный, если хотим другое название.
          dry_run (bool) - если true, только подсчитываем сколько было бы создано.
        Логика:
          Перебираем дни от start_date до until_date включительно, создаем Lesson для подходящих дат,
          пропуская даты вне диапазона RecurringLesson и где уже есть пересекающийся Lesson для той же группы.
        """
        rl = self.get_object()
        user = request.user
        if not user.is_authenticated or getattr(user, 'role', None) != 'teacher' or rl.teacher_id != user.id:
            return Response({'detail': 'Недостаточно прав'}, status=403)
        until_date_str = request.data.get('until_date')
        start_date_str = request.data.get('start_date')
        override_title = request.data.get('override_title')
        dry_run = bool(request.data.get('dry_run'))
        if not until_date_str:
            return Response({'detail': 'until_date обязателен'}, status=400)
        from datetime import datetime, timedelta
        from django.utils.dateparse import parse_date
        until_date = parse_date(until_date_str)
        start_date = parse_date(start_date_str) if start_date_str else timezone.localdate()
        if not until_date:
            return Response({'detail': 'Некорректный until_date'}, status=400)
        if start_date > until_date:
            return Response({'detail': 'start_date позже until_date'}, status=400)
        created = []
        skipped_existing = 0
        skipped_outside = 0
        title_base = override_title or rl.title

        def matches_week_type(week_type, date):
            if week_type == 'ALL':
                return True
            iso_week = date.isocalendar()[1]
            if week_type == 'UPPER':
                return iso_week % 2 == 0
            if week_type == 'LOWER':
                return iso_week % 2 == 1
            return True

        current = start_date
        while current <= until_date:
            # Outside RL active window
            if current < rl.start_date or current > rl.end_date:
                current += timedelta(days=1)
                continue
            if current.weekday() == rl.day_of_week and matches_week_type(rl.week_type, current):
                start_dt = datetime.combine(current, rl.start_time)
                end_dt = datetime.combine(current, rl.end_time)
                # Проверка пересечения существующих уроков группы
                overlap = Lesson.objects.filter(group=rl.group, start_time__lt=end_dt, end_time__gt=start_dt).exists()
                if overlap:
                    skipped_existing += 1
                else:
                    if not dry_run:
                        lesson = Lesson.objects.create(
                            title=title_base,
                            group=rl.group,
                            teacher=rl.teacher,
                            start_time=timezone.make_aware(start_dt, timezone.get_current_timezone()),
                            end_time=timezone.make_aware(end_dt, timezone.get_current_timezone()),
                            topics=rl.topics,
                            location=rl.location
                        )
                        created.append(lesson.id)
                    else:
                        created.append({'virtual_date': current.isoformat()})
            else:
                skipped_outside += 1
            current += timedelta(days=1)

        return Response({
            'status': 'ok',
            'dry_run': dry_run,
            'created_count': 0 if dry_run else len(created),
            'would_create_count': len(created) if dry_run else len(created),
            'created_ids': created if not dry_run else None,
            'skipped_existing': skipped_existing,
            'skipped_outside_pattern': skipped_outside
        })

    @action(detail=True, methods=['post'], url_path='telegram_bind_code')
    def telegram_bind_code(self, request, pk=None):
        """Сгенерировать одноразовый код для привязки Telegram-группы к этому регулярному уроку.

        Использование:
          1) Добавьте бота в Telegram-группу.
          2) В группе отправьте: /bindgroup <CODE>
        """
        rl = self.get_object()
        user = request.user
        if not user.is_authenticated or getattr(user, 'role', None) != 'teacher' or rl.teacher_id != user.id:
            return Response({'detail': 'Недостаточно прав'}, status=403)

        from django.utils.crypto import get_random_string
        from django.utils import timezone
        from datetime import timedelta
        from .models import RecurringLessonTelegramBindCode

        ttl_minutes = 30
        expires_at = timezone.now() + timedelta(minutes=ttl_minutes)

        # Генерируем уникальный код
        code = None
        for _ in range(10):
            candidate = get_random_string(8).upper()
            if not RecurringLessonTelegramBindCode.objects.filter(code=candidate).exists():
                code = candidate
                break
        if not code:
            return Response({'detail': 'Не удалось сгенерировать код, попробуйте позже'}, status=500)

        RecurringLessonTelegramBindCode.objects.create(
            recurring_lesson=rl,
            code=code,
            expires_at=expires_at,
        )

        return Response({
            'code': code,
            'expires_at': expires_at,
            'ttl_minutes': ttl_minutes,
            'instructions': f"Добавьте бота в группу и отправьте в группе: /bindgroup {code}",
        })


# Web UI Views

@login_required
def teacher_schedule_view(request):
    """
    Страница расписания для преподавателя
    Показывает календарь с занятиями и список групп
    """
    if not request.user.is_teacher():
        return render(request, 'schedule/access_denied.html', {
            'message': 'Эта страница доступна только преподавателям'
        })
    
    groups = Group.objects.filter(teacher=request.user)
    
    return render(request, 'schedule/teacher_schedule.html', {
        'groups': groups,
        'user': request.user
    })


@login_required
def student_dashboard_view(request):
    """
    Дашборд для студента
    Показывает его занятия и группы
    """
    if not request.user.is_student():
        return render(request, 'schedule/access_denied.html', {
            'message': 'Эта страница доступна только студентам'
        })
    
    groups = request.user.enrolled_groups.all()
    upcoming_lessons = Lesson.objects.filter(
        group__in=groups,
        start_time__gte=timezone.now()
    ).order_by('start_time')[:5]
    
    return render(request, 'schedule/student_dashboard.html', {
        'groups': groups,
        'upcoming_lessons': upcoming_lessons,
        'user': request.user
    })


# Промт 2: View для запуска урока с атомарным захватом Zoom аккаунта



@csrf_exempt  # Required for external webhooks - verified by signature instead
@require_http_methods(["GET", "POST"])  # Allow GET for Zoom validation probes
def zoom_webhook_receiver(request):
    """
    Webhook приемник для событий Zoom
    """
    try:
        # Логируем всё что приходит
        logger.info(f"[Webhook] Получен {request.method} запрос на /schedule/webhook/zoom/")
        logger.info(f"[Webhook] Content-Type: {request.content_type}")
        logger.info(f"[Webhook] Body length: {len(request.body)}")

        # Zoom может слать GET пробный — отвечаем 200
        if request.method == 'GET':
            return JsonResponse({'status': 'ok'})
        
        # Если body пуста, просто отвечаем 200 (может быть проверка доступности)
        if not request.body:
            logger.info(f"[Webhook] Empty body, returning 200")
            return JsonResponse({'status': 'ok'})
        
        # Парсим JSON из тела запроса
        try:
            payload = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError as e:
            logger.error(f"[Webhook] Invalid JSON: {e}")
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
        
        logger.info(f"[Webhook] Payload keys: {list(payload.keys())}")
        
        # Zoom отправляет verification token при первой настройке webhook
        # Проверяем наличие plainToken на верхнем уровне
        if 'plainToken' in payload:
            plain_token = payload.get('plainToken')
            logger.info(f"[Webhook] ✓ Verification request detected, plainToken={plain_token[:20]}...")
            response = JsonResponse({'plainToken': plain_token})
            logger.info(f"[Webhook] ✓ Responding with plainToken")
            return response
        
        # Также проверяем структуру с payload.payload.plainToken (старые версии)
        if 'event' not in payload and 'payload' in payload:
            plain_token = payload.get('payload', {}).get('plainToken')
            if plain_token:
                logger.info(f"[Webhook] ✓ Verification request (nested), responding")
                return JsonResponse({'plainToken': plain_token})
        
        # Обрабатываем события
        event_type = payload.get('event')
        logger.info(f"[Webhook] Event type: {event_type}")
        
        # Обрабатываем событие завершения встречи
        if event_type == 'meeting.ended':
            meeting_data = payload.get('payload', {}).get('object', {})
            meeting_id = meeting_data.get('id')  # Zoom meeting ID (строка)
            
            if not meeting_id:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Meeting ID not found in payload'
                }, status=400)
            
            # Ищем урок по Zoom meeting ID
            try:
                lesson = Lesson.objects.select_related('zoom_account_used').get(
                    zoom_meeting_id=meeting_id
                )
                
                # Получаем привязанный Zoom аккаунт
                zoom_account = lesson.zoom_account_used
                
                if zoom_account and zoom_account.is_busy:
                    # Освобождаем аккаунт
                    zoom_account.is_busy = False
                    zoom_account.current_lesson = None
                    zoom_account.save()
                    
                    logger.info(f"[Webhook] Zoom аккаунт {zoom_account.name} освобожден "
                          f"после завершения встречи #{meeting_id} (урок #{lesson.id})")
                    
                    return JsonResponse({
                        'status': 'success',
                        'message': f'Account {zoom_account.name} released',
                        'lesson_id': lesson.id,
                        'meeting_id': meeting_id
                    })
                else:
                    return JsonResponse({
                        'status': 'already_released',
                        'message': 'Account was already free',
                        'lesson_id': lesson.id
                    })
                    
            except Lesson.DoesNotExist:
                # Урок не найден - возможно, был удален или meeting_id неверный
                logger.warning(f"[Webhook] Урок с meeting_id={meeting_id} не найден")
                return JsonResponse({
                    'status': 'not_found',
                    'message': f'Lesson with meeting_id {meeting_id} not found'
                }, status=404)
        
        # Обрабатываем событие готовности записи
        elif event_type == 'recording.completed':
            recording_data = payload.get('payload', {}).get('object', {})
            meeting_id = str(recording_data.get('id', ''))  # Zoom meeting ID
            host_email = recording_data.get('host_email', '')
            topic = recording_data.get('topic', '')
            recording_files = recording_data.get('recording_files', [])
            
            logger.info(f"[Webhook] Получено событие recording.completed для встречи {meeting_id}")
            
            if not meeting_id:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Meeting ID not found in recording payload'
                }, status=400)
            
            # Ищем урок по Zoom meeting ID
            try:
                lesson = Lesson.objects.select_related('group', 'teacher').get(
                    zoom_meeting_id=meeting_id
                )
                
                # Проверяем, был ли включен флаг записи для этого урока
                if not lesson.record_lesson:
                    logger.info(f"[Webhook] Урок {lesson.id} не требует записи (record_lesson=False), пропускаем")
                    return JsonResponse({
                        'status': 'skipped',
                        'message': 'Recording not enabled for this lesson',
                        'lesson_id': lesson.id
                    })
                
                # Обрабатываем файлы записи
                created_recordings = []
                for rec_file in recording_files:
                    file_type = rec_file.get('file_type', '')
                    recording_type = rec_file.get('recording_type', '')
                    
                    # Обрабатываем только видео файлы (MP4)
                    if file_type.lower() not in ['mp4', 'video']:
                        continue
                    
                    download_url = rec_file.get('download_url', '')
                    play_url = rec_file.get('play_url', '')
                    recording_start = rec_file.get('recording_start', '')
                    recording_end = rec_file.get('recording_end', '')
                    file_size = rec_file.get('file_size', 0)
                    
                    # Создаём запись в БД со статусом "processing"
                    recording = LessonRecording.objects.create(
                        lesson=lesson,
                        zoom_recording_id=rec_file.get('id', ''),
                        download_url=download_url,
                        play_url=play_url,
                        recording_type=recording_type,
                        file_size=file_size,
                        status='ready',  # Сразу готова к просмотру
                        visibility=LessonRecording.Visibility.LESSON_GROUP,  # Доступна группе урока
                        storage_provider='zoom',  # Изначально в Zoom Cloud
                    )
                    
                    # Устанавливаем доступность записи
                    if lesson.recording_available_for_days > 0:
                        from datetime import timedelta
                        recording.available_until = timezone.now() + timedelta(days=lesson.recording_available_for_days)
                        recording.save()
                    
                    created_recordings.append({
                        'id': recording.id,
                        'recording_type': recording_type,
                        'file_size': file_size
                    })
                    
                    logger.info(f"[Webhook] Создана запись {recording.id} для урока {lesson.id} ({lesson.title})")
                
                if created_recordings:
                    return JsonResponse({
                        'status': 'success',
                        'message': f'Created {len(created_recordings)} recording(s)',
                        'lesson_id': lesson.id,
                        'recordings': created_recordings
                    })
                else:
                    return JsonResponse({
                        'status': 'no_recordings',
                        'message': 'No video files found in recording',
                        'lesson_id': lesson.id
                    })
                    
            except Lesson.DoesNotExist:
                logger.warning(f"[Webhook] Урок с meeting_id={meeting_id} не найден при обработке записи")
                return JsonResponse({
                    'status': 'not_found',
                    'message': f'Lesson with meeting_id {meeting_id} not found'
                }, status=404)
        
        # Другие события - просто логируем и отвечаем 200
        logger.info(f"[Webhook] Получено событие {event_type}, игнорируем")
        return JsonResponse({
            'status': 'ignored',
            'event': event_type
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        print(f"[Webhook] Ошибка обработки: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


# ============================================================================
# API ENDPOINTS ДЛЯ ЗАПИСЕЙ УРОКОВ
# ============================================================================

from rest_framework.decorators import api_view, permission_classes
from .serializers import LessonRecordingSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_recordings_list(request):
    """
    Список всех записей уроков доступных студенту
    GET /schedule/api/recordings/
    """
    user = request.user
    
    # Только для студентов
    if getattr(user, 'role', None) != 'student':
        return Response({
            'error': 'Доступ только для студентов'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        # Находим все записи уроков из групп, где состоит текущий пользователь-студент
        recordings = LessonRecording.objects.filter(
            status='ready'
        ).filter(
            Q(visibility=LessonRecording.Visibility.ALL_TEACHER_GROUPS,
              lesson__teacher__teaching_groups__students=user)
            | Q(allowed_groups__students=user)
            | Q(allowed_students=user)
        ).select_related(
            'lesson',
            'lesson__group',
            'lesson__teacher'
        ).prefetch_related('allowed_groups', 'allowed_students').order_by('-lesson__start_time').distinct()
        
        # Фильтры
        group_id = request.query_params.get('group_id')
        if group_id:
            recordings = recordings.filter(
                Q(lesson__group_id=group_id) |
                Q(allowed_groups__id=group_id)
            )
        
        # Поиск по названию
        search = request.query_params.get('search')
        if search:
            recordings = recordings.filter(lesson__title__icontains=search)
        
        # Пагинация
        from rest_framework.pagination import PageNumberPagination
        paginator = PageNumberPagination()
        paginator.page_size = 20
        paginated_recordings = paginator.paginate_queryset(recordings, request)
        
        serializer = LessonRecordingSerializer(paginated_recordings, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    except Exception:
        # Любые точечные ошибки выше перехватим ниже общим блоком
        raise
    except Exception as e:
        logger.exception(f"Error loading recordings: {e}")
        return Response({
            'error': 'Ошибка загрузки записей'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def sync_missing_zoom_recordings_for_teacher(teacher):
    """Подтягивает облачные записи Zoom, если вебхук не пришел."""
    from .zoom_client import ZoomAPIClient
    
    # Проверяем что у учителя настроены Zoom credentials
    if not (teacher.zoom_account_id and teacher.zoom_client_id and teacher.zoom_client_secret):
        logger.warning(f"Cannot sync recordings: teacher {teacher.email} has no Zoom credentials")
        return 0
    
    try:
        now = timezone.now()
        recent_from = now - timedelta(days=3)

        # Ищем уроки без записей за последние 3 дня
        lessons_to_sync = Lesson.objects.filter(
            teacher=teacher,
            record_lesson=True,
            zoom_meeting_id__isnull=False,
            start_time__lte=now,
            start_time__gte=recent_from,
        ).filter(lessonrecording__isnull=True).distinct()

        if not lessons_to_sync:
            return 0

        # Создаём клиент с credentials учителя
        zoom_client = ZoomAPIClient(
            account_id=teacher.zoom_account_id,
            client_id=teacher.zoom_client_id,
            client_secret=teacher.zoom_client_secret
        )
        
        recordings_response = zoom_client.list_user_recordings(
            user_id=teacher.zoom_user_id or 'me',
            from_date=recent_from.date().isoformat(),
            to_date=now.date().isoformat(),
        )

        meetings = recordings_response.get('meetings', [])
        meetings_by_id = {str(m.get('id')): m for m in meetings if m.get('id')}

        synced = 0

        for lesson in lessons_to_sync:
            meeting_data = meetings_by_id.get(str(lesson.zoom_meeting_id))
            if not meeting_data:
                continue

            recording_files = meeting_data.get('recording_files', [])
            passcode = meeting_data.get('recording_play_passcode') or meeting_data.get('password')

            def apply_passcode(url, pwd):
                if not url or not pwd:
                    return url
                if 'pwd=' in url:
                    return url
                separator = '&' if '?' in url else '?'
                return f"{url}{separator}pwd={pwd}"
            for rec_file in recording_files:
                file_type = str(rec_file.get('file_type', '')).lower()
                # Только MP4 видео, пропускаем аудио и timeline JSON
                if file_type not in ['mp4']:
                    continue

                # Время записи из Zoom
                def parse_dt(val):
                    if not val:
                        return None
                    try:
                        return datetime.fromisoformat(val.replace('Z', '+00:00'))
                    except Exception:
                        return None

                rec_start = parse_dt(rec_file.get('recording_start'))
                rec_end = parse_dt(rec_file.get('recording_end'))
                rec_duration = None
                if rec_start and rec_end:
                    rec_duration = int((rec_end - rec_start).total_seconds())

                play_url = apply_passcode(rec_file.get('play_url', ''), passcode)
                download_url = apply_passcode(rec_file.get('download_url', ''), passcode)

                lr, created = LessonRecording.objects.get_or_create(
                    lesson=lesson,
                    zoom_recording_id=rec_file.get('id', ''),
                    defaults={
                        'download_url': download_url,
                        'play_url': play_url,
                        'recording_type': rec_file.get('recording_type', ''),
                        'file_size': rec_file.get('file_size', 0),
                        'status': 'ready',
                        'visibility': LessonRecording.Visibility.LESSON_GROUP,
                        'storage_provider': 'zoom',
                        'recording_start': rec_start,
                        'recording_end': rec_end,
                        'duration': rec_duration,
                    }
                )

                if not created:
                    lr.download_url = download_url
                    lr.play_url = play_url
                    lr.recording_type = rec_file.get('recording_type', '')
                    lr.file_size = rec_file.get('file_size', 0)
                    lr.status = 'ready'
                    lr.storage_provider = 'zoom'
                    lr.recording_start = rec_start or lr.recording_start
                    lr.recording_end = rec_end or lr.recording_end
                    if rec_duration:
                        lr.duration = rec_duration
                    lr.save()

                if lesson.recording_available_for_days > 0 and not lr.available_until:
                    lr.available_until = timezone.now() + timedelta(days=lesson.recording_available_for_days)
                    lr.save()

                lr.apply_privacy(
                    privacy_type=LessonRecording.Visibility.LESSON_GROUP,
                    teacher=lesson.teacher,
                )

                synced += 1

        if synced:
            logger.info(f"Synced {synced} Zoom recording(s) for teacher {teacher.id}")
        return synced

    except Exception as e:
        logger.exception(f"Failed to sync Zoom recordings for teacher {teacher.id}: {e}")
        return 0


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_recordings_list(request):
    """
    Список всех записей уроков преподавателя
    GET /schedule/api/recordings/teacher/
    """
    user = request.user
    
    # Только для преподавателей
    if getattr(user, 'role', None) != 'teacher':
        return Response({
            'error': 'Доступ только для преподавателей'
        }, status=status.HTTP_403_FORBIDDEN)
    # Требуем активную подписку
    try:
        require_active_subscription(user)
    except Exception as e:
        return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        # Подтягиваем записи напрямую из Zoom, если вебхук не сработал
        try:
            sync_missing_zoom_recordings_for_teacher(user)
        except Exception:
            # Ошибка уже залогирована внутри
            pass

        # Все записи уроков преподавателя:
        # 1. Записи привязанные к урокам учителя
        # 2. Standalone записи (lesson=None), где teacher=user
        recordings = LessonRecording.objects.filter(
            Q(lesson__teacher=user) |
            Q(lesson__isnull=True, teacher=user)
        ).select_related(
            'lesson',
            'lesson__group',
            'teacher'
        ).prefetch_related('allowed_groups', 'allowed_students').order_by('-created_at').distinct()
        
        # Фильтры
        group_id = request.query_params.get('group_id')
        if group_id:
            recordings = recordings.filter(
                Q(lesson__group_id=group_id) |
                Q(allowed_groups__id=group_id)
            )
        
        status_filter = request.query_params.get('status')
        if status_filter:
            recordings = recordings.filter(status=status_filter)
        
        # Поиск
        search = request.query_params.get('search')
        if search:
            recordings = recordings.filter(lesson__title__icontains=search)
        
        # Пагинация
        from rest_framework.pagination import PageNumberPagination
        paginator = PageNumberPagination()
        paginator.page_size = 20
        paginated_recordings = paginator.paginate_queryset(recordings, request)
        
        serializer = LessonRecordingSerializer(paginated_recordings, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    except Exception as e:
        logger.exception(f"Error loading teacher recordings: {e}")
        return Response({
            'error': 'Ошибка загрузки записей'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'DELETE'])
@permission_classes([IsAuthenticated])
def recording_detail(request, recording_id):
    """
    Детальная информация о записи урока
    GET /schedule/api/recordings/<id>/
    DELETE /schedule/api/recordings/<id>/
    """
    user = request.user
    
    if request.method == 'DELETE':
        # Удаление записи (только преподаватель-владелец)
        if getattr(user, 'role', None) != 'teacher':
            return Response({
                'error': 'Только преподаватели могут удалять записи'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Требуем активную подписку
        try:
            require_active_subscription(user)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            recording = LessonRecording.objects.select_related(
                'lesson', 'lesson__group', 'teacher'
            ).get(id=recording_id)
            
            # Проверка что запись принадлежит преподавателю
            # Для обычных записей: lesson.teacher_id == user.id
            # Для standalone записей: teacher_id == user.id
            is_owner = False
            if recording.lesson_id and recording.lesson:
                is_owner = recording.lesson.teacher_id == user.id
            elif recording.teacher_id:
                is_owner = recording.teacher_id == user.id
            
            if not is_owner:
                return Response({
                    'error': 'У вас нет прав на удаление этой записи'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Удаляем файл из Google Drive
            if recording.gdrive_file_id:
                try:
                    from .gdrive_utils import get_gdrive_manager
                    gdrive = get_gdrive_manager()
                    gdrive.delete_file(recording.gdrive_file_id)
                    logger.info(f"Deleted file {recording.gdrive_file_id} from Google Drive")
                except Exception as e:
                    logger.error(f"Failed to delete file from Google Drive: {e}")
                    # Продолжаем удаление записи из БД даже если не удалось из Drive
            
            # Освобождаем квоту преподавателя
            if recording.file_size:
                try:
                    quota = user.storage_quota
                    quota.remove_recording(recording.file_size)
                    logger.info(f"Freed {recording.file_size} bytes for teacher {user.id}")
                except Exception as e:
                    logger.error(f"Failed to update quota: {e}")
            
            # Удаляем запись из БД
            recording_id_str = str(recording.id)
            recording_title = recording.lesson.title if recording.lesson_id and recording.lesson else recording.title
            recording.delete()
            
            logger.info(f"Teacher {user.id} deleted recording {recording_id_str} ({recording_title})")
            
            return Response({
                'message': 'Запись успешно удалена',
                'recording_id': recording_id_str
            }, status=status.HTTP_200_OK)
        
        except LessonRecording.DoesNotExist:
            return Response({
                'error': 'Запись не найдена'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.exception(f"Error deleting recording: {e}")
            return Response({
                'error': 'Ошибка удаления записи'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # GET method
    try:
        recording = LessonRecording.objects.select_related(
            'lesson',
            'lesson__group',
            'lesson__teacher'
        ).prefetch_related('allowed_groups', 'allowed_students').get(id=recording_id)
        
        if not _user_has_recording_access(user, recording):
            return Response({
                'error': 'У вас нет доступа к этой записи'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = LessonRecordingSerializer(recording)
        return Response(serializer.data)
    
    except LessonRecording.DoesNotExist:
        return Response({
            'error': 'Запись не найдена'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.exception(f"Error loading recording detail: {e}")
        return Response({
            'error': 'Ошибка загрузки записи'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def recording_track_view(request, recording_id):
    """
    Отслеживание просмотра записи (увеличить счетчик)
    POST /schedule/api/recordings/<id>/view/
    """
    user = request.user
    
    try:
        recording = LessonRecording.objects.select_related('lesson', 'lesson__group').prefetch_related('allowed_groups', 'allowed_students').get(id=recording_id)
        
        if not _user_has_recording_access(user, recording):
            return Response({
                'error': 'У вас нет доступа к этой записи'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Увеличиваем счетчик просмотров
        recording.views_count = F('views_count') + 1
        recording.save(update_fields=['views_count'])
        recording.refresh_from_db()
        
        logger.info(f"Recording {recording_id} viewed by user {user.id}, total views: {recording.views_count}")
        
        return Response({
            'success': True,
            'views_count': recording.views_count
        })
    
    except LessonRecording.DoesNotExist:
        return Response({
            'error': 'Запись не найдена'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.exception(f"Error tracking recording view: {e}")
        return Response({
            'error': 'Ошибка отслеживания просмотра'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_recording(request, recording_id):
    """
    Удалить запись урока (только преподаватель)
    DELETE /schedule/api/recordings/<id>/
    """
    user = request.user
    
    # Только преподаватели могут удалять записи
    if getattr(user, 'role', None) != 'teacher':
        return Response({
            'error': 'Только преподаватели могут удалять записи'
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Требуем активную подписку
    try:
        require_active_subscription(user)
    except Exception as e:
        return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        recording = LessonRecording.objects.select_related(
            'lesson__group__teacher'
        ).get(id=recording_id)
        
        # Проверка что запись принадлежит преподавателю
        if recording.lesson.teacher_id != user.id:
            return Response({
                'error': 'У вас нет прав на удаление этой записи'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Удаляем файл из Google Drive
        if recording.gdrive_file_id:
            try:
                from .gdrive_utils import get_gdrive_manager
                gdrive = get_gdrive_manager()
                gdrive.delete_file(recording.gdrive_file_id)
                logger.info(f"Deleted file {recording.gdrive_file_id} from Google Drive")
            except Exception as e:
                logger.error(f"Failed to delete file from Google Drive: {e}")
                # Продолжаем удаление записи из БД даже если не удалось из Drive
        
        # Освобождаем квоту преподавателя
        if recording.file_size:
            try:
                quota = user.storage_quota
                quota.remove_recording(recording.file_size)
                logger.info(f"Freed {recording.file_size} bytes for teacher {user.id}")
            except Exception as e:
                logger.error(f"Failed to update quota: {e}")
        
        # Удаляем запись из БД
        recording_id_str = str(recording.id)
        lesson_title = recording.lesson.title
        recording.delete()
        
        logger.info(f"Teacher {user.id} deleted recording {recording_id_str} ({lesson_title})")
        
        return Response({
            'message': 'Запись успешно удалена',
            'recording_id': recording_id_str
        }, status=status.HTTP_200_OK)
    
    except LessonRecording.DoesNotExist:
        return Response({
            'error': 'Запись не найдена'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.exception(f"Error deleting recording: {e}")
        return Response({
            'error': 'Ошибка удаления записи'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def lesson_recording(request, lesson_id):
    """
    Получить запись конкретного урока
    GET /schedule/api/lessons/<id>/recording/
    """
    user = request.user
    
    try:
        lesson = Lesson.objects.select_related('group', 'teacher').get(id=lesson_id)

        role = getattr(user, 'role', None)
        base_access = False
        if role == 'admin':
            base_access = True
        elif role == 'teacher' and lesson.teacher_id == user.id:
            base_access = True
        elif role == 'student' and lesson.group and lesson.group.students.filter(id=user.id).exists():
            base_access = True

        try:
            recording = LessonRecording.objects.select_related(
                'lesson',
                'lesson__group',
                'lesson__teacher'
            ).prefetch_related('allowed_groups', 'allowed_students').get(lesson_id=lesson_id, status='ready')

            if not base_access and not _user_has_recording_access(user, recording):
                return Response({
                    'error': 'У вас нет доступа к этой записи'
                }, status=status.HTTP_403_FORBIDDEN)

            serializer = LessonRecordingSerializer(recording)
            return Response(serializer.data)

        except LessonRecording.DoesNotExist:
            if not base_access:
                return Response({
                    'error': 'У вас нет доступа к этому уроку'
                }, status=status.HTTP_403_FORBIDDEN)

            processing = LessonRecording.objects.filter(
                lesson_id=lesson_id,
                status='processing'
            ).exists()
            
            if processing:
                return Response({
                    'status': 'processing',
                    'message': 'Запись обрабатывается, попробуйте позже'
                }, status=status.HTTP_202_ACCEPTED)
            else:
                return Response({
                    'status': 'not_found',
                    'message': 'Запись урока не найдена'
                }, status=status.HTTP_404_NOT_FOUND)
    
    except Lesson.DoesNotExist:
        return Response({
            'error': 'Урок не найден'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.exception(f"Error loading lesson recording: {e}")
        return Response({
            'error': 'Ошибка загрузки записи'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class IndividualInviteCodeViewSet(viewsets.ModelViewSet):
    """ViewSet для управления индивидуальными инвайт-кодами"""
    queryset = IndividualInviteCode.objects.all()
    serializer_class = IndividualInviteCodeSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Фильтруем коды по пользователю"""
        user = self.request.user
        if user.role == 'teacher':
            # Учитель видит только свои коды
            return IndividualInviteCode.objects.filter(teacher=user).order_by('-created_at')
        elif user.role == 'student':
            # Ученик видит коды которыми он воспользовался
            return IndividualInviteCode.objects.filter(used_by=user).order_by('-used_at')
        else:
            # Админ видит все
            return IndividualInviteCode.objects.all().order_by('-created_at')
    
    def create(self, request, *args, **kwargs):
        """Создать новый инвайт-код (только учителя)"""
        if request.user.role != 'teacher':
            return Response(
                {'error': 'Только учителя могут создавать инвайт-коды'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        subject = request.data.get('subject', '').strip()
        if not subject:
            return Response(
                {'error': 'Название предмета обязательно'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Создаем код
        invite_code = IndividualInviteCode(
            teacher=request.user,
            subject=subject
        )
        invite_code.save()
        
        serializer = self.get_serializer(invite_code)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def destroy(self, request, *args, **kwargs):
        """Удалить инвайт-код (может удалить только учитель-создатель или админ)"""
        obj = self.get_object()
        
        if request.user.role != 'admin' and obj.teacher != request.user:
            return Response(
                {'error': 'Вы не можете удалить этот инвайт-код'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if obj.is_used:
            return Response(
                {'error': 'Нельзя удалить использованный инвайт-код'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return super().destroy(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        """Обновить инвайт-код (редактировать предмет)"""
        obj = self.get_object()
        
        if request.user.role != 'admin' and obj.teacher != request.user:
            return Response(
                {'error': 'Вы не можете редактировать этот инвайт-код'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        subject = request.data.get('subject', '').strip()
        if not subject:
            return Response(
                {'error': 'Название предмета обязательно'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        old_subject = obj.subject
        obj.subject = subject
        obj.save()
        
        # Если код уже использован, обновляем название группы
        if obj.is_used:
            old_group_name = f"Индивидуально • {old_subject}"
            new_group_name = f"Индивидуально • {subject}"
            Group.objects.filter(teacher=obj.teacher, name=old_group_name).update(name=new_group_name)
        
        serializer = self.get_serializer(obj)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def regenerate(self, request):
        """Регенерировать инвайт-код (создать новый неиспользованный код)"""
        if request.user.role != 'teacher':
            return Response(
                {'error': 'Только учителя могут регенерировать коды'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        invite_code_id = request.data.get('id')
        if not invite_code_id:
            return Response(
                {'error': 'ID инвайт-кода не указан'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            code_obj = IndividualInviteCode.objects.get(id=invite_code_id, teacher=request.user)
        except IndividualInviteCode.DoesNotExist:
            return Response(
                {'error': 'Инвайт-код не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if code_obj.is_used:
            return Response(
                {'error': 'Нельзя регенерировать использованный код'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Генерируем новый код
        code_obj.generate_invite_code()
        
        serializer = self.get_serializer(code_obj)
        return Response({
            'message': 'Код успешно сгенерирован',
            'code': serializer.data
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def preview_by_code(self, request):
        """Получить информацию по инвайт-коду (без присоединения)"""
        invite_code = request.query_params.get('code', '').strip().upper()
        if not invite_code:
            return Response(
                {'error': 'Код приглашения не указан'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            code_obj = IndividualInviteCode.objects.select_related('teacher').get(invite_code=invite_code)
        except IndividualInviteCode.DoesNotExist:
            return Response(
                {'error': 'Инвайт-код не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if code_obj.is_used:
            return Response(
                {'error': 'Этот инвайт-код уже использован'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(code_obj)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def join_by_code(self, request):
        """Присоединиться к предмету учителя по инвайт-коду"""
        invite_code = request.data.get('invite_code', '').strip().upper()
        if not invite_code:
            return Response(
                {'error': 'Код приглашения не указан'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = request.user
        if user.role != 'student':
            return Response(
                {'error': 'Только ученики могут присоединяться по инвайт-коду'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            code_obj = IndividualInviteCode.objects.select_related('teacher').get(invite_code=invite_code)
        except IndividualInviteCode.DoesNotExist:
            return Response(
                {'error': 'Инвайт-код не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if code_obj.is_used:
            return Response(
                {'error': 'Этот инвайт-код уже был использован'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Привязываем ученика к индивидуальной группе учителя, чтобы он видел уроки/материалы
        group_name = f"Индивидуально • {code_obj.subject}"
        group = Group.objects.filter(teacher=code_obj.teacher, name=group_name).first()
        if not group:
            group = Group.objects.create(
                name=group_name,
                teacher=code_obj.teacher,
                description='Автосозданная группа для индивидуального ученика по инвайт-коду'
            )
        group.students.add(user)

        # Отмечаем код как использованный
        code_obj.is_used = True
        code_obj.used_by = user
        code_obj.used_at = timezone.now()
        code_obj.save()
        
        serializer = self.get_serializer(code_obj)
        return Response({
            'message': f'Вы успешно присоединились к предмету "{code_obj.subject}" преподавателя {code_obj.teacher.get_full_name()}',
            'code': serializer.data,
            'teacher': {
                'id': code_obj.teacher.id,
                'email': code_obj.teacher.email,
                'first_name': code_obj.teacher.first_name,
                'last_name': code_obj.teacher.last_name
            },
            'group': {
                'id': group.id,
                'name': group.name,
                'invite_code': group.invite_code
            }
        }, status=status.HTTP_200_OK)


# ============================================
# LessonMaterial ViewSet (Miro, конспекты, файлы)
# ============================================

from .models import LessonMaterial
from .serializers import LessonMaterialSerializer


class LessonMaterialViewSet(viewsets.ModelViewSet):
    """ViewSet для управления учебными материалами (Miro, конспекты, файлы)"""
    queryset = LessonMaterial.objects.all()
    serializer_class = LessonMaterialSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Фильтруем материалы по пользователю и параметрам"""
        user = self.request.user
        qs = LessonMaterial.objects.select_related('lesson', 'uploaded_by', 'lesson__group')
        
        if user.role == 'teacher':
            qs = qs.filter(uploaded_by=user)
        elif user.role == 'student':
            # Студент видит материалы доступных ему уроков
            from django.db.models import Q
            student_groups = user.enrolled_groups.all()
            qs = qs.filter(
                Q(lesson__group__in=student_groups) |
                Q(visibility='all_teacher_groups', lesson__group__in=student_groups) |
                Q(visibility='custom_groups', allowed_groups__in=student_groups) |
                Q(visibility='custom_students', allowed_students=user)
            ).distinct()
        
        # Фильтр по типу материала
        material_type = self.request.query_params.get('type')
        if material_type:
            qs = qs.filter(material_type=material_type)
        
        # Фильтр по уроку
        lesson_id = self.request.query_params.get('lesson_id')
        if lesson_id:
            qs = qs.filter(lesson_id=lesson_id)
        
        return qs.order_by('order', '-uploaded_at')
    
    def create(self, request, *args, **kwargs):
        """Создать новый материал"""
        if request.user.role != 'teacher':
            return Response(
                {'error': 'Только учителя могут создавать материалы'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        data = request.data.copy()
        
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(uploaded_by=request.user)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        """Обновить материал"""
        obj = self.get_object()
        
        if request.user.role != 'teacher' or obj.uploaded_by != request.user:
            return Response(
                {'error': 'Нельзя редактировать чужие материалы'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """Удалить материал"""
        obj = self.get_object()
        
        if request.user.role != 'admin' and obj.uploaded_by != request.user:
            return Response(
                {'error': 'Нельзя удалить чужой материал'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().destroy(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def view(self, request, pk=None):
        """Трекинг просмотра материала"""
        material = self.get_object()
        material.views_count += 1
        material.save(update_fields=['views_count'])
        return Response({'views_count': material.views_count})
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def teacher_materials(self, request):
        """Получить все материалы учителя с группировкой по типу"""
        if request.user.role != 'teacher':
            return Response(
                {'error': 'Только для учителей'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        materials = LessonMaterial.objects.filter(uploaded_by=request.user).order_by('order', '-uploaded_at')
        
        # Группируем по типу
        grouped = {
            'miro': [],
            'notes': [],
            'document': [],
            'link': [],
            'image': [],
        }
        
        for material in materials:
            serialized = LessonMaterialSerializer(material).data
            if material.material_type in grouped:
                grouped[material.material_type].append(serialized)
        
        # Статистика
        stats = {
            'total': materials.count(),
            'miro_count': len(grouped['miro']),
            'notes_count': len(grouped['notes']),
            'documents_count': len(grouped['document']),
            'links_count': len(grouped['link']),
        }
        
        return Response({
            'materials': grouped,
            'stats': stats
        })


# ============================================
# Miro Integration API
# ============================================

import requests
import re
from django.conf import settings as django_settings


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def miro_add_board(request):
    """
    Добавить доску Miro как материал урока.
    Принимает URL доски Miro и извлекает информацию.
    """
    if request.user.role != 'teacher':
        return Response(
            {'error': 'Только учителя могут добавлять доски Miro'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    board_url = request.data.get('board_url', '').strip()
    title = request.data.get('title', '').strip()
    description = request.data.get('description', '').strip()
    lesson_id = request.data.get('lesson_id')
    visibility = request.data.get('visibility', 'lesson_group')
    
    if not board_url:
        return Response(
            {'error': 'URL доски Miro обязателен'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Извлекаем board_id из URL
    # Форматы: https://miro.com/app/board/uXjVK...=/ или https://miro.com/welcomeonboard/...
    board_id = None
    
    # Паттерн 1: /app/board/{board_id}/
    match = re.search(r'/app/board/([a-zA-Z0-9_=-]+)', board_url)
    if match:
        board_id = match.group(1)
    
    # Паттерн 2: /welcomeonboard/{board_id}
    if not board_id:
        match = re.search(r'/welcomeonboard/([a-zA-Z0-9_=-]+)', board_url)
        if match:
            board_id = match.group(1)
    
    if not board_id:
        return Response(
            {'error': 'Не удалось извлечь ID доски из URL. Убедитесь, что это корректная ссылка на Miro доску.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Формируем embed URL для iframe
    embed_url = f"https://miro.com/app/live-embed/{board_id}/?autoplay=yep"
    
    # Проверяем, существует ли урок (если указан)
    lesson = None
    if lesson_id:
        try:
            lesson = Lesson.objects.get(id=lesson_id, teacher=request.user)
        except Lesson.DoesNotExist:
            return Response(
                {'error': 'Урок не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    # Создаем материал
    material = LessonMaterial.objects.create(
        uploaded_by=request.user,
        lesson=lesson,
        material_type=LessonMaterial.MaterialType.MIRO_BOARD,
        title=title or f"Доска Miro",
        description=description,
        miro_board_id=board_id,
        miro_board_url=board_url,
        miro_embed_url=embed_url,
        visibility=visibility
    )
    
    # Добавляем группы если нужно
    if visibility == 'custom_groups':
        group_ids = request.data.get('allowed_groups', [])
        if group_ids:
            groups = Group.objects.filter(id__in=group_ids, teacher=request.user)
            material.allowed_groups.set(groups)
    
    # Добавляем студентов если нужно
    if visibility == 'custom_students':
        student_ids = request.data.get('allowed_students', [])
        if student_ids:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            teacher_groups = Group.objects.filter(teacher=request.user)
            students = User.objects.filter(
                id__in=student_ids,
                role='student',
                enrolled_groups__in=teacher_groups
            ).distinct()
            material.allowed_students.set(students)
    
    serializer = LessonMaterialSerializer(material)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def miro_create_board(request):
    """
    Создать новую доску Miro через API (требует OAuth токен).
    Если токен не настроен, возвращает инструкции.
    """
    if request.user.role != 'teacher':
        return Response(
            {'error': 'Только учителя могут создавать доски Miro'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Проверяем наличие Miro credentials
    miro_access_token = getattr(django_settings, 'MIRO_ACCESS_TOKEN', None) or os.environ.get('MIRO_ACCESS_TOKEN')
    
    if not miro_access_token:
        return Response({
            'error': 'Miro API не настроен',
            'instructions': {
                'step1': 'Создайте приложение на https://miro.com/app/settings/user-profile/apps',
                'step2': 'Получите access token с scope: boards:read, boards:write',
                'step3': 'Добавьте MIRO_ACCESS_TOKEN в переменные окружения',
                'alternative': 'Или используйте miro_add_board для добавления существующей доски по URL'
            }
        }, status=status.HTTP_501_NOT_IMPLEMENTED)
    
    board_name = request.data.get('name', '').strip() or 'Новая доска'
    description = request.data.get('description', '').strip()
    lesson_id = request.data.get('lesson_id')
    
    # Создаем доску через Miro API
    try:
        response = requests.post(
            'https://api.miro.com/v2/boards',
            headers={
                'Authorization': f'Bearer {miro_access_token}',
                'Content-Type': 'application/json'
            },
            json={
                'name': board_name,
                'description': description,
                'sharingPolicy': {
                    'access': 'view',
                    'inviteToAccountAndBoardLinkAccess': 'viewer'
                }
            },
            timeout=15
        )
        
        if response.status_code not in (200, 201):
            return Response({
                'error': 'Ошибка создания доски в Miro',
                'details': response.json() if response.text else response.status_code
            }, status=status.HTTP_502_BAD_GATEWAY)
        
        board_data = response.json()
        board_id = board_data.get('id')
        board_url = board_data.get('viewLink')
        embed_url = f"https://miro.com/app/live-embed/{board_id}/?autoplay=yep"
        
    except requests.RequestException as e:
        return Response({
            'error': 'Не удалось подключиться к Miro API',
            'details': str(e)
        }, status=status.HTTP_502_BAD_GATEWAY)
    
    # Проверяем урок
    lesson = None
    if lesson_id:
        try:
            lesson = Lesson.objects.get(id=lesson_id, teacher=request.user)
        except Lesson.DoesNotExist:
            pass
    
    # Создаем материал
    material = LessonMaterial.objects.create(
        uploaded_by=request.user,
        lesson=lesson,
        material_type=LessonMaterial.MaterialType.MIRO_BOARD,
        title=board_name,
        description=description,
        miro_board_id=board_id,
        miro_board_url=board_url,
        miro_embed_url=embed_url,
        visibility=LessonMaterial.Visibility.LESSON_GROUP
    )
    
    serializer = LessonMaterialSerializer(material)
    return Response({
        'material': serializer.data,
        'miro_board': board_data
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_notes(request):
    """
    Добавить конспект (текстовый материал) к уроку.
    """
    if request.user.role != 'teacher':
        return Response(
            {'error': 'Только учителя могут добавлять конспекты'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    title = request.data.get('title', '').strip()
    content = request.data.get('content', '').strip()
    description = request.data.get('description', '').strip()
    lesson_id = request.data.get('lesson_id')
    visibility = request.data.get('visibility', 'lesson_group')
    
    if not title:
        return Response(
            {'error': 'Название конспекта обязательно'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Проверяем урок
    lesson = None
    if lesson_id:
        try:
            lesson = Lesson.objects.get(id=lesson_id, teacher=request.user)
        except Lesson.DoesNotExist:
            return Response(
                {'error': 'Урок не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    # Создаем материал
    material = LessonMaterial.objects.create(
        uploaded_by=request.user,
        lesson=lesson,
        material_type=LessonMaterial.MaterialType.NOTES,
        title=title,
        description=description,
        content=content,
        visibility=visibility
    )
    
    # Добавляем группы если нужно
    if visibility == 'custom_groups':
        group_ids = request.data.get('allowed_groups', [])
        if group_ids:
            groups = Group.objects.filter(id__in=group_ids, teacher=request.user)
            material.allowed_groups.set(groups)
    
    # Добавляем студентов если нужно
    if visibility == 'custom_students':
        student_ids = request.data.get('allowed_students', [])
        if student_ids:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            # Только студенты из групп учителя
            teacher_groups = Group.objects.filter(teacher=request.user)
            students = User.objects.filter(
                id__in=student_ids,
                role='student',
                enrolled_groups__in=teacher_groups
            ).distinct()
            material.allowed_students.set(students)
    
    serializer = LessonMaterialSerializer(material)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_document(request):
    """
    Добавить документ/ссылку как материал урока.
    """
    if request.user.role != 'teacher':
        return Response(
            {'error': 'Только учителя могут добавлять документы'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    title = request.data.get('title', '').strip()
    file_url = request.data.get('file_url', '').strip()
    description = request.data.get('description', '').strip()
    lesson_id = request.data.get('lesson_id')
    material_type = request.data.get('material_type', 'document')
    visibility = request.data.get('visibility', 'lesson_group')
    
    if not title:
        return Response(
            {'error': 'Название документа обязательно'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not file_url:
        return Response(
            {'error': 'Ссылка на файл обязательна'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Определяем тип материала
    if material_type not in ('document', 'link', 'image'):
        material_type = 'document'
    
    # Проверяем урок
    lesson = None
    if lesson_id:
        try:
            lesson = Lesson.objects.get(id=lesson_id, teacher=request.user)
        except Lesson.DoesNotExist:
            return Response(
                {'error': 'Урок не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    # Создаем материал
    material = LessonMaterial.objects.create(
        uploaded_by=request.user,
        lesson=lesson,
        material_type=material_type,
        title=title,
        description=description,
        file_url=file_url,
        file_name=request.data.get('file_name', ''),
        file_size_bytes=request.data.get('file_size_bytes', 0) or 0,
        visibility=visibility
    )
    
    # Добавляем группы если нужно
    if visibility == 'custom_groups':
        group_ids = request.data.get('allowed_groups', [])
        if group_ids:
            groups = Group.objects.filter(id__in=group_ids, teacher=request.user)
            material.allowed_groups.set(groups)
    
    # Добавляем студентов если нужно
    if visibility == 'custom_students':
        student_ids = request.data.get('allowed_students', [])
        if student_ids:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            teacher_groups = Group.objects.filter(teacher=request.user)
            students = User.objects.filter(
                id__in=student_ids,
                role='student',
                enrolled_groups__in=teacher_groups
            ).distinct()
            material.allowed_students.set(students)
    
    serializer = LessonMaterialSerializer(material)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def miro_status(request):
    """
    Проверить статус интеграции с Miro.
    """
    miro_access_token = getattr(django_settings, 'MIRO_ACCESS_TOKEN', None) or os.environ.get('MIRO_ACCESS_TOKEN')
    
    return Response({
        'miro_api_configured': bool(miro_access_token),
        'can_add_boards': True,  # Всегда можно добавить по URL
        'can_create_boards': bool(miro_access_token),  # Только с API
        'instructions': {
            'add_existing': 'Скопируйте URL доски Miro и добавьте её через API',
            'create_new': 'Для создания новых досок через API настройте MIRO_ACCESS_TOKEN'
        }
    })
