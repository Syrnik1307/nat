"""
ViewSet'ы для API системы посещений, рейтинга и индивидуальных учеников.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Prefetch, Q
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
        
        serializer = AttendanceLogSerializer(
            {},
            context={'group_id': group_id}
        )
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def update(self, request, group_id=None):
        """
        POST /api/groups/{group_id}/attendance-log/update/
        {
            "lesson_id": 1,
            "student_id": 5,
            "status": "attended"
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
        
        try:
            lesson = Lesson.objects.get(id=lesson_id, group_id=group_id)
            if lesson.teacher != request.user:
                return Response(
                    {'error': 'Вы не имеете прав на обновление'},
                    status=status.HTTP_403_FORBIDDEN
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
    
    @action(detail=True, methods=['get'])
    def card(self, request, pk=None):
        """GET /api/students/{student_id}/card/"""
        
        try:
            student = CustomUser.objects.get(id=pk, role='student')
        except CustomUser.DoesNotExist:
            return Response(
                {'error': f'Ученик с ID {pk} не найден'},
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
        
        card_data = {
            'student_id': student.id,
            'name': student.get_full_name(),
            'email': student.email,
        }
        
        # Добавить замечания учителя если это индивидуальный ученик
        try:
            ind_student = student.individual_student_profile
            card_data['teacher_notes'] = ind_student.teacher_notes
        except IndividualStudent.DoesNotExist:
            card_data['teacher_notes'] = ''
        
        serializer = StudentCardSerializer(
            card_data,
            context={'group_id': group_id}
        )
        return Response(serializer.data)
    
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
