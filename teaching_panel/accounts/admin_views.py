from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Sum, ExpressionWrapper, F, DurationField
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
from .models import StatusBarMessage, SystemSettings, Subscription
from .subscriptions_utils import get_subscription

User = get_user_model()
logger = logging.getLogger(__name__)


def _serialize_subscription(sub: Subscription):
    if not sub:
        return None
    total_storage = (sub.total_storage_gb or 0)
    used_storage = float(sub.used_storage_gb or 0)
    storage_usage_percent = 0
    if total_storage > 0:
        storage_usage_percent = round(min(100, (used_storage / total_storage) * 100), 2)
    return {
        'plan': sub.plan,
        'status': sub.status,
        'expires_at': sub.expires_at,
        'remaining_days': sub.days_until_expiry(),
        'base_storage_gb': sub.base_storage_gb,
        'extra_storage_gb': sub.extra_storage_gb,
        'used_storage_gb': used_storage,
        'total_storage_gb': total_storage,
        'storage_usage_percent': storage_usage_percent,
        'auto_renew': sub.auto_renew,
        'next_billing_date': sub.next_billing_date,
        'last_payment_date': sub.last_payment_date,
        'total_paid': sub.total_paid,
    }


def _ensure_admin(request):
    if request.user.role != 'admin':
        raise PermissionError('Доступ запрещен')


def _format_timedelta_minutes(duration):
    if not duration:
        return 0
    return int(duration.total_seconds() // 60)


def _get_teacher_metrics(teacher):
    now = timezone.now()
    lessons_qs = Lesson.objects.filter(teacher=teacher)
    total_lessons = lessons_qs.count()
    recent_period = now - timedelta(days=30)
    recent_lessons_qs = lessons_qs.filter(start_time__gte=recent_period)
    duration_expr = ExpressionWrapper(F('end_time') - F('start_time'), output_field=DurationField())
    duration_value = recent_lessons_qs.aggregate(total=Sum(duration_expr))['total']
    teaching_minutes_recent = _format_timedelta_minutes(duration_value)

    groups_qs = ScheduleGroup.objects.filter(teacher=teacher)
    total_groups = groups_qs.count()
    total_students = groups_qs.filter(students__isnull=False).values('students').distinct().count()

    return {
        'total_lessons': total_lessons,
        'lessons_last_30_days': recent_lessons_qs.count(),
        'teaching_minutes_last_30_days': teaching_minutes_recent,
        'total_groups': total_groups,
        'total_students': total_students,
    }


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
        
        # Подсчет пользователей
        total_users = User.objects.count()
        teachers = User.objects.filter(role='teacher').count()
        students = User.objects.filter(role='student').count()
        
        # Онлайн пользователи (активность за последние 15 минут)
        online_threshold = timezone.now() - timedelta(minutes=15)
        teachers_online = User.objects.filter(
            role='teacher',
            last_login__gte=online_threshold
        ).count()
        students_online = User.objects.filter(
            role='student',
            last_login__gte=online_threshold
        ).count()
        
        # Группы
        groups = ScheduleGroup.objects.count()
        
        # Занятия
        lessons = Lesson.objects.count()
        
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
            teacher_growth = User.objects.filter(
                role='teacher',
                created_at__gte=period_start
            ).count()
            student_growth = User.objects.filter(
                role='student',
                created_at__gte=period_start
            ).count()
            lesson_growth = Lesson.objects.filter(
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

        # Поиск и пагинация
        search_q = request.query_params.get('q', '').strip()
        try:
            limit = int(request.query_params.get('limit', 50))
        except (TypeError, ValueError):
            limit = 50
        try:
            offset = int(request.query_params.get('offset', 0))
        except (TypeError, ValueError):
            offset = 0

        limit = max(1, min(limit, 200))  # не больше 200 за запрос
        offset = max(0, offset)

        teachers_qs = User.objects.filter(role='teacher')
        if search_q:
            teachers_qs = teachers_qs.filter(
                Q(email__icontains=search_q)
                | Q(first_name__icontains=search_q)
                | Q(last_name__icontains=search_q)
                | Q(middle_name__icontains=search_q)
            )

        total = teachers_qs.count()
        teachers = teachers_qs.order_by('last_name', 'first_name')[offset:offset + limit]

        teachers_data = []
        now = timezone.now()
        for teacher in teachers:
            try:
                subscription = teacher.subscription
            except Subscription.DoesNotExist:
                subscription = None
            metrics = _get_teacher_metrics(teacher)
            days_on_platform = (now - teacher.created_at).days if teacher.created_at else 0
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
                'subscription': _serialize_subscription(subscription),
                'metrics': metrics,
                'days_on_platform': days_on_platform,
            })

        return Response({
            'results': teachers_data,
            'total': total,
            'limit': limit,
            'offset': offset,
        })


class AdminTeacherDetailView(APIView):
    """Детальная информация по преподавателю"""

    permission_classes = [IsAuthenticated]

    def get(self, request, teacher_id):
        if request.user.role != 'admin':
            return Response({'error': 'Доступ запрещен'}, status=status.HTTP_403_FORBIDDEN)

        try:
            teacher = User.objects.get(id=teacher_id, role='teacher')
        except User.DoesNotExist:
            return Response({'error': 'Учитель не найден'}, status=status.HTTP_404_NOT_FOUND)

        subscription = get_subscription(teacher)
        metrics = _get_teacher_metrics(teacher)
        days_on_platform = 0
        if teacher.created_at:
            days_on_platform = (timezone.now() - teacher.created_at).days

        zoom_config = {
            'zoom_account_id': teacher.zoom_account_id,
            'zoom_client_id': teacher.zoom_client_id,
            'zoom_client_secret': teacher.zoom_client_secret,
            'zoom_user_id': teacher.zoom_user_id,
            'has_zoom_config': bool(teacher.zoom_account_id and teacher.zoom_client_id and teacher.zoom_client_secret),
        }

        metrics_extended = {
            **metrics,
            'teaching_hours_last_30_days': round(metrics['teaching_minutes_last_30_days'] / 60, 2) if metrics['teaching_minutes_last_30_days'] else 0,
        }

        profile = {
            'id': teacher.id,
            'first_name': teacher.first_name,
            'last_name': teacher.last_name,
            'middle_name': teacher.middle_name,
            'email': teacher.email,
            'phone_number': teacher.phone_number,
            'role': teacher.role,
            'created_at': teacher.created_at,
            'last_login': teacher.last_login,
            'days_on_platform': days_on_platform,
            'avatar': teacher.avatar,
        }

        return Response({
            'teacher': profile,
            'subscription': _serialize_subscription(subscription),
            'metrics': metrics_extended,
            'zoom': zoom_config,
        })


class AdminTeacherSubscriptionView(APIView):
    """Управление подпиской преподавателя"""

    permission_classes = [IsAuthenticated]

    def post(self, request, teacher_id):
        if request.user.role != 'admin':
            return Response({'error': 'Доступ запрещен'}, status=status.HTTP_403_FORBIDDEN)

        action = request.data.get('action')
        if action not in {'activate', 'deactivate'}:
            return Response({'error': 'Некорректное действие'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            teacher = User.objects.get(id=teacher_id, role='teacher')
        except User.DoesNotExist:
            return Response({'error': 'Учитель не найден'}, status=status.HTTP_404_NOT_FOUND)

        subscription = get_subscription(teacher)

        if action == 'activate':
            days = request.data.get('days') or 28
            try:
                days = int(days)
            except (TypeError, ValueError):
                days = 28
            days = max(1, min(days, 365))
            subscription.plan = Subscription.PLAN_MONTHLY
            subscription.status = Subscription.STATUS_ACTIVE
            subscription.expires_at = timezone.now() + timedelta(days=days)
            subscription.auto_renew = False
            update_fields = ['plan', 'status', 'expires_at', 'auto_renew', 'updated_at']
        else:
            subscription.status = Subscription.STATUS_PENDING
            subscription.expires_at = timezone.now()
            subscription.auto_renew = False
            update_fields = ['status', 'expires_at', 'auto_renew', 'updated_at']

        subscription.save(update_fields=update_fields)
        subscription.refresh_from_db()

        return Response({'subscription': _serialize_subscription(subscription)})


class AdminTeacherStorageView(APIView):
    """Добавление дополнительного хранилища преподавателю"""

    permission_classes = [IsAuthenticated]

    def post(self, request, teacher_id):
        if request.user.role != 'admin':
            return Response({'error': 'Доступ запрещен'}, status=status.HTTP_403_FORBIDDEN)

        extra_gb = request.data.get('extra_gb')
        try:
            extra_gb = int(extra_gb)
        except (TypeError, ValueError):
            extra_gb = 0

        if extra_gb <= 0:
            return Response({'error': 'Укажите количество гигабайт больше 0'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            teacher = User.objects.get(id=teacher_id, role='teacher')
        except User.DoesNotExist:
            return Response({'error': 'Учитель не найден'}, status=status.HTTP_404_NOT_FOUND)

        subscription = get_subscription(teacher)
        subscription.extra_storage_gb += extra_gb
        subscription.save(update_fields=['extra_storage_gb', 'updated_at'])
        subscription.refresh_from_db()

        return Response({'subscription': _serialize_subscription(subscription)})


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
            teacher = User.objects.get(id=teacher_id, role='teacher')
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
            teacher = User.objects.get(id=teacher_id, role='teacher')
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
        
        students = User.objects.filter(role='student').order_by('last_name', 'first_name')
        
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
            student = User.objects.get(id=student_id, role='student')
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
            student = User.objects.get(id=student_id, role='student')
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


class AdminCreateStudentView(APIView):
    """Создание нового ученика администратором"""
    
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
        
        # Создание ученика
        try:
            student = User(
                email=email,
                first_name=first_name,
                last_name=last_name,
                middle_name=middle_name,
                phone_number=phone_number if phone_number else None,
                role='student',
                is_active=True
            )
            student.set_password(password)
            student.save()
            
            logger.info(f"Student created successfully: {student.email} (ID: {student.id})")
            
            serializer = UserProfileSerializer(student)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            logger.error(f"Failed to create student: {error_detail}")
            return Response(
                {'error': str(e), 'detail': error_detail if settings.DEBUG else str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminChangeTeacherPasswordView(APIView):
    """Смена пароля учителя администратором"""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request, teacher_id):
        # Проверка прав админа
        if request.user.role != 'admin':
            return Response(
                {'error': 'Доступ запрещен'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            teacher = User.objects.get(id=teacher_id, role='teacher')
        except User.DoesNotExist:
            return Response(
                {'error': 'Учитель не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        new_password = request.data.get('new_password')
        
        if not new_password:
            return Response(
                {'error': 'Новый пароль обязателен'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(new_password) < 6:
            return Response(
                {'error': 'Пароль должен быть минимум 6 символов'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        teacher.set_password(new_password)
        teacher.save()
        
        logger.info(f"Password changed for teacher {teacher.email} (ID: {teacher_id}) by admin {request.user.email}")
        
        return Response({
            'message': f'Пароль для {teacher.first_name} {teacher.last_name} успешно изменен'
        }, status=status.HTTP_200_OK)


class AdminChangeStudentPasswordView(APIView):
    """Смена пароля ученика администратором"""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request, student_id):
        # Проверка прав админа
        if request.user.role != 'admin':
            return Response(
                {'error': 'Доступ запрещен'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            student = User.objects.get(id=student_id, role='student')
        except User.DoesNotExist:
            return Response(
                {'error': 'Ученик не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        new_password = request.data.get('new_password')
        
        if not new_password:
            return Response(
                {'error': 'Новый пароль обязателен'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(new_password) < 6:
            return Response(
                {'error': 'Пароль должен быть минимум 6 символов'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        student.set_password(new_password)
        student.save()
        
        logger.info(f"Password changed for student {student.email} (ID: {student_id}) by admin {request.user.email}")
        
        return Response({
            'message': f'Пароль для {student.first_name} {student.last_name} успешно изменен'
        }, status=status.HTTP_200_OK)

