from django.contrib.auth import get_user_model
from django.db.models import Q, Count
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
import logging

from schedule.models import Lesson, Group as ScheduleGroup

from .serializers import UserProfileSerializer, SystemSettingsSerializer
from .models import StatusBarMessage, SystemSettings

User = get_user_model()
logger = logging.getLogger(__name__)


def _tenant_user_qs(request, base_qs=None):
    """Фильтрует queryset пользователей по текущему тенанту.
    Если тенант есть — возвращает только участников этого тенанта.
    Если нет — возвращает исходный queryset (backward compat).
    """
    if base_qs is None:
        base_qs = User.objects.all()
    tenant = getattr(request, 'tenant', None)
    if tenant:
        from tenants.models import TenantMembership
        tenant_user_ids = TenantMembership.objects.filter(
            tenant=tenant, is_active=True
        ).values_list('user_id', flat=True)
        return base_qs.filter(id__in=tenant_user_ids)
    return base_qs


class AdminStatsView(APIView):
    """Статистика для админ панели"""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Проверка прав админа
        if request.user.role != 'admin':
            return Response(
                {'error': 'Доступ запрещен'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Подсчет пользователей (только тенанта)
        tenant_users = _tenant_user_qs(request)
        total_users = tenant_users.count()
        teachers = tenant_users.filter(role='teacher').count()
        students = tenant_users.filter(role='student').count()
        
        # Онлайн пользователи (активность за последние 15 минут)
        online_threshold = timezone.now() - timedelta(minutes=15)
        teachers_online = tenant_users.filter(
            role='teacher',
            last_login__gte=online_threshold
        ).count()
        students_online = tenant_users.filter(
            role='student',
            last_login__gte=online_threshold
        ).count()
        
        # Группы (только по учителям тенанта)
        teacher_ids = tenant_users.filter(role='teacher').values_list('id', flat=True)
        groups = ScheduleGroup.objects.filter(teacher_id__in=teacher_ids).count()
        
        # Занятия (только по учителям тенанта)
        lessons = Lesson.objects.filter(teacher_id__in=teacher_ids).count()
        
        # Zoom аккаунты
        from zoom_pool.models import ZoomAccount
        zoom_accounts = ZoomAccount.objects.filter(is_active=True).count()

        now = timezone.now()
        period_specs = [
            ('day', 'За день', 'Последние 24 часа', timedelta(days=1)),
            ('week', 'За неделю', 'Последние 7 дней', timedelta(days=7)),
            ('month', 'За месяц', 'Последние 30 дней', timedelta(days=30)),
            ('half_year', 'За полгода', 'Последние 6 месяцев', timedelta(days=182)),
        ]

        growth_periods = []
        for key, label, range_label, delta in period_specs:
            period_start = now - delta
            teacher_growth = tenant_users.filter(
                role='teacher',
                created_at__gte=period_start
            ).count()
            student_growth = tenant_users.filter(
                role='student',
                created_at__gte=period_start
            ).count()
            lesson_growth = Lesson.objects.filter(
                teacher_id__in=teacher_ids,
                start_time__gte=period_start,
                start_time__lte=now
            ).count()

            growth_periods.append({
                'key': key,
                'label': label,
                'range_label': range_label,
                'teachers': teacher_growth,
                'students': student_growth,
                'lessons': lesson_growth,
                'total_users': teacher_growth + student_growth,
            })
        
        return Response({
            'total_users': total_users,
            'teachers': teachers,
            'students': students,
            'teachers_online': teachers_online,
            'students_online': students_online,
            'groups': groups,
            'lessons': lessons,
            'zoom_accounts': zoom_accounts,
            'growth_periods': growth_periods,
        })


class AdminCreateTeacherView(APIView):
    """Создание нового учителя"""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Проверка прав админа
        if request.user.role != 'admin':
            return Response(
                {'error': 'Доступ запрещен'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Валидация данных
        email = request.data.get('email')
        password = request.data.get('password')
        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name')
        middle_name = request.data.get('middle_name', '')
        phone_number = request.data.get('phone_number', '')
        
        if not email or not password:
            return Response(
                {'error': 'Email и пароль обязательны'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not first_name or not last_name:
            return Response(
                {'error': 'Имя и фамилия обязательны'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверка существующего email
        if User.objects.filter(email=email).exists():
            return Response(
                {'error': 'Пользователь с таким email уже существует'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверка существующего телефона (если указан)
        if phone_number and User.objects.filter(phone_number=phone_number).exists():
            return Response(
                {'error': 'Пользователь с таким телефоном уже существует'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Создание учителя
        try:
            # Создаем пользователя без валидации пароля Django
            teacher = User(
                email=email,
                first_name=first_name,
                last_name=last_name,
                middle_name=middle_name,
                phone_number=phone_number if phone_number else None,  # None если пустой
                role='teacher',
                is_active=True
            )
            teacher.set_password(password)  # Хешируем пароль
            teacher.save()
            
            logger.info(f"Teacher created successfully: {teacher.email} (ID: {teacher.id})")
            
            serializer = UserProfileSerializer(teacher)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            logger.error(f"Failed to create teacher: {error_detail}")
            return Response(
                {'error': str(e), 'detail': error_detail if settings.DEBUG else str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminTeachersListView(APIView):
    """Список всех учителей"""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Проверка прав админа
        if request.user.role != 'admin':
            return Response(
                {'error': 'Доступ запрещен'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        teachers = _tenant_user_qs(request).filter(role='teacher').order_by('last_name', 'first_name')
        
        teachers_data = []
        for teacher in teachers:
            teachers_data.append({
                'id': teacher.id,
                'email': teacher.email,
                'first_name': teacher.first_name,
                'last_name': teacher.last_name,
                'middle_name': teacher.middle_name,
                'phone_number': teacher.phone_number,
                'zoom_account_id': teacher.zoom_account_id,
                'zoom_client_id': teacher.zoom_client_id,
                'zoom_client_secret': teacher.zoom_client_secret,
                'zoom_user_id': teacher.zoom_user_id,
                'has_zoom_config': bool(teacher.zoom_account_id and teacher.zoom_client_id and teacher.zoom_client_secret),
                'created_at': teacher.created_at,
                'last_login': teacher.last_login,
            })
        
        return Response(teachers_data)


class AdminUpdateTeacherZoomView(APIView):
    """Обновление Zoom credentials учителя"""
    
    permission_classes = [IsAuthenticated]
    
    def patch(self, request, teacher_id):
        # Проверка прав админа
        if request.user.role != 'admin':
            return Response(
                {'error': 'Доступ запрещен'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            teacher = _tenant_user_qs(request).get(id=teacher_id, role='teacher')
        except User.DoesNotExist:
            return Response(
                {'error': 'Учитель не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Обновление Zoom credentials
        teacher.zoom_account_id = request.data.get('zoom_account_id', teacher.zoom_account_id)
        teacher.zoom_client_id = request.data.get('zoom_client_id', teacher.zoom_client_id)
        teacher.zoom_client_secret = request.data.get('zoom_client_secret', teacher.zoom_client_secret)
        teacher.zoom_user_id = request.data.get('zoom_user_id', teacher.zoom_user_id)
        teacher.save()
        
        return Response({
            'id': teacher.id,
            'email': teacher.email,
            'first_name': teacher.first_name,
            'last_name': teacher.last_name,
            'zoom_account_id': teacher.zoom_account_id,
            'zoom_client_id': teacher.zoom_client_id,
            'zoom_client_secret': teacher.zoom_client_secret,
            'zoom_user_id': teacher.zoom_user_id,
            'has_zoom_config': bool(teacher.zoom_account_id and teacher.zoom_client_id and teacher.zoom_client_secret),
        })


class AdminDeleteTeacherView(APIView):
    """Удаление учителя"""
    
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, teacher_id):
        # Проверка прав админа
        if request.user.role != 'admin':
            return Response(
                {'error': 'Доступ запрещен'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            teacher = _tenant_user_qs(request).get(id=teacher_id, role='teacher')
        except User.DoesNotExist:
            return Response(
                {'error': 'Учитель не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        teacher_name = f"{teacher.first_name} {teacher.last_name}"
        teacher.delete()
        
        logger.info(f"Teacher deleted: {teacher_name} (ID: {teacher_id}) by admin {request.user.email}")
        
        return Response({
            'message': f'Учитель {teacher_name} успешно удален'
        }, status=status.HTTP_200_OK)


class AdminStudentsListView(APIView):
    """Список всех учеников"""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Проверка прав админа
        if request.user.role != 'admin':
            return Response(
                {'error': 'Доступ запрещен'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        students = _tenant_user_qs(request).filter(role='student').order_by('last_name', 'first_name')
        
        students_data = []
        for student in students:
            students_data.append({
                'id': student.id,
                'email': student.email,
                'first_name': student.first_name,
                'last_name': student.last_name,
                'middle_name': student.middle_name,
                'created_at': student.created_at,
                'last_login': student.last_login,
            })
        
        return Response(students_data)


class AdminUpdateStudentView(APIView):
    """Обновление данных ученика"""
    
    permission_classes = [IsAuthenticated]
    
    def patch(self, request, student_id):
        # Проверка прав админа
        if request.user.role != 'admin':
            return Response(
                {'error': 'Доступ запрещен'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            student = _tenant_user_qs(request).get(id=student_id, role='student')
        except User.DoesNotExist:
            return Response(
                {'error': 'Ученик не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Обновление данных
        student.first_name = request.data.get('first_name', student.first_name)
        student.last_name = request.data.get('last_name', student.last_name)
        student.middle_name = request.data.get('middle_name', student.middle_name)
        student.save()
        
        return Response({
            'id': student.id,
            'email': student.email,
            'first_name': student.first_name,
            'last_name': student.last_name,
            'middle_name': student.middle_name,
        })


class AdminDeleteStudentView(APIView):
    """Удаление ученика"""
    
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, student_id):
        # Проверка прав админа
        if request.user.role != 'admin':
            return Response(
                {'error': 'Доступ запрещен'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            student = _tenant_user_qs(request).get(id=student_id, role='student')
        except User.DoesNotExist:
            return Response(
                {'error': 'Ученик не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        student_name = f"{student.first_name} {student.last_name}"
        student.delete()
        
        logger.info(f"Student deleted: {student_name} (ID: {student_id}) by admin {request.user.email}")
        
        return Response({
            'message': f'Ученик {student_name} успешно удален'
        }, status=status.HTTP_200_OK)


class AdminStatusMessagesView(APIView):
    """Управление сообщениями статус-бара"""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Получить активные сообщения"""
        if request.user.role != 'admin':
            # Для обычных пользователей - только их сообщения
            user_role = 'teachers' if request.user.role == 'teacher' else 'students'
            messages = StatusBarMessage.objects.filter(
                Q(target=user_role) | Q(target='all'),
                is_active=True
            ).order_by('-created_at')
        else:
            # Для админа - все сообщения
            messages = StatusBarMessage.objects.all().order_by('-created_at')
        
        data = []
        for msg in messages:
            data.append({
                'id': msg.id,
                'message': msg.message,
                'target': msg.target,
                'is_active': msg.is_active,
                'created_at': msg.created_at,
                'created_by': msg.created_by.email if msg.created_by else None
            })
        
        return Response(data)
    
    def post(self, request):
        """Создать новое сообщение"""
        if request.user.role != 'admin':
            return Response(
                {'error': 'Доступ запрещен'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        message = request.data.get('message', '').strip()
        target = request.data.get('target', 'all')
        
        if not message:
            return Response(
                {'error': 'Сообщение не может быть пустым'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if target not in ['teachers', 'students', 'all']:
            return Response(
                {'error': 'Неверный target'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        msg = StatusBarMessage.objects.create(
            message=message,
            target=target,
            created_by=request.user
        )
        
        logger.info(f"Status bar message created by {request.user.email}: {message} (target: {target})")
        
        return Response({
            'id': msg.id,
            'message': msg.message,
            'target': msg.target,
            'is_active': msg.is_active,
            'created_at': msg.created_at
        }, status=status.HTTP_201_CREATED)
    
    def delete(self, request, message_id):
        """Удалить сообщение"""
        if request.user.role != 'admin':
            return Response(
                {'error': 'Доступ запрещен'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            msg = StatusBarMessage.objects.get(id=message_id)
            msg.delete()
            logger.info(f"Status bar message deleted by {request.user.email}: {msg.message}")
            return Response({'message': 'Сообщение удалено'}, status=status.HTTP_200_OK)
        except StatusBarMessage.DoesNotExist:
            return Response(
                {'error': 'Сообщение не найдено'},
                status=status.HTTP_404_NOT_FOUND
            )


class SystemSettingsView(APIView):
    """API для управления системными настройками"""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Получить текущие настройки"""
        if request.user.role != 'admin':
            return Response(
                {'error': 'Доступ запрещен'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        settings = SystemSettings.get_settings()
        serializer = SystemSettingsSerializer(settings)
        return Response(serializer.data)
    
    def put(self, request):
        """Обновить настройки"""
        if request.user.role != 'admin':
            return Response(
                {'error': 'Доступ запрещен'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        settings = SystemSettings.get_settings()
        serializer = SystemSettingsSerializer(settings, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            logger.info(f"System settings updated by {request.user.email}")
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request):
        """Частичное обновление настроек"""
        return self.put(request)
