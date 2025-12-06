"""
ViewSet'ы для API системы посещений, рейтинга и индивидуальных учеников.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Prefetch, Q, Max
from django.utils import timezone

from accounts.models import (
    AttendanceRecord, 
    UserRating, 
    IndividualStudent,
    CustomUser
)
from accounts.attendance_service import AttendanceService, RatingService
from accounts.attendance_serializers import (
    AttendanceRecordSerializer,
    UserRatingSerializer,
    IndividualStudentSerializer,
    AttendanceLogSerializer,
    GroupRatingSerializer,
    StudentCardSerializer,
    GroupReportSerializer,
)
from schedule.models import Lesson, Group


class AttendanceRecordViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления записями посещений.
    
    Endpoints:
    - GET /api/attendance-records/ - список всех
    - POST /api/attendance-records/ - создать
    - GET /api/attendance-records/{id}/ - получить
    - PUT /api/attendance-records/{id}/ - обновить
    - DELETE /api/attendance-records/{id}/ - удалить
    - POST /api/attendance-records/auto_record/ - автоматически записать
    - POST /api/attendance-records/manual_record/ - ручно записать
    - GET /api/attendance-records/group_log/ - журнал посещений группы
    """
    
    queryset = AttendanceRecord.objects.all().select_related(
        'lesson', 'student', 'recorded_by'
    )
    serializer_class = AttendanceRecordSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Фильтровать по текущему пользователю"""
        user = self.request.user
        
        if user.role == 'teacher':
            # Учитель видит посещения своих учеников в своих группах
            return self.queryset.filter(
                lesson__teacher=user
            )
        elif user.role == 'student':
            # Ученик видит только свои посещения
            return self.queryset.filter(student=user)
        else:
            # Админ видит все
            return self.queryset
    
    @action(detail=False, methods=['post'])
    def auto_record(self, request):
        """
        Автоматически записать посещение при подключении к Zoom.
        
        POST /api/attendance-records/auto_record/
        {
            "lesson_id": 1,
            "student_id": 5,
            "is_joined": true
        }
        """
        lesson_id = request.data.get('lesson_id')
        student_id = request.data.get('student_id')
        is_joined = request.data.get('is_joined', True)
        
        if not lesson_id or not student_id:
            return Response(
                {'error': 'lesson_id и student_id обязательны'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            record = AttendanceService.auto_record_attendance(
                lesson_id=lesson_id,
                student_id=student_id,
                is_joined=is_joined
            )
            return Response(
                AttendanceRecordSerializer(record).data,
                status=status.HTTP_201_CREATED
            )
        except Lesson.DoesNotExist:
            return Response(
                {'error': f'Занятие с ID {lesson_id} не найдено'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    def manual_record(self, request):
        """
        Ручно записать посещение (для учителя).
        
        POST /api/attendance-records/manual_record/
        {
            "lesson_id": 1,
            "student_id": 5,
            "status": "attended"  # или "absent", "watched_recording"
        }
        """
        lesson_id = request.data.get('lesson_id')
        student_id = request.data.get('student_id')
        status_value = request.data.get('status')
        
        if not all([lesson_id, student_id, status_value]):
            return Response(
                {'error': 'lesson_id, student_id и status обязательны'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверить, что пользователь - учитель и это его группа
        try:
            lesson = Lesson.objects.get(id=lesson_id)
            if lesson.teacher != request.user:
                return Response(
                    {'error': 'Вы можете записывать посещения только в своих группах'},
                    status=status.HTTP_403_FORBIDDEN
                )
        except Lesson.DoesNotExist:
            return Response(
                {'error': f'Занятие с ID {lesson_id} не найдено'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            record = AttendanceService.manual_record_attendance(
                lesson_id=lesson_id,
                student_id=student_id,
                status=status_value,
                teacher_id=request.user.id
            )
            return Response(
                AttendanceRecordSerializer(record).data,
                status=status.HTTP_200_OK
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    def record_watched_recording(self, request):
        """
        Записать просмотр видеозаписи занятия.
        
        POST /api/attendance-records/record_watched_recording/
        {
            "lesson_id": 1,
            "student_id": 5
        }
        """
        lesson_id = request.data.get('lesson_id')
        student_id = request.data.get('student_id')
        
        if not lesson_id or not student_id:
            return Response(
                {'error': 'lesson_id и student_id обязательны'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            record = AttendanceService.record_watched_recording(
                lesson_id=lesson_id,
                student_id=student_id
            )
            return Response(
                AttendanceRecordSerializer(record).data,
                status=status.HTTP_200_OK
            )
        except Lesson.DoesNotExist:
            return Response(
                {'error': f'Занятие с ID {lesson_id} не найдено'},
                status=status.HTTP_404_NOT_FOUND
            )


class UserRatingViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для просмотра рейтинга учеников.
    
    Endpoints:
    - GET /api/ratings/ - список всех
    - GET /api/ratings/{id}/ - получить
    """
    
    queryset = UserRating.objects.all().select_related(
        'user', 'group'
    ).order_by('-total_points')
    serializer_class = UserRatingSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Фильтровать по текущему пользователю"""
        user = self.request.user
        
        if user.role == 'teacher':
            # Учитель видит рейтинги своих групп
            group_ids = Group.objects.filter(teacher=user).values_list('id', flat=True)
            return self.queryset.filter(group_id__in=group_ids)
        elif user.role == 'student':
            # Ученик видит только свои рейтинги
            return self.queryset.filter(user=user)
        else:
            # Админ видит все
            return self.queryset


class GroupAttendanceLogViewSet(viewsets.ViewSet):
    """
    ViewSet для журнала посещений группы.
    
    Endpoints:
    - GET /api/groups/{group_id}/attendance-log/ - журнал посещений
    - POST /api/groups/{group_id}/attendance-log/update/ - обновить запись
    """
    
    permission_classes = [IsAuthenticated]
    
    def list(self, request, group_id=None):
        """GET /api/groups/{group_id}/attendance-log/"""
        
        # Проверить доступ
        try:
            group = Group.objects.get(id=group_id)
            if request.user.role == 'teacher' and group.teacher != request.user:
                return Response(
                    {'error': 'Вы не имеете доступа к этой группе'},
                    status=status.HTTP_403_FORBIDDEN
                )
        except Group.DoesNotExist:
            return Response(
                {'error': f'Группа с ID {group_id} не найдена'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        lessons = list(
            Lesson.objects.filter(group=group)
            .only('id', 'title', 'start_time', 'end_time')
            .order_by('start_time')
        )
        students = list(
            group.students.all()
            .only('id', 'first_name', 'last_name', 'email')
            .order_by('last_name', 'first_name')
        )

        lessons_data = [
            {
                'id': lesson.id,
                'title': lesson.title,
                'start_time': lesson.start_time,
                'end_time': lesson.end_time,
            }
            for lesson in lessons
        ]

        students_data = [
            {
                'id': student.id,
                'name': student.get_full_name() or student.email,
                'email': student.email,
            }
            for student in students
        ]

        attendance_records = AttendanceRecord.objects.filter(lesson__group=group).only(
            'lesson_id', 'student_id', 'status', 'auto_recorded', 'updated_at'
        )
        records_map = {}
        attendance_counters = {student['id']: 0 for student in students_data}
        watched_total = 0
        absences_total = 0

        for record in attendance_records:
            key = f"{record.student_id}_{record.lesson_id}"
            records_map[key] = {
                'status': record.status,
                'auto_recorded': record.auto_recorded,
            }

            if record.status == AttendanceRecord.STATUS_ATTENDED:
                attendance_counters[record.student_id] = attendance_counters.get(record.student_id, 0) + 1
            elif record.status == AttendanceRecord.STATUS_WATCHED_RECORDING:
                watched_total += 1
            elif record.status == AttendanceRecord.STATUS_ABSENT:
                absences_total += 1

        lessons_count = len(lessons_data)
        students_count = len(students_data)
        avg_attendance_percent = 0
        if lessons_count and students_count:
            total_percent = sum(
                (attendance_counters.get(student['id'], 0) / lessons_count) * 100
                for student in students_data
            )
            avg_attendance_percent = round(total_percent / students_count)

        last_updated = attendance_records.aggregate(last=Max('updated_at'))['last']
        meta = {
            'records_count': len(records_map),
            'updated_at': last_updated,
            'stats': {
                'avg_attendance_percent': avg_attendance_percent,
                'watched_total': watched_total,
                'absences_total': absences_total,
                'lessons_count': lessons_count,
                'students_count': students_count,
            }
        }

        serializer = AttendanceLogSerializer(
            {},
            context={
                'group_id': group_id,
                'lessons_data': lessons_data,
                'students_data': students_data,
                'records_data': records_map,
                'meta': meta,
            }
        )
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def update(self, request, group_id=None):
        """
        POST /api/groups/{group_id}/attendance-log/update/
        {
            "lesson_id": 1,
            "student_id": 5,
            "status": "attended" | "absent" | "watched_recording" | null (очистить)
        }
        """
        lesson_id = request.data.get('lesson_id')
        student_id = request.data.get('student_id')
        status_value = request.data.get('status')

        if lesson_id is None or student_id is None:
            return Response(
                {'error': 'lesson_id и student_id обязательны'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            lesson = Lesson.objects.get(id=lesson_id, group_id=group_id)
            if lesson.teacher != request.user:
                return Response(
                    {'error': 'Вы не имеете прав на обновление'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Очистка статуса
            if status_value in (None, ''):
                AttendanceRecord.objects.filter(
                    lesson=lesson,
                    student_id=student_id
                ).delete()
                RatingService.recalculate_student_rating(
                    student_id=student_id,
                    group_id=lesson.group_id
                )
                return Response({'status': 'cleared'}, status=status.HTTP_200_OK)

            if status_value not in [
                AttendanceRecord.STATUS_ATTENDED,
                AttendanceRecord.STATUS_ABSENT,
                AttendanceRecord.STATUS_WATCHED_RECORDING,
            ]:
                return Response(
                    {'error': 'Недопустимый статус посещения'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            record = AttendanceService.manual_record_attendance(
                lesson_id=lesson_id,
                student_id=student_id,
                status=status_value,
                teacher_id=request.user.id
            )

            return Response(
                AttendanceRecordSerializer(record).data,
                status=status.HTTP_200_OK
            )
        except Lesson.DoesNotExist:
            return Response(
                {'error': 'Занятие не найдено'},
                status=status.HTTP_404_NOT_FOUND
            )


class GroupRatingViewSet(viewsets.ViewSet):
    """
    ViewSet для рейтинга группы.
    
    Endpoints:
    - GET /api/groups/{group_id}/rating/ - рейтинг группы
    """
    
    permission_classes = [IsAuthenticated]
    
    def list(self, request, group_id=None):
        """GET /api/groups/{group_id}/rating/"""
        
        # Проверить доступ
        try:
            group = Group.objects.get(id=group_id)
            if request.user.role == 'teacher' and group.teacher != request.user:
                return Response(
                    {'error': 'Вы не имеете доступа к этой группе'},
                    status=status.HTTP_403_FORBIDDEN
                )
        except Group.DoesNotExist:
            return Response(
                {'error': f'Группа с ID {group_id} не найдена'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = GroupRatingSerializer(
            {},
            context={'group_id': group_id}
        )
        return Response(serializer.data)


class StudentCardViewSet(viewsets.ViewSet):
    """
    ViewSet для карточки ученика.
    
    Endpoints:
    - GET /api/students/{student_id}/card/ - карточка ученика
    - GET /api/students/individual/ - список индивидуальных учеников
    """
    
    permission_classes = [IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        """Primary entrypoint for detail routes (aliases to card)."""
        student_id = kwargs.pop('pk', None) or kwargs.get('student_id')
        return self.card(request, pk=student_id, **kwargs)

    def _build_card_response(self, student, group_id=None, teacher_notes=None):
        notes = teacher_notes
        if notes is None:
            try:
                notes = student.individual_student_profile.teacher_notes
            except IndividualStudent.DoesNotExist:
                notes = ''

        card_data = {
            'student_id': student.id,
            'name': student.get_full_name(),
            'email': student.email,
            'teacher_notes': notes,
        }

        serializer = StudentCardSerializer(
            card_data,
            context={'group_id': group_id}
        )
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def card(self, request, pk=None, **kwargs):
        """GET /api/students/{student_id}/card/ (also used by retrieve)."""

        student_id = pk or kwargs.get('student_id') or kwargs.get('pk')
        if not student_id:
            return Response(
                {'error': 'student_id обязателен'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            student = CustomUser.objects.get(id=student_id, role='student')
        except CustomUser.DoesNotExist:
            return Response(
                {'error': f'Ученик с ID {student_id} не найден'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Проверить доступ (учитель может видеть только своих учеников)
        if request.user.role == 'teacher':
            if not student.enrolled_groups.filter(teacher=request.user).exists():
                # Может быть индивидуальный ученик
                try:
                    if student.individual_student_profile.teacher != request.user:
                        return Response(
                            {'error': 'Вы не имеете доступа к этому ученику'},
                            status=status.HTTP_403_FORBIDDEN
                        )
                except IndividualStudent.DoesNotExist:
                    return Response(
                        {'error': 'Вы не имеете доступа к этому ученику'},
                        status=status.HTTP_403_FORBIDDEN
                    )

        group_id = request.query_params.get('group_id')
        return self._build_card_response(student, group_id=group_id)

    @action(detail=True, methods=['get'], url_path='individual-card')
    def individual_card(self, request, pk=None, **kwargs):
        """GET /api/students/{student_id}/individual-card/"""

        student_id = pk or kwargs.get('student_id') or kwargs.get('pk')
        if not student_id:
            return Response(
                {'error': 'student_id обязателен'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            ind_student = IndividualStudent.objects.select_related('user', 'teacher').get(user_id=student_id)
        except IndividualStudent.DoesNotExist:
            return Response(
                {'error': f'Индивидуальный ученик с ID {student_id} не найден'},
                status=status.HTTP_404_NOT_FOUND
            )

        if request.user.role == 'teacher' and ind_student.teacher != request.user:
            return Response(
                {'error': 'Вы не имеете доступа к этому ученику'},
                status=status.HTTP_403_FORBIDDEN
            )

        return self._build_card_response(
            ind_student.user,
            group_id=None,
            teacher_notes=ind_student.teacher_notes
        )
    
    @action(detail=False, methods=['get'])
    def individual(self, request):
        """GET /api/students/individual/ - список индивидуальных учеников"""
        
        if request.user.role == 'teacher':
            # Получить индивидуальных учеников этого учителя
            ind_students = IndividualStudent.objects.filter(
                teacher=request.user
            ).select_related('user')
        else:
            # Админ видит всех индивидуальных учеников
            ind_students = IndividualStudent.objects.all().select_related('user')
        
        serializer = IndividualStudentSerializer(ind_students, many=True)
        return Response(serializer.data)


class IndividualStudentViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления индивидуальными учениками.
    
    Endpoints:
    - GET /api/individual-students/ - список
    - POST /api/individual-students/ - создать
    - GET /api/individual-students/{id}/ - получить
    - PUT /api/individual-students/{id}/ - обновить
    - PATCH /api/individual-students/{id}/ - частичное обновление
    - DELETE /api/individual-students/{id}/ - удалить
    """
    
    queryset = IndividualStudent.objects.all().select_related(
        'user', 'teacher'
    )
    serializer_class = IndividualStudentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Фильтровать по текущему пользователю"""
        user = self.request.user
        
        if user.role == 'teacher':
            return self.queryset.filter(teacher=user)
        elif user.role == 'student':
            return self.queryset.filter(user=user)
        else:
            return self.queryset
    
    @action(detail=True, methods=['patch'])
    def update_notes(self, request, pk=None):
        """
        PATCH /api/individual-students/{id}/update_notes/
        {
            "teacher_notes": "Хороший прогресс..."
        }
        """
        try:
            ind_student = self.get_object()
            
            # Проверить, что это учитель студента
            if request.user.role == 'teacher' and ind_student.teacher != request.user:
                return Response(
                    {'error': 'Вы не имеете прав на изменение'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            ind_student.teacher_notes = request.data.get(
                'teacher_notes',
                ind_student.teacher_notes
            )
            ind_student.save()
            
            return Response(
                IndividualStudentSerializer(ind_student).data,
                status=status.HTTP_200_OK
            )
        except IndividualStudent.DoesNotExist:
            return Response(
                {'error': 'Не найдено'},
                status=status.HTTP_404_NOT_FOUND
            )


class GroupReportViewSet(viewsets.ViewSet):
    """
    ViewSet для отчета группы.
    
    Endpoints:
    - GET /api/groups/{group_id}/report/ - отчет группы
    """
    
    permission_classes = [IsAuthenticated]
    
    def list(self, request, group_id=None):
        """GET /api/groups/{group_id}/report/"""
        
        # Проверить доступ
        try:
            group = Group.objects.get(id=group_id)
            if request.user.role == 'teacher' and group.teacher != request.user:
                return Response(
                    {'error': 'Вы не имеете доступа к этой группе'},
                    status=status.HTTP_403_FORBIDDEN
                )
        except Group.DoesNotExist:
            return Response(
                {'error': f'Группа с ID {group_id} не найдена'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = GroupReportSerializer(
            {},
            context={'group_id': group_id}
        )
        data = serializer.get_representation({})
        return Response(data)
