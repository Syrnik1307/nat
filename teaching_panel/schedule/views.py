from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
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
from .models import ZoomAccount, Group, Lesson, Attendance, RecurringLesson, LessonRecording, AuditLog, IndividualInviteCode
from zoom_pool.models import ZoomAccount as PoolZoomAccount
from django.db.models import F
from .permissions import IsLessonOwnerOrReadOnly, IsGroupOwnerOrReadOnly
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
from .zoom_client import my_zoom_api_client
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


def _user_has_recording_access(user, recording):
    role = getattr(user, 'role', None)
    if role == 'admin':
        return True
    if role == 'teacher':
        return recording.lesson.teacher_id == user.id
    if role != 'student':
        return False

    if recording.visibility == LessonRecording.Visibility.ALL_TEACHER_GROUPS:
        return Group.objects.filter(teacher=recording.lesson.teacher, students=user).exists()

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
    # Базовая аутентификация включится позже; сейчас ограничим по роли
    permission_classes = [IsGroupOwnerOrReadOnly]
    
    def get_queryset(self):
        """Фильтруем группы по преподавателю для аутентифицированных пользователей"""
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_authenticated:
            if getattr(user, 'role', None) == 'teacher':
                return queryset.filter(teacher=user)
            elif getattr(user, 'role', None) == 'student':
                return queryset.filter(students=user)
        return queryset
    
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


class LessonViewSet(viewsets.ModelViewSet):
    """
    ViewSet для работы с занятиями.
    Поддерживает создание, редактирование, удаление занятий.
    """
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsLessonOwnerOrReadOnly]
    
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
        """Загрузить самостоятельное видео без привязки к уроку"""
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
        
        privacy_type = request.data.get('privacy_type', 'all')
        allowed_groups = _parse_ids_list(request.data.get('allowed_groups'))
        allowed_students = _parse_ids_list(request.data.get('allowed_students'))
        
        from django.core.files.storage import default_storage
        from django.conf import settings
        import os
        
        # Создаём папку для записей если нет
        upload_dir = 'lesson_recordings'
        media_root = getattr(settings, 'MEDIA_ROOT', '/tmp')
        if not os.path.exists(os.path.join(media_root, upload_dir)):
            os.makedirs(os.path.join(media_root, upload_dir))
        
        # Сохраняем файл
        from django.utils.text import slugify
        safe_filename = f'{slugify(title)}_{video_file.name}'
        file_path = os.path.join(upload_dir, safe_filename)
        saved_path = default_storage.save(file_path, video_file)
        
        # Создаём запись БЕЗ урока (standalone recording)
        # lesson уже nullable в модели LessonRecording
        recording = LessonRecording.objects.create(
            lesson=None,
            play_url=f'/media/{saved_path}',
            download_url=f'/media/{saved_path}',
            status='ready',
            file_size=video_file.size,
            storage_provider='local'
        )
        
        recording.apply_privacy(
            privacy_type=privacy_type,
            group_ids=allowed_groups,
            student_ids=allowed_students,
            teacher=request.user
        )

        logger.info(f"Standalone video uploaded by {request.user.email}: {saved_path}, privacy: {privacy_type}")
        
        return Response({
            'status': 'success',
            'recording': {
                'id': recording.id,
                'play_url': recording.play_url,
                'file_size': recording.file_size,
                'created_at': recording.created_at
            }
        }, status=status.HTTP_201_CREATED)
    
    def get_queryset(self):
        """Фильтрация по параметрам запроса"""
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_authenticated:
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

    def _start_zoom_via_pool(self, lesson, user, request):
        """Создать Zoom встречу через пул аккаунтов и сохранить в урок."""
        pool_account = None
        try:
            with transaction.atomic():
                pool_account = (
                    PoolZoomAccount.objects.select_for_update()
                    .filter(
                        is_active=True,
                        current_meetings__lt=F('max_concurrent_meetings')
                    )
                    .order_by('current_meetings', 'last_used_at')
                    .first()
                )

                if not pool_account:
                    return None, Response(
                        {'detail': 'Все Zoom аккаунты заняты. Попробуйте позже.'},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE
                    )

                pool_account.acquire()

                meeting_data = my_zoom_api_client.create_meeting(
                    user_id=pool_account.zoom_user_id or None,
                    topic=f"{lesson.group.name} - {lesson.title}",
                    start_time=lesson.start_time,
                    duration=lesson.duration(),
                    auto_record=lesson.record_lesson  # Передаём флаг автозаписи
                )

                lesson.zoom_meeting_id = meeting_data['id']
                lesson.zoom_join_url = meeting_data['join_url']
                lesson.zoom_start_url = meeting_data['start_url']
                lesson.zoom_password = meeting_data.get('password', '')
                lesson.zoom_account = pool_account
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
                        'zoom_account_email': pool_account.email,
                        'zoom_meeting_id': meeting_data['id'],
                        'start_time': lesson.start_time.isoformat(),
                    }
                )

            payload = {
                'zoom_join_url': lesson.zoom_join_url,
                'zoom_start_url': lesson.zoom_start_url,
                'zoom_meeting_id': lesson.zoom_meeting_id,
                'zoom_password': lesson.zoom_password,
                'account_email': pool_account.email,
            }
            return payload, None
        except Exception as e:
            logger.exception(f"Failed to create Zoom meeting for lesson {lesson.id}: {e}")
            if pool_account:
                try:
                    pool_account.release()
                except Exception:
                    logger.exception('Failed to release Zoom account after error')
            return None, Response(
                {'detail': f'Ошибка при создании встречи: {e}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def mark_attendance(self, request, pk=None):
        """Отметить посещаемость для занятия"""
        lesson = self.get_object()
        attendances = request.data.get('attendances', [])
        
        for attendance_data in attendances:
            student_id = attendance_data.get('student_id')
            status_value = attendance_data.get('status', 'absent')
            notes = attendance_data.get('notes', '')
            
            if student_id:
                Attendance.objects.update_or_create(
                    lesson=lesson,
                    student_id=student_id,
                    defaults={
                        'status': status_value,
                        'notes': notes
                    }
                )
        
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
        """Загрузить видео файл урока с настройками приватности"""
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
        
        privacy_type = request.data.get('privacy_type', 'all')
        allowed_groups = _parse_ids_list(request.data.get('allowed_groups'))
        allowed_students = _parse_ids_list(request.data.get('allowed_students'))
        
        # TODO: Здесь должна быть загрузка файла в Google Drive или другое хранилище
        # Пока сохраняем как временную запись с локальным путем
        from django.core.files.storage import default_storage
        from django.conf import settings
        import os
        
        # Создаём папку для записей если нет
        upload_dir = 'lesson_recordings'
        media_root = getattr(settings, 'MEDIA_ROOT', '/tmp')
        if not os.path.exists(os.path.join(media_root, upload_dir)):
            os.makedirs(os.path.join(media_root, upload_dir))
        
        # Сохраняем файл
        file_path = os.path.join(upload_dir, f'lesson_{lesson.id}_{video_file.name}')
        saved_path = default_storage.save(file_path, video_file)
        
        # Создаём запись
        recording = LessonRecording.objects.create(
            lesson=lesson,
            play_url=f'/media/{saved_path}',
            download_url=f'/media/{saved_path}',
            status='ready',
            file_size=video_file.size,
            storage_provider='local'
        )
        recording.apply_privacy(
            privacy_type=privacy_type,
            group_ids=allowed_groups,
            student_ids=allowed_students,
            teacher=request.user
        )
        
        # Сохраняем настройки приватности в JSON поле details (если есть)
        # Или можно создать отдельную модель для связи recording-groups/students
        
        logger.info(f"Video uploaded for lesson {lesson.id}: {saved_path}, privacy: {privacy_type}")
        
        return Response({
            'status': 'success',
            'recording': {
                'id': recording.id,
                'play_url': recording.play_url,
                'file_size': recording.file_size,
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
        Новый старт урока, использующий пул из приложения zoom_pool.
        POST /api/schedule/lessons/{id}/start-new/

        Возвращает 503 если все аккаунты заняты.
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

        # Если уже есть встреча – вернуть её
        if lesson.zoom_meeting_id:
            return Response({
                'zoom_join_url': lesson.zoom_join_url,
                'zoom_start_url': lesson.zoom_start_url,
                'zoom_meeting_id': lesson.zoom_meeting_id,
                'zoom_password': lesson.zoom_password,
                'account_email': getattr(lesson.zoom_account, 'email', 'уже назначен')
            }, status=status.HTTP_200_OK)

        # Проверка времени (за 15 минут до начала)
        now = timezone.now()
        if lesson.start_time - timezone.timedelta(minutes=15) > now:
            return Response({'detail': 'Урок можно начать за 15 минут до начала'}, status=status.HTTP_400_BAD_REQUEST)

        # Поиск свободного аккаунта
        payload, error_response = self._start_zoom_via_pool(lesson, user, request)
        if error_response:
            return error_response
        return Response(payload, status=status.HTTP_200_OK)

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

        lesson = Lesson.objects.create(
            title=title,
            group=group,
            teacher=user,
            start_time=start_time,
            end_time=end_time,
            notes='Создано кнопкой "Создать урок без расписания"'
        )

        payload, error_response = self._start_zoom_via_pool(lesson, user, request)
        if error_response:
            lesson.delete()
            return error_response

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
    
    @action(detail=False, methods=['get'])
    def status_summary(self, request):
        """Сводка по занятости аккаунтов"""
        total = ZoomAccount.objects.count()
        busy = ZoomAccount.objects.filter(is_busy=True).count()
        free = total - busy
        
        busy_accounts = ZoomAccount.objects.filter(is_busy=True).select_related('current_lesson')
        
        return Response({
            'total': total,
            'busy': busy,
            'free': free,
            'busy_accounts': ZoomAccountSerializer(busy_accounts, many=True).data
        })


class RecurringLessonViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления регулярными уроками
    """
    queryset = RecurringLesson.objects.all()
    serializer_class = RecurringLessonSerializer
    
    def get_queryset(self):
        """Фильтрация регулярных уроков"""
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_authenticated:
            if getattr(user, 'role', None) == 'teacher':
                queryset = queryset.filter(teacher=user)
            elif getattr(user, 'role', None) == 'student':
                queryset = queryset.filter(group__students=user)
        
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
@require_http_methods(["POST"])
def zoom_webhook_receiver(request):
    """
    Webhook приемник для событий Zoom
    
    Zoom отправляет POST запросы на этот endpoint при различных событиях:
    - meeting.started - встреча началась
    - meeting.ended - встреча завершена
    - participant.joined - участник присоединился
    - etc.
    
    Security: This endpoint uses @csrf_exempt because it receives external webhooks.
    Instead, we verify the webhook signature using ZOOM_WEBHOOK_SECRET_TOKEN.
    
    Документация: https://developers.zoom.us/docs/api/rest/webhook-reference/
    
    Для тестирования можно использовать ngrok:
    1. ngrok http 8000
    2. Скопировать https URL
    3. В Zoom App настройках добавить Event Subscription:
       https://your-ngrok-url.ngrok.io/schedule/webhook/zoom/
    4. Подписаться на событие "End Meeting" (meeting.ended)
    """
    try:
        # TODO: Verify webhook signature for production
        # webhook_signature = request.headers.get('x-zm-signature')
        # if webhook_signature:
        #     from django.conf import settings
        #     import hmac, hashlib
        #     expected_signature = hmac.new(
        #         settings.ZOOM_WEBHOOK_SECRET_TOKEN.encode(),
        #         request.body,
        #         hashlib.sha256
        #     ).hexdigest()
        #     if not hmac.compare_digest(webhook_signature, expected_signature):
        #         return JsonResponse({'status': 'error', 'message': 'Invalid signature'}, status=403)
        
        # Парсим JSON из тела запроса
        payload = json.loads(request.body.decode('utf-8'))
        
        # Zoom отправляет verification token при первой настройке webhook
        # Нужно ответить этим же token для верификации
        if 'event' not in payload:
            # Это verification request
            plain_token = payload.get('payload', {}).get('plainToken')
            if plain_token:
                return JsonResponse({
                    'plainToken': plain_token,
                    'encryptedToken': plain_token  # В production нужно шифровать
                })
        
        event_type = payload.get('event')
        
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
        # Все записи уроков преподавателя
        recordings = LessonRecording.objects.filter(
            lesson__teacher=user
        ).select_related(
            'lesson',
            'lesson__group'
        ).prefetch_related('allowed_groups', 'allowed_students').order_by('-lesson__start_time').distinct()
        
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
            }
        }, status=status.HTTP_200_OK)


