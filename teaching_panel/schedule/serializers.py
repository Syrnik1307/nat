from rest_framework import serializers
from django.utils import timezone
from .models import Group, Lesson, Attendance, ZoomAccount, RecurringLesson, LessonRecording, TeacherStorageQuota
from accounts.models import CustomUser


class StudentSerializer(serializers.ModelSerializer):
    """Сериализатор для студентов в группе"""
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'last_name']


class TeacherSerializer(serializers.ModelSerializer):
    """Сериализатор для преподавателя"""
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'last_name']


class GroupSerializer(serializers.ModelSerializer):
    """Сериализатор для группы"""
    teacher = TeacherSerializer(read_only=True)
    teacher_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.filter(role='teacher'),
        source='teacher',
        write_only=True
    )
    students = StudentSerializer(many=True, read_only=True)
    student_ids = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.filter(role='student'),
        source='students',
        many=True,
        write_only=True,
        required=False
    )
    student_count = serializers.IntegerField(read_only=True)
    invite_code = serializers.CharField(read_only=True)
    
    class Meta:
        model = Group
        fields = [
            'id', 'name', 'description', 
            'teacher', 'teacher_id',
            'students', 'student_ids', 'student_count',
            'invite_code',
            'created_at', 'updated_at'
        ]


class LessonSerializer(serializers.ModelSerializer):
    """Сериализатор для занятия"""
    group_name = serializers.CharField(source='group.name', read_only=True)
    teacher_name = serializers.CharField(source='teacher.get_full_name', read_only=True)
    duration_minutes = serializers.IntegerField(source='duration', read_only=True)
    # teacher делаем read_only – будет выставляться автоматически из request.user
    teacher = serializers.PrimaryKeyRelatedField(read_only=True)
    
    class Meta:
        model = Lesson
        fields = [
            'id', 'title', 'group', 'group_name',
            'teacher', 'teacher_name',
            'start_time', 'end_time', 'duration_minutes',
            'topics', 'location',
            'zoom_meeting_id', 'zoom_start_url', 'zoom_join_url', 'zoom_password',
            'notes', 'created_at', 'updated_at'
        ]

    def validate(self, attrs):
        start = attrs.get('start_time') or getattr(self.instance, 'start_time', None)
        end = attrs.get('end_time') or getattr(self.instance, 'end_time', None)
        # Приводим в aware если пришли naive
        if start and timezone.is_naive(start):
            start = timezone.make_aware(start, timezone.get_current_timezone())
            attrs['start_time'] = start
        if end and timezone.is_naive(end):
            end = timezone.make_aware(end, timezone.get_current_timezone())
            attrs['end_time'] = end
        if start and end and end <= start:
            raise serializers.ValidationError({'end_time': 'end_time должно быть позже start_time'})

        # Проверка пересечений по преподавателю
        teacher = attrs.get('teacher') or getattr(self.instance, 'teacher', None)
        group = attrs.get('group') or getattr(self.instance, 'group', None)
        if start and end and teacher:
            qs = Lesson.objects.filter(teacher=teacher, start_time__lt=end, end_time__gt=start)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError('У преподавателя уже есть урок, пересекающийся по времени.')

        # Проверка пересечения по группе (не допускать два урока одной группы одновременно)
        if start and end and group:
            gqs = Lesson.objects.filter(group=group, start_time__lt=end, end_time__gt=start)
            if self.instance:
                gqs = gqs.exclude(pk=self.instance.pk)
            if gqs.exists():
                raise serializers.ValidationError('У группы уже есть пересекающийся урок.')

        return attrs

    def create(self, validated_data):
        # Автоматически проставляем преподавателя из контекста
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError('Требуется аутентификация')
        user = request.user
        if getattr(user, 'role', None) != 'teacher':
            raise serializers.ValidationError('Только преподаватель может создавать занятия')
        # Проверяем что группа принадлежит этому преподавателю
        group = validated_data.get('group')
        if group.teacher_id != user.id:
            raise serializers.ValidationError('Вы не являетесь преподавателем этой группы')
        validated_data['teacher'] = user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """
        Обновление урока с автоматическим пересозданием Zoom встречи при изменении времени
        """
        from core.zoom_service import delete_zoom_meeting, create_zoom_meeting, ZoomAPIError
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Запрещаем смену преподавателя через API
        if 'teacher' in validated_data:
            validated_data.pop('teacher')
        
        # Проверяем изменение времени для пересоздания Zoom встречи
        start_changed = 'start_time' in validated_data and validated_data['start_time'] != instance.start_time
        end_changed = 'end_time' in validated_data and validated_data['end_time'] != instance.end_time
        time_changed = start_changed or end_changed
        
        # Сохраняем старые данные Zoom
        old_zoom_meeting_id = instance.zoom_meeting_id
        old_zoom_account = instance.zoom_account
        
        # Обновляем урок
        updated_lesson = super().update(instance, validated_data)
        
        # Пересоздаём Zoom встречу, если время изменилось и встреча была создана
        if time_changed and old_zoom_meeting_id and old_zoom_account:
            logger.info(f"Lesson {updated_lesson.id}: time changed, recreating Zoom meeting")
            
            try:
                # Удаляем старую встречу
                success = delete_zoom_meeting(
                    old_zoom_account.api_key,
                    old_zoom_account.api_secret,
                    old_zoom_meeting_id
                )
                if success:
                    logger.info(f"Deleted old Zoom meeting {old_zoom_meeting_id}")
                else:
                    logger.warning(f"Failed to delete old Zoom meeting {old_zoom_meeting_id}")
                
                # Создаём новую встречу
                topic = updated_lesson.title or f"Урок {updated_lesson.group.name}"
                meeting_id, join_url = create_zoom_meeting(
                    old_zoom_account.api_key,
                    old_zoom_account.api_secret,
                    topic=topic,
                    start_time=updated_lesson.start_time,
                    duration=int(updated_lesson.duration().total_seconds() // 60)
                )
                
                # Обновляем данные встречи
                updated_lesson.zoom_meeting_id = meeting_id
                updated_lesson.zoom_join_url = join_url
                updated_lesson.save(update_fields=['zoom_meeting_id', 'zoom_join_url'])
                
                logger.info(f"Created new Zoom meeting {meeting_id} for lesson {updated_lesson.id}")
                
            except ZoomAPIError as e:
                logger.error(f"Failed to recreate Zoom meeting for lesson {updated_lesson.id}: {e}")
                # Продолжаем выполнение - урок обновлён, но встреча не пересоздана
                # В production можно отправить уведомление администратору
        
        return updated_lesson

    def to_representation(self, instance):
        data = super().to_representation(instance)
        user = self.context.get('request').user if self.context.get('request') else None
        # Скрываем zoom_start_url для студентов
        if not (user and user.is_authenticated and getattr(user, 'role', None) == 'teacher'):
            data.pop('zoom_start_url', None)
        return data


class LessonCalendarSerializer(serializers.ModelSerializer):
    """Упрощенный сериализатор для календаря (FullCalendar.js)"""
    title = serializers.SerializerMethodField()
    start = serializers.DateTimeField(source='start_time')
    end = serializers.DateTimeField(source='end_time')
    color = serializers.SerializerMethodField()
    extendedProps = serializers.SerializerMethodField()
    
    class Meta:
        model = Lesson
        fields = ['id', 'title', 'start', 'end', 'color', 'extendedProps']
    
    def get_title(self, obj):
        """Формат: Название - Группа"""
        return f"{obj.title} - {obj.group.name}"
    
    def get_color(self, obj):
        """Цвет в зависимости от группы (можно настроить)"""
        colors = ['#3788d8', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6']
        return colors[obj.group.id % len(colors)]
    
    def get_extendedProps(self, obj):
        """Дополнительные данные для событий"""
        return {
            'groupId': obj.group.id,
            'groupName': obj.group.name,
            'teacherId': obj.teacher.id,
            'teacherName': obj.teacher.get_full_name(),
            'location': obj.location,
            'topics': obj.topics,
            'zoomUrl': obj.zoom_join_url,
        }


class AttendanceSerializer(serializers.ModelSerializer):
    """Сериализатор для посещаемости"""
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    lesson_title = serializers.CharField(source='lesson.title', read_only=True)
    
    class Meta:
        model = Attendance
        fields = [
            'id', 'lesson', 'lesson_title',
            'student', 'student_name',
            'status', 'notes', 'marked_at'
        ]


class LessonDetailSerializer(serializers.ModelSerializer):
    """Детальный сериализатор занятия с посещаемостью"""
    group = GroupSerializer(read_only=True)
    teacher = TeacherSerializer(read_only=True)
    attendances = AttendanceSerializer(many=True, read_only=True)
    recordings = serializers.SerializerMethodField()
    duration_minutes = serializers.IntegerField(source='duration', read_only=True)
    
    class Meta:
        model = Lesson
        fields = [
            'id', 'title', 'group', 'teacher',
            'start_time', 'end_time', 'duration_minutes',
            'topics', 'location',
            'zoom_meeting_id', 'zoom_start_url', 'zoom_join_url', 'zoom_password',
            'notes', 'attendances', 'recordings',
            'created_at', 'updated_at'
        ]

    def get_recordings(self, obj):
        return [
            {
                'id': rec.id,
                'url': rec.url,
                'created_at': rec.created_at,
            }
            for rec in obj.recordings.all()
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        user = self.context.get('request').user if self.context.get('request') else None
        if not (user and user.is_authenticated and getattr(user, 'role', None) == 'teacher'):
            data.pop('zoom_start_url', None)
        return data



class ZoomAccountSerializer(serializers.ModelSerializer):
    """Сериализатор для Zoom аккаунтов"""
    current_lesson_title = serializers.CharField(source='current_lesson.title', read_only=True)
    current_lesson_id = serializers.IntegerField(source='current_lesson.id', read_only=True)
    
    class Meta:
        model = ZoomAccount
        fields = [
            'id', 'name', 'zoom_user_id', 'is_busy',
            'current_lesson_id', 'current_lesson_title',
            'created_at', 'updated_at'
        ]
        # Не показываем api_key и api_secret в API
        read_only_fields = ['is_busy', 'current_lesson_id', 'current_lesson_title']


class RecurringLessonSerializer(serializers.ModelSerializer):
    """Сериализатор для регулярных уроков"""
    teacher = TeacherSerializer(read_only=True)
    group = GroupSerializer(read_only=True)
    # Для создания/редактирования: передаем идентификатор группы
    group_id = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(), source='group', write_only=True, required=True
    )
    day_of_week_display = serializers.SerializerMethodField()
    week_type_display = serializers.CharField(source='get_week_type_display', read_only=True)
    
    def get_day_of_week_display(self, obj):
        days = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
        return days[obj.day_of_week] if 0 <= obj.day_of_week < 7 else 'Unknown'
    
    class Meta:
        model = RecurringLesson
        fields = [
            'id', 'title', 'teacher', 'group', 'group_id',
            'day_of_week', 'day_of_week_display',
            'week_type', 'week_type_display',
            'start_time', 'end_time',
            'start_date', 'end_date',
            'topics', 'location'
        ]

    def validate(self, attrs):
        start_time = attrs.get('start_time') or getattr(self.instance, 'start_time', None)
        end_time = attrs.get('end_time') or getattr(self.instance, 'end_time', None)
        if start_time and end_time and end_time <= start_time:
            raise serializers.ValidationError({'end_time': 'end_time должно быть позже start_time'})
        start_date = attrs.get('start_date') or getattr(self.instance, 'start_date', None)
        end_date = attrs.get('end_date') or getattr(self.instance, 'end_date', None)
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({'end_date': 'end_date не может быть раньше start_date'})
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError('Требуется аутентификация')
        user = request.user
        if getattr(user, 'role', None) != 'teacher':
            raise serializers.ValidationError('Только преподаватель может создавать регулярные занятия')
        group = validated_data.get('group')
        if group.teacher_id != user.id:
            raise serializers.ValidationError('Вы не являетесь преподавателем этой группы')
        validated_data['teacher'] = user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # teacher нельзя менять
        if 'teacher' in validated_data:
            validated_data.pop('teacher')
        # group менять можно только если она принадлежит тому же преподавателю
        if 'group' in validated_data:
            new_group = validated_data['group']
            request = self.context.get('request')
            user = request.user if request else None
            if not user or getattr(user, 'role', None) != 'teacher' or new_group.teacher_id != user.id:
                raise serializers.ValidationError('Нельзя установить группу: вы не её преподаватель')
        return super().update(instance, validated_data)


class LessonRecordingSerializer(serializers.ModelSerializer):
    """Сериализатор для записей уроков (без несуществующих полей)"""
    lesson_info = serializers.SerializerMethodField()
    file_size_mb = serializers.SerializerMethodField()
    duration_display = serializers.SerializerMethodField()
    available_days_left = serializers.SerializerMethodField()
    access_groups = serializers.SerializerMethodField()
    access_students = serializers.SerializerMethodField()

    def get_lesson_info(self, obj):
        if not obj.lesson:
            return None
        lesson = obj.lesson
        return {
            'id': lesson.id,
            'title': lesson.title,
            # Frontend expects subject/group_name/group_id fields for filtering
            'subject': lesson.title,
            'group': lesson.group.name if lesson.group else None,
            'group_name': lesson.group.name if lesson.group else None,
            'group_id': lesson.group.id if lesson.group else None,
            'teacher': {
                'id': lesson.teacher.id,
                'name': f"{lesson.teacher.first_name} {lesson.teacher.last_name}".strip() or lesson.teacher.email
            } if lesson.teacher else None,
            'start_time': lesson.start_time,
            'end_time': lesson.end_time,
            'date': lesson.start_time.strftime('%Y-%m-%d') if lesson.start_time else None,
        }

    def get_file_size_mb(self, obj):
        if obj.file_size:
            return round(obj.file_size / (1024 * 1024), 2)
        return None

    def get_duration_display(self, obj):
        if obj.lesson and obj.lesson.start_time and obj.lesson.end_time:
            duration = obj.lesson.end_time - obj.lesson.start_time
            return int(duration.total_seconds() / 60)
        return None

    def get_available_days_left(self, obj):
        if obj.available_until:
            now = timezone.now()
            if obj.available_until > now:
                return (obj.available_until - now).days
            return 0
        return None

    def get_access_groups(self, obj):
        groups = getattr(obj, 'allowed_groups', None)
        if not groups:
            return []
        return [
            {
                'id': group.id,
                'name': group.name
            }
            for group in groups.all()
        ]

    def get_access_students(self, obj):
        students = getattr(obj, 'allowed_students', None)
        if not students:
            return []
        return [
            {
                'id': student.id,
                'name': student.get_full_name() or student.email,
                'email': student.email
            }
            for student in students.all()
        ]

    class Meta:
        model = LessonRecording
        fields = [
            'id', 'lesson', 'lesson_info',
            'zoom_recording_id',
            'file_size', 'file_size_mb',
            'duration_display',
            'play_url', 'download_url', 'thumbnail_url',
            'storage_provider', 'gdrive_file_id',
            'status', 'views_count',
            'visibility', 'access_groups', 'access_students',
            'available_until', 'available_days_left',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'zoom_recording_id', 'file_size',
            'play_url', 'download_url', 'thumbnail_url',
            'storage_provider', 'gdrive_file_id',
            'status', 'views_count', 'visibility',
            'created_at', 'updated_at'
        ]


class TeacherStorageQuotaSerializer(serializers.ModelSerializer):
    """Сериализатор для квот хранилища преподавателей"""
    
    teacher_info = serializers.SerializerMethodField()
    total_gb = serializers.SerializerMethodField()
    used_gb = serializers.SerializerMethodField()
    available_gb = serializers.SerializerMethodField()
    usage_percent = serializers.SerializerMethodField()
    
    def get_teacher_info(self, obj):
        """Информация о преподавателе"""
        return {
            'id': obj.teacher.id,
            'email': obj.teacher.email,
            'name': obj.teacher.get_full_name() or obj.teacher.email,
            'first_name': obj.teacher.first_name,
            'last_name': obj.teacher.last_name
        }
    
    def get_total_gb(self, obj):
        """Общая квота в ГБ"""
        return round(obj.total_gb, 2)
    
    def get_used_gb(self, obj):
        """Использовано ГБ"""
        return round(obj.used_gb, 2)
    
    def get_available_gb(self, obj):
        """Доступно ГБ"""
        return round(obj.available_gb, 2)
    
    def get_usage_percent(self, obj):
        """Процент использования"""
        return round(obj.usage_percent, 1)
    
    class Meta:
        model = TeacherStorageQuota
        fields = [
            'id', 'teacher', 'teacher_info',
            'total_quota_bytes', 'total_gb',
            'used_bytes', 'used_gb',
            'available_gb', 'usage_percent',
            'recordings_count', 'purchased_gb',
            'warning_sent', 'quota_exceeded',
            'last_warning_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'used_bytes', 'recordings_count',
            'warning_sent', 'quota_exceeded', 'last_warning_at',
            'created_at', 'updated_at'
        ]
