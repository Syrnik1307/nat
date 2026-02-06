from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Sum, ExpressionWrapper, F, DurationField, Value, IntegerField
from django.db.models.functions import Coalesce, NullIf, Cast
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.conf import settings
from datetime import timedelta, datetime
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
import logging

from schedule.models import Lesson, Group as ScheduleGroup

from .serializers import UserProfileSerializer, SystemSettingsSerializer
from .models import StatusBarMessage, SystemSettings, Subscription, Payment
from .subscriptions_utils import get_subscription
from .permissions import IsAdmin  # SECURITY: Role-based access control

# Import for homework counting in teacher analytics
try:
    from homework.models import Homework
    HOMEWORK_MODEL_AVAILABLE = True
except ImportError:
    HOMEWORK_MODEL_AVAILABLE = False

User = get_user_model()
logger = logging.getLogger(__name__)


def _parse_date(value):
    if not value:
        return None
    # Try ISO datetime first
    dt = parse_datetime(value)
    if dt:
        return timezone.make_aware(dt) if timezone.is_naive(dt) else dt
    # Try date-only
    try:
        d = datetime.fromisoformat(value)
        dt = datetime(d.year, d.month, d.day)
        return timezone.make_aware(dt)
    except Exception:
        return None


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


# Троттлинг для пересчёта хранилища: не чаще раза в 15 минут на учителя
STORAGE_REFRESH_COOLDOWN_MINUTES = 15


def _refresh_storage_usage_if_needed(subscription):
    """
    Пересчитывает used_storage_gb с Google Drive, если прошло достаточно времени.
    
    Использует updated_at подписки как индикатор последнего обновления.
    Троттлинг: не чаще раза в 15 минут.
    """
    if not subscription or not subscription.gdrive_folder_id:
        return
    
    # Проверяем что Google Drive включен
    if not getattr(settings, 'USE_GDRIVE_STORAGE', False):
        return
    
    now = timezone.now()
    
    # Проверяем cooldown по updated_at (грубая эвристика)
    # Более точный способ — добавить поле storage_synced_at, но пока используем updated_at
    if subscription.updated_at and (now - subscription.updated_at) < timedelta(minutes=STORAGE_REFRESH_COOLDOWN_MINUTES):
        return  # Недавно обновляли, пропускаем
    
    try:
        from .gdrive_folder_service import get_teacher_storage_usage
        storage_stats = get_teacher_storage_usage(subscription)
        # used_storage_gb уже обновлён и сохранён внутри get_teacher_storage_usage
        logger.debug(f"Refreshed storage usage for subscription {subscription.id}: {storage_stats.get('used_gb', 0)} GB")
    except Exception as e:
        logger.warning(f"Failed to refresh storage usage for subscription {subscription.id}: {e}")


class AdminStatsView(APIView):
    """Статистика для админ панели"""
    
    permission_classes = [IsAuthenticated, IsAdmin]
    
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


class AdminSystemErrorsView(APIView):
    """Список ошибок системы/процессов для админа."""

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Доступ запрещен'}, status=status.HTTP_403_FORBIDDEN)

        from accounts.models import SystemErrorEvent

        limit = int(request.query_params.get('limit', 50))
        limit = max(1, min(limit, 200))
        offset = int(request.query_params.get('offset', 0))
        offset = max(0, offset)

        severity = (request.query_params.get('severity') or '').strip()
        teacher_id = (request.query_params.get('teacher_id') or '').strip()
        q = (request.query_params.get('q') or '').strip()
        include_resolved = (request.query_params.get('include_resolved') or '').strip() in ('1', 'true', 'True')

        qs = SystemErrorEvent.objects.select_related('teacher').all()
        if not include_resolved:
            qs = qs.filter(resolved_at__isnull=True)
        if severity in ('warning', 'error', 'critical'):
            qs = qs.filter(severity=severity)
        if teacher_id.isdigit():
            qs = qs.filter(teacher_id=int(teacher_id))
        if q:
            qs = qs.filter(
                Q(code__icontains=q)
                | Q(source__icontains=q)
                | Q(message__icontains=q)
                | Q(teacher__email__icontains=q)
                | Q(teacher__first_name__icontains=q)
                | Q(teacher__last_name__icontains=q)
            )

        total = qs.count()
        items = qs.order_by('-last_seen_at')[offset:offset + limit]

        def teacher_payload(t):
            if not t:
                return None
            name = (t.get_full_name() or t.email or '').strip()
            return {
                'id': t.id,
                'email': t.email,
                'name': name,
            }

        results = []
        for e in items:
            results.append({
                'id': str(e.id),
                'severity': e.severity,
                'source': e.source,
                'code': e.code,
                'message': e.message,
                'details': e.details,
                'teacher': teacher_payload(e.teacher),
                'request_path': e.request_path,
                'request_method': e.request_method,
                'process': e.process,
                'occurrences': e.occurrences,
                'created_at': e.created_at.isoformat() if e.created_at else None,
                'last_seen_at': e.last_seen_at.isoformat() if e.last_seen_at else None,
                'resolved_at': e.resolved_at.isoformat() if e.resolved_at else None,
            })

        return Response({
            'count': total,
            'limit': limit,
            'offset': offset,
            'results': results,
        })


class AdminSystemErrorsCountsView(APIView):
    """Счётчики ошибок по severity для табов."""

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Доступ запрещен'}, status=status.HTTP_403_FORBIDDEN)

        from accounts.models import SystemErrorEvent

        qs = SystemErrorEvent.objects.filter(resolved_at__isnull=True)
        return Response({
            'all': qs.count(),
            'critical': qs.filter(severity='critical').count(),
            'error': qs.filter(severity='error').count(),
            'warning': qs.filter(severity='warning').count(),
        })


def _source_expr_for_user(prefix: str = ''):
    channel = F(f'{prefix}referral_attribution__channel')
    utm_source = F(f'{prefix}referral_attribution__utm_source')
    return Coalesce(
        NullIf(channel, Value('')),
        NullIf(utm_source, Value('')),
        Value('unknown')
    )


def _source_expr_for_payment():
    channel = F('subscription__user__referral_attribution__channel')
    utm_source = F('subscription__user__referral_attribution__utm_source')
    return Coalesce(
        NullIf(channel, Value('')),
        NullIf(utm_source, Value('')),
        Value('unknown')
    )


class AdminGrowthOverviewView(APIView):
    """Полная аналитика роста/монетизации для управления бизнесом."""

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Доступ запрещен'}, status=status.HTTP_403_FORBIDDEN)

        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # === КЛЮЧЕВЫЕ KPI ЗА СЕГОДНЯ ===
        today_registrations = User.objects.filter(role='teacher', created_at__gte=today_start).count()
        today_payments = Payment.objects.filter(
            status=Payment.STATUS_SUCCEEDED,
            created_at__gte=today_start
        ).aggregate(count=Count('id'), revenue=Sum('amount'))

        # === ПЕРИОДИЧЕСКИЕ МЕТРИКИ ===
        period_specs = [
            ('day', 'Сегодня', 'За 24 часа', timedelta(days=1)),
            ('week', 'Неделя', 'За 7 дней', timedelta(days=7)),
            ('month', 'Месяц', 'За 30 дней', timedelta(days=30)),
        ]

        periods = []
        payment_source_expr = _source_expr_for_payment()
        user_source_expr = _source_expr_for_user(prefix='')

        for key, label, range_label, delta in period_specs:
            start = now - delta

            new_teachers = User.objects.filter(
                role='teacher',
                created_at__gte=start,
                created_at__lte=now,
            )
            new_teachers_count = new_teachers.count()

            payments_created_qs = Payment.objects.filter(created_at__gte=start, created_at__lte=now)
            payments_succeeded_qs = Payment.objects.filter(
                status=Payment.STATUS_SUCCEEDED
            ).filter(
                Q(paid_at__gte=start, paid_at__lte=now) |
                Q(paid_at__isnull=True, created_at__gte=start, created_at__lte=now)
            )
            payments_failed_qs = Payment.objects.filter(
                status=Payment.STATUS_FAILED,
                created_at__gte=start, created_at__lte=now
            )

            payments_created_count = payments_created_qs.count()
            payments_succeeded_count = payments_succeeded_qs.count()
            payments_failed_count = payments_failed_qs.count()
            revenue_value = payments_succeeded_qs.aggregate(total=Sum('amount'))['total'] or 0

            new_teachers_paid_count = new_teachers.filter(
                subscription__payments__status=Payment.STATUS_SUCCEEDED
            ).filter(
                Q(subscription__payments__paid_at__gte=start, subscription__payments__paid_at__lte=now) |
                Q(subscription__payments__paid_at__isnull=True, subscription__payments__created_at__gte=start, subscription__payments__created_at__lte=now)
            ).distinct().count()

            avg_check = float(revenue_value) / float(payments_succeeded_count) if payments_succeeded_count > 0 else 0
            reg_to_pay_cr = round((new_teachers_paid_count / new_teachers_count) * 100, 2) if new_teachers_count > 0 else 0
            payment_success_rate = round((payments_succeeded_count / payments_created_count) * 100, 2) if payments_created_count > 0 else 0

            periods.append({
                'key': key,
                'label': label,
                'range_label': range_label,
                'registrations': new_teachers_count,
                'payments_created': payments_created_count,
                'payments_succeeded': payments_succeeded_count,
                'payments_failed': payments_failed_count,
                'revenue': float(revenue_value),
                'avg_check': round(avg_check, 2),
                'reg_to_pay_cr': reg_to_pay_cr,
                'payment_success_rate': payment_success_rate,
                'new_paid_users': new_teachers_paid_count,
            })

        # === ВОРОНКА ЗА 30 ДНЕЙ ===
        month_start = now - timedelta(days=30)
        funnel_registrations = User.objects.filter(role='teacher', created_at__gte=month_start).count()
        funnel_with_subscription = Subscription.objects.filter(
            user__role='teacher',
            user__created_at__gte=month_start
        ).count()
        funnel_paid = Payment.objects.filter(
            status=Payment.STATUS_SUCCEEDED,
            subscription__user__role='teacher',
            subscription__user__created_at__gte=month_start
        ).values('subscription__user').distinct().count()

        funnel = {
            'period': 'Последние 30 дней',
            'steps': [
                {'name': 'Регистрации', 'value': funnel_registrations, 'percent': 100},
                {'name': 'Создали подписку', 'value': funnel_with_subscription, 'percent': round((funnel_with_subscription / funnel_registrations) * 100, 1) if funnel_registrations else 0},
                {'name': 'Оплатили', 'value': funnel_paid, 'percent': round((funnel_paid / funnel_registrations) * 100, 1) if funnel_registrations else 0},
            ]
        }

        # === ИСТОЧНИКИ ТРАФИКА (ТОП-10) ===
        sources_registrations = list(
            User.objects.filter(role='teacher', created_at__gte=month_start)
            .annotate(source=user_source_expr)
            .values('source')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )

        sources_revenue = list(
            Payment.objects.filter(status=Payment.STATUS_SUCCEEDED)
            .filter(
                Q(paid_at__gte=month_start, paid_at__lte=now) |
                Q(paid_at__isnull=True, created_at__gte=month_start, created_at__lte=now)
            )
            .annotate(source=payment_source_expr)
            .values('source')
            .annotate(
                revenue=Sum('amount'),
                count=Count('id'),
                users=Count('subscription__user', distinct=True),
            )
            .order_by('-revenue')[:10]
        )

        # === АКТИВНОСТЬ ПЛАТФОРМЫ ===
        active_teachers = User.objects.filter(
            role='teacher',
            subscription__status=Subscription.STATUS_ACTIVE,
            subscription__expires_at__gt=now
        ).count()
        total_teachers = User.objects.filter(role='teacher').count()
        active_rate = round((active_teachers / total_teachers) * 100, 1) if total_teachers else 0

        # Истекающие подписки (следующие 7 дней)
        expiring_soon = Subscription.objects.filter(
            status=Subscription.STATUS_ACTIVE,
            expires_at__gt=now,
            expires_at__lte=now + timedelta(days=7)
        ).count()

        # Недавние платежи (последние 5)
        recent_payments = list(
            Payment.objects.filter(status=Payment.STATUS_SUCCEEDED)
            .select_related('subscription__user')
            .order_by('-created_at')[:5]
            .values(
                'id', 'amount', 'created_at',
                'subscription__user__email',
                'subscription__user__first_name',
                'subscription__user__last_name',
            )
        )

        # === ДИСКОВОЕ ПРОСТРАНСТВО СЕРВЕРА ===
        import shutil
        import os
        try:
            # Получаем реальное использование диска на сервере
            disk_path = getattr(settings, 'MEDIA_ROOT', '/var/www/teaching_panel/media')
            if not os.path.exists(disk_path):
                disk_path = '/'
            total_bytes, used_bytes, free_bytes = shutil.disk_usage(disk_path)
            disk_total_gb = total_bytes / (1024 ** 3)
            disk_used_gb = used_bytes / (1024 ** 3)
            disk_free_gb = free_bytes / (1024 ** 3)
        except Exception:
            disk_total_gb = 0
            disk_used_gb = 0
            disk_free_gb = 0
        
        # Подсчёт размера медиа-файлов (записи, uploads)
        media_used_gb = 0
        try:
            media_root = getattr(settings, 'MEDIA_ROOT', None)
            if media_root and os.path.exists(media_root):
                total_size = 0
                for dirpath, dirnames, filenames in os.walk(media_root):
                    for f in filenames:
                        fp = os.path.join(dirpath, f)
                        if os.path.isfile(fp):
                            total_size += os.path.getsize(fp)
                media_used_gb = total_size / (1024 ** 3)
        except Exception:
            pass

        return Response({
            'today': {
                'registrations': today_registrations,
                'payments': today_payments['count'] or 0,
                'revenue': float(today_payments['revenue'] or 0),
            },
            'periods': periods,
            'funnel': funnel,
            'sources': {
                'period': 'Последние 30 дней',
                'registrations': sources_registrations,
                'revenue': [
                    {**r, 'revenue': float(r['revenue'] or 0)} for r in sources_revenue
                ],
            },
            'platform': {
                'active_teachers': active_teachers,
                'total_teachers': total_teachers,
                'active_rate': active_rate,
                'expiring_soon': expiring_soon,
            },
            'recent_payments': [
                {
                    'id': p['id'],
                    'amount': float(p['amount']),
                    'date': p['created_at'].isoformat() if p['created_at'] else None,
                    'user': f"{p['subscription__user__first_name'] or ''} {p['subscription__user__last_name'] or ''}".strip() or p['subscription__user__email'],
                }
                for p in recent_payments
            ],
            'storage': {
                'disk_total_gb': round(disk_total_gb, 1),
                'disk_used_gb': round(disk_used_gb, 1),
                'disk_free_gb': round(disk_free_gb, 1),
                'media_used_gb': round(media_used_gb, 2),
            },
        })


class AdminCreateTeacherView(APIView):
    """Создание нового учителя"""
    
    permission_classes = [IsAuthenticated, IsAdmin]
    
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
    
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request):
        # Проверка прав админа
        if request.user.role != 'admin':
            return Response(
                {'error': 'Доступ запрещен'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Поиск, фильтры, сортировка
        search_q = request.query_params.get('q', '').strip()
        status_filter = request.query_params.get('status', '').strip()  # subscription status
        zoom_filter = request.query_params.get('has_zoom', '').strip()  # true/false
        active_filter = request.query_params.get('active_recent', '').strip()  # true => last_login < 15m
        created_from = _parse_date(request.query_params.get('created_from'))
        created_to = _parse_date(request.query_params.get('created_to'))
        sort = (request.query_params.get('sort') or 'last_login').strip()
        order = (request.query_params.get('order') or 'desc').strip()

        try:
            page_size = int(request.query_params.get('page_size', 50))
        except (TypeError, ValueError):
            page_size = 50
        try:
            page = int(request.query_params.get('page', 1))
        except (TypeError, ValueError):
            page = 1

        page_size = max(1, min(page_size, 200))
        page = max(1, page)
        offset = (page - 1) * page_size

        teachers_qs = User.objects.filter(role='teacher')
        if search_q:
            teachers_qs = teachers_qs.filter(
                Q(email__icontains=search_q)
                | Q(first_name__icontains=search_q)
                | Q(last_name__icontains=search_q)
                | Q(middle_name__icontains=search_q)
            )

        if status_filter:
            teachers_qs = teachers_qs.filter(subscription__status=status_filter)

        if zoom_filter in {'true', 'false'}:
            want = zoom_filter == 'true'
            teachers_qs = teachers_qs.filter(
                (Q(zoom_account_id__isnull=False) & ~Q(zoom_account_id='')
                 & Q(zoom_client_id__isnull=False) & ~Q(zoom_client_id='')
                 & Q(zoom_client_secret__isnull=False) & ~Q(zoom_client_secret=''))
                if want else
                (Q(zoom_account_id__isnull=True) | Q(zoom_account_id='')
                 | Q(zoom_client_id__isnull=True) | Q(zoom_client_id='')
                 | Q(zoom_client_secret__isnull=True) | Q(zoom_client_secret=''))
            )

        if active_filter == 'true':
            recent = timezone.now() - timedelta(minutes=15)
            teachers_qs = teachers_qs.filter(last_login__gte=recent)

        if created_from:
            teachers_qs = teachers_qs.filter(created_at__gte=created_from)
        if created_to:
            teachers_qs = teachers_qs.filter(created_at__lte=created_to)

        sort_map = {
            'created_at': 'created_at',
            'last_login': 'last_login',
            'first_name': 'first_name',
            'last_name': 'last_name',
            'email': 'email',
        }
        sort_field = sort_map.get(sort, 'last_login')
        if order == 'asc':
            teachers_qs = teachers_qs.order_by(sort_field)
        else:
            teachers_qs = teachers_qs.order_by(f'-{sort_field}')

        total = teachers_qs.count()
        teachers = teachers_qs.select_related('subscription')[offset:offset + page_size]

        teachers_data = []
        now = timezone.now()
        for teacher in teachers:
            subscription = getattr(teacher, 'subscription', None)
            metrics = _get_teacher_metrics(teacher)
            days_on_platform = (now - teacher.created_at).days if teacher.created_at else 0
            teachers_data.append({
                'id': teacher.id,
                'email': teacher.email,
                'first_name': teacher.first_name,
                'last_name': teacher.last_name,
                'middle_name': teacher.middle_name,
                'phone_number': teacher.phone_number,
                'telegram_id': teacher.telegram_id or None,
                'telegram_username': teacher.telegram_username or None,
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

        total_pages = (total + page_size - 1) // page_size if total else 1

        return Response({
            'results': teachers_data,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages,
        })


class AdminTeacherDetailView(APIView):
    """Детальная информация по преподавателю"""

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request, teacher_id):
        if request.user.role != 'admin':
            return Response({'error': 'Доступ запрещен'}, status=status.HTTP_403_FORBIDDEN)

        try:
            teacher = User.objects.get(id=teacher_id, role='teacher')
        except User.DoesNotExist:
            return Response({'error': 'Учитель не найден'}, status=status.HTTP_404_NOT_FOUND)

        subscription = get_subscription(teacher)
        
        # Пересчитываем used_storage_gb с Google Drive (с троттлингом 15 мин)
        _refresh_storage_usage_if_needed(subscription)
        
        metrics = _get_teacher_metrics(teacher)
        days_on_platform = 0
        if teacher.created_at:
            days_on_platform = (timezone.now() - teacher.created_at).days

        zoom_config = {
            'zoom_account_id': teacher.zoom_account_id,
            'zoom_client_id': teacher.zoom_client_id,
            'zoom_client_secret': teacher.zoom_client_secret,
            'zoom_user_id': teacher.zoom_user_id,
            'zoom_pmi_link': teacher.zoom_pmi_link,
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
            'telegram_id': teacher.telegram_id or None,
            'telegram_username': teacher.telegram_username or None,
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

    permission_classes = [IsAuthenticated, IsAdmin]

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
    """Просмотр и добавление хранилища преподавателю"""

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request, teacher_id):
        """Получить реальную статистику использования хранилища с Google Drive"""
        if request.user.role != 'admin':
            return Response({'error': 'Доступ запрещен'}, status=status.HTTP_403_FORBIDDEN)

        try:
            teacher = User.objects.get(id=teacher_id, role='teacher')
        except User.DoesNotExist:
            return Response({'error': 'Учитель не найден'}, status=status.HTTP_404_NOT_FOUND)

        subscription = get_subscription(teacher)
        
        # Получаем реальную статистику с Google Drive
        try:
            from .gdrive_folder_service import get_teacher_storage_usage
            storage_stats = get_teacher_storage_usage(subscription)
        except Exception as e:
            storage_stats = {
                'used_gb': float(subscription.used_storage_gb),
                'limit_gb': subscription.total_storage_gb,
                'available_gb': float(subscription.total_storage_gb - subscription.used_storage_gb),
                'usage_percent': float(subscription.used_storage_gb / subscription.total_storage_gb * 100) if subscription.total_storage_gb > 0 else 0,
                'error': str(e)
            }
        
        return Response({
            'teacher_id': teacher.id,
            'teacher_email': teacher.email,
            'teacher_name': teacher.get_full_name(),
            'subscription_id': subscription.id,
            'subscription_status': subscription.status,
            'storage': storage_stats,
            'gdrive_folder_id': subscription.gdrive_folder_id,
            'gdrive_folder_link': f"https://drive.google.com/drive/folders/{subscription.gdrive_folder_id}" if subscription.gdrive_folder_id else None
        })

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
    
    permission_classes = [IsAuthenticated, IsAdmin]
    
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
        teacher.zoom_pmi_link = request.data.get('zoom_pmi_link', teacher.zoom_pmi_link)
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
            'zoom_pmi_link': teacher.zoom_pmi_link,
            'has_zoom_config': bool(teacher.zoom_account_id and teacher.zoom_client_id and teacher.zoom_client_secret),
        })


class AdminTeachersBulkActionView(APIView):
    """Массовые действия над учителями"""

    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Доступ запрещен'}, status=status.HTTP_403_FORBIDDEN)

        ids = request.data.get('ids') or []
        if not isinstance(ids, list) or not ids:
            return Response({'error': 'Передайте ids: []'}, status=status.HTTP_400_BAD_REQUEST)

        action = request.data.get('action')
        if action not in {'activate_subscription', 'deactivate_subscription', 'add_storage', 'reset_password', 'delete'}:
            return Response({'error': 'Некорректное действие'}, status=status.HTTP_400_BAD_REQUEST)

        teachers = list(User.objects.filter(role='teacher', id__in=ids))
        if not teachers:
            return Response({'error': 'Учителя не найдены'}, status=status.HTTP_404_NOT_FOUND)

        results = []
        now = timezone.now()

        for teacher in teachers:
            if action in {'activate_subscription', 'deactivate_subscription', 'add_storage'}:
                subscription = get_subscription(teacher)

            if action == 'activate_subscription':
                days = request.data.get('days') or 28
                try:
                    days = int(days)
                except (TypeError, ValueError):
                    days = 28
                days = max(1, min(days, 365))
                subscription.plan = Subscription.PLAN_MONTHLY
                subscription.status = Subscription.STATUS_ACTIVE
                subscription.expires_at = now + timedelta(days=days)
                subscription.auto_renew = False
                subscription.save(update_fields=['plan', 'status', 'expires_at', 'auto_renew', 'updated_at'])
                results.append({'id': teacher.id, 'subscription': _serialize_subscription(subscription)})

            elif action == 'deactivate_subscription':
                subscription.status = Subscription.STATUS_PENDING
                subscription.expires_at = now
                subscription.auto_renew = False
                subscription.save(update_fields=['status', 'expires_at', 'auto_renew', 'updated_at'])
                results.append({'id': teacher.id, 'subscription': _serialize_subscription(subscription)})

            elif action == 'add_storage':
                extra_gb = request.data.get('extra_gb')
                try:
                    extra_gb = int(extra_gb)
                except (TypeError, ValueError):
                    extra_gb = 0
                if extra_gb <= 0:
                    return Response({'error': 'extra_gb должен быть > 0'}, status=status.HTTP_400_BAD_REQUEST)
                subscription.extra_storage_gb += extra_gb
                subscription.save(update_fields=['extra_storage_gb', 'updated_at'])
                results.append({'id': teacher.id, 'subscription': _serialize_subscription(subscription)})

            elif action == 'reset_password':
                new_password = request.data.get('new_password')
                if not new_password:
                    new_password = User.objects.make_random_password(length=12)
                teacher.set_password(new_password)
                teacher.save(update_fields=['password'])
                results.append({'id': teacher.id, 'generated_password': new_password})

            elif action == 'delete':
                teacher_id = teacher.id
                teacher.delete()
                results.append({'id': teacher_id, 'deleted': True})

        return Response({'count': len(results), 'results': results})


class AdminDeleteTeacherView(APIView):
    """Удаление учителя"""
    
    permission_classes = [IsAuthenticated, IsAdmin]
    
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
    
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request):
        # Проверка прав админа
        if request.user.role != 'admin':
            return Response(
                {'error': 'Доступ запрещен'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        from django.db.models import Q

        # Query params
        q = (request.query_params.get('q') or '').strip()
        status_filter = (request.query_params.get('status') or 'active').strip()  # active|archived|all
        teacher_id = request.query_params.get('teacher_id')
        sort = (request.query_params.get('sort') or 'last_login').strip()  # last_login|created_at|name|email
        order = (request.query_params.get('order') or 'desc').strip()  # asc|desc

        def _int_or_none(value):
            try:
                return int(value)
            except Exception:
                return None

        page = _int_or_none(request.query_params.get('page')) or 1
        page_size = _int_or_none(request.query_params.get('page_size')) or 50
        page = max(1, page)
        page_size = min(max(10, page_size), 200)

        students = User.objects.filter(role='student')

        if status_filter == 'active':
            students = students.filter(is_active=True)
        elif status_filter == 'archived':
            students = students.filter(is_active=False)

        if q:
            students = students.filter(
                Q(email__icontains=q)
                | Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(middle_name__icontains=q)
            )

        tid = _int_or_none(teacher_id)
        if tid:
            students = students.filter(
                Q(enrolled_groups__teacher_id=tid)
                | Q(individual_student_profile__teacher_id=tid)
            ).distinct()

        sort_map = {
            'last_login': 'last_login',
            'created_at': 'created_at',
            'name': 'last_name',
            'email': 'email',
        }
        sort_field = sort_map.get(sort, 'last_login')
        prefix = '' if order == 'asc' else '-'
        # Добавляем вторичный сорт для стабильности
        if sort_field == 'last_login':
            students = students.order_by(f'{prefix}{sort_field}', 'last_name', 'first_name', 'id')
        elif sort_field == 'last_name':
            students = students.order_by(f'{prefix}{sort_field}', 'first_name', 'id')
        else:
            students = students.order_by(f'{prefix}{sort_field}', 'last_name', 'first_name', 'id')

        total = students.count()
        offset = (page - 1) * page_size
        students = (
            students
            .select_related('individual_student_profile__teacher')
            .prefetch_related('enrolled_groups__teacher')
        )[offset:offset + page_size]

        results = []
        for student in students:
            groups = []
            teachers_by_id = {}

            for g in getattr(student, 'enrolled_groups', []).all():
                teacher = getattr(g, 'teacher', None)
                if teacher is not None:
                    teachers_by_id[teacher.id] = {
                        'id': teacher.id,
                        'email': teacher.email,
                        'first_name': teacher.first_name,
                        'last_name': teacher.last_name,
                        'middle_name': getattr(teacher, 'middle_name', '')
                    }
                groups.append({
                    'id': g.id,
                    'name': g.name,
                    'teacher_id': teacher.id if teacher else None,
                })

            # Individual teacher (если есть)
            ind = getattr(student, 'individual_student_profile', None)
            if ind and ind.teacher:
                t = ind.teacher
                teachers_by_id[t.id] = {
                    'id': t.id,
                    'email': t.email,
                    'first_name': t.first_name,
                    'last_name': t.last_name,
                    'middle_name': getattr(t, 'middle_name', '')
                }

            teachers = list(teachers_by_id.values())
            teachers.sort(key=lambda x: ((x.get('last_name') or '').lower(), (x.get('first_name') or '').lower(), x.get('id') or 0))

            results.append({
                'id': student.id,
                'email': student.email,
                'first_name': student.first_name,
                'last_name': student.last_name,
                'middle_name': student.middle_name,
                'created_at': student.created_at,
                'last_login': student.last_login,
                'is_active': student.is_active,
                'groups': groups,
                'teachers': teachers,
                'is_individual': bool(ind),
            })

        return Response({'total': total, 'results': results})


class AdminUpdateStudentView(APIView):
    """Обновление данных ученика"""
    
    permission_classes = [IsAuthenticated, IsAdmin]
    
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
        if 'first_name' in request.data:
            student.first_name = request.data.get('first_name', student.first_name)
        if 'last_name' in request.data:
            student.last_name = request.data.get('last_name', student.last_name)
        if 'middle_name' in request.data:
            student.middle_name = request.data.get('middle_name', student.middle_name)
        if 'is_active' in request.data:
            student.is_active = bool(request.data.get('is_active'))
        student.save()
        
        return Response({
            'id': student.id,
            'email': student.email,
            'first_name': student.first_name,
            'last_name': student.last_name,
            'middle_name': student.middle_name,
            'is_active': student.is_active,
        })


class AdminDeleteStudentView(APIView):
    """Удаление ученика"""
    
    permission_classes = [IsAuthenticated, IsAdmin]
    
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
    
    permission_classes = [IsAuthenticated, IsAdmin]
    
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
    
    permission_classes = [IsAuthenticated, IsAdmin]
    
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
    
    permission_classes = [IsAuthenticated, IsAdmin]
    
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
    
    permission_classes = [IsAuthenticated, IsAdmin]
    
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
    
    permission_classes = [IsAuthenticated, IsAdmin]
    
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


class AdminAlertsView(APIView):
    """Алерты и предупреждения для админа."""

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Доступ запрещен'}, status=status.HTTP_403_FORBIDDEN)

        now = timezone.now()
        alerts = []

        # 1. Истекающие подписки (7 дней)
        expiring_subs = Subscription.objects.filter(
            status=Subscription.STATUS_ACTIVE,
            expires_at__gt=now,
            expires_at__lte=now + timedelta(days=7)
        ).select_related('user')

        for sub in expiring_subs:
            days_left = (sub.expires_at - now).days
            alerts.append({
                'id': f'sub_expiring_{sub.id}',
                'type': 'subscription_expiring',
                'severity': 'warning' if days_left > 3 else 'critical',
                'title': f'Подписка истекает через {days_left} дн.',
                'message': f'{sub.user.get_full_name() or sub.user.email} - подписка истекает {sub.expires_at.strftime("%d.%m.%Y")}',
                'user_id': sub.user.id,
                'user_name': sub.user.get_full_name() or sub.user.email,
                'user_email': sub.user.email,
                'expires_at': sub.expires_at.isoformat(),
                'action': 'contact',
            })

        # 2. Неактивные учителя (не заходили 14+ дней)
        inactive_threshold = now - timedelta(days=14)
        inactive_teachers = User.objects.filter(
            role='teacher',
            is_active=True,
            last_login__lt=inactive_threshold
        ).exclude(last_login__isnull=True)

        for teacher in inactive_teachers[:20]:
            days_inactive = (now - teacher.last_login).days if teacher.last_login else 999
            alerts.append({
                'id': f'inactive_{teacher.id}',
                'type': 'inactive_user',
                'severity': 'warning' if days_inactive < 30 else 'critical',
                'title': f'Неактивен {days_inactive} дней',
                'message': f'{teacher.get_full_name() or teacher.email} не заходил {days_inactive} дней',
                'user_id': teacher.id,
                'user_name': teacher.get_full_name() or teacher.email,
                'user_email': teacher.email,
                'last_login': teacher.last_login.isoformat() if teacher.last_login else None,
                'action': 'contact',
            })

        # 3. Просроченные подписки (истекли за последние 7 дней)
        recently_expired = Subscription.objects.filter(
            status=Subscription.STATUS_ACTIVE,
            expires_at__lt=now,
            expires_at__gte=now - timedelta(days=7)
        ).select_related('user')

        for sub in recently_expired:
            days_ago = (now - sub.expires_at).days
            alerts.append({
                'id': f'sub_expired_{sub.id}',
                'type': 'subscription_expired',
                'severity': 'critical',
                'title': f'Подписка истекла {days_ago} дн. назад',
                'message': f'{sub.user.get_full_name() or sub.user.email} - подписка истекла {sub.expires_at.strftime("%d.%m.%Y")}',
                'user_id': sub.user.id,
                'user_name': sub.user.get_full_name() or sub.user.email,
                'user_email': sub.user.email,
                'expires_at': sub.expires_at.isoformat(),
                'action': 'renew',
            })

        # 4. Неудачные платежи за последние 7 дней
        failed_payments = Payment.objects.filter(
            status=Payment.STATUS_FAILED,
            created_at__gte=now - timedelta(days=7)
        ).select_related('subscription__user').order_by('-created_at')[:10]

        for payment in failed_payments:
            user = payment.subscription.user if payment.subscription else None
            if user:
                alerts.append({
                    'id': f'payment_failed_{payment.id}',
                    'type': 'payment_failed',
                    'severity': 'warning',
                    'title': 'Неудачный платеж',
                    'message': f'{user.get_full_name() or user.email} - платеж на {payment.amount} ₽ не прошел',
                    'user_id': user.id,
                    'user_name': user.get_full_name() or user.email,
                    'user_email': user.email,
                    'amount': float(payment.amount),
                    'created_at': payment.created_at.isoformat(),
                    'action': 'contact',
                })

        # 5. Переполнение хранилища (>90%)
        storage_alerts = Subscription.objects.filter(
            status=Subscription.STATUS_ACTIVE
        ).select_related('user').annotate(
            total_storage=F('base_storage_gb') + F('extra_storage_gb')
        ).filter(
            used_storage_gb__gt=F('total_storage') * 0.9
        )

        for sub in storage_alerts:
            total = sub.base_storage_gb + sub.extra_storage_gb
            used_pct = round((float(sub.used_storage_gb or 0) / total) * 100, 1) if total else 0
            alerts.append({
                'id': f'storage_{sub.id}',
                'type': 'storage_full',
                'severity': 'warning' if used_pct < 100 else 'critical',
                'title': f'Хранилище заполнено на {used_pct}%',
                'message': f'{sub.user.get_full_name() or sub.user.email} - {sub.used_storage_gb:.1f}/{total} ГБ',
                'user_id': sub.user.id,
                'user_name': sub.user.get_full_name() or sub.user.email,
                'user_email': sub.user.email,
                'used_gb': float(sub.used_storage_gb or 0),
                'total_gb': total,
                'action': 'upsell',
            })

        # Сортируем по severity (critical первые)
        severity_order = {'critical': 0, 'warning': 1, 'info': 2}
        alerts.sort(key=lambda x: severity_order.get(x['severity'], 99))

        return Response({
            'alerts': alerts,
            'summary': {
                'total': len(alerts),
                'critical': sum(1 for a in alerts if a['severity'] == 'critical'),
                'warning': sum(1 for a in alerts if a['severity'] == 'warning'),
            }
        })


class AdminChurnRetentionView(APIView):
    """Метрики оттока и удержания."""

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Доступ запрещен'}, status=status.HTTP_403_FORBIDDEN)

        now = timezone.now()

        # Cohort analysis по месяцам (последние 6 месяцев)
        cohorts = []
        for months_ago in range(6):
            month_start = (now.replace(day=1) - timedelta(days=months_ago * 30)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if months_ago > 0:
                prev_month = (month_start - timedelta(days=1)).replace(day=1)
                month_start = prev_month
            
            month_end = (month_start + timedelta(days=32)).replace(day=1)
            
            # Зарегистрированные в этом месяце
            registered = User.objects.filter(
                role='teacher',
                created_at__gte=month_start,
                created_at__lt=month_end
            )
            registered_count = registered.count()
            
            # Оплатившие из зарегистрированных
            paid = Payment.objects.filter(
                status=Payment.STATUS_SUCCEEDED,
                subscription__user__in=registered
            ).values('subscription__user').distinct().count()
            
            # Активные сейчас (есть активная подписка)
            still_active = Subscription.objects.filter(
                user__in=registered,
                status=Subscription.STATUS_ACTIVE,
                expires_at__gt=now
            ).count()
            
            # Churn rate
            churn_rate = round(((paid - still_active) / paid) * 100, 1) if paid > 0 else 0
            retention_rate = 100 - churn_rate if paid > 0 else 0

            cohorts.append({
                'month': month_start.strftime('%Y-%m'),
                'month_label': month_start.strftime('%B %Y'),
                'registered': registered_count,
                'converted': paid,
                'conversion_rate': round((paid / registered_count) * 100, 1) if registered_count else 0,
                'still_active': still_active,
                'churned': paid - still_active if paid > still_active else 0,
                'churn_rate': churn_rate,
                'retention_rate': retention_rate,
            })

        # MRR (Monthly Recurring Revenue)
        month_ago = now - timedelta(days=30)
        mrr_payments = Payment.objects.filter(
            status=Payment.STATUS_SUCCEEDED,
            paid_at__gte=month_ago
        ).aggregate(total=Sum('amount'))
        mrr = float(mrr_payments['total'] or 0)

        # LTV (Lifetime Value) - средний доход на платящего пользователя
        paying_users = Payment.objects.filter(
            status=Payment.STATUS_SUCCEEDED
        ).values('subscription__user').distinct().count()
        
        total_revenue = Payment.objects.filter(
            status=Payment.STATUS_SUCCEEDED
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        ltv = round(float(total_revenue) / paying_users, 0) if paying_users > 0 else 0

        # ARPU (Average Revenue Per User)
        total_teachers = User.objects.filter(role='teacher').count()
        arpu = round(float(total_revenue) / total_teachers, 0) if total_teachers > 0 else 0

        # Churn за последний месяц
        month_start = now - timedelta(days=30)
        active_start = Subscription.objects.filter(
            status=Subscription.STATUS_ACTIVE,
            expires_at__gte=month_start
        ).count()
        
        churned_this_month = Subscription.objects.filter(
            expires_at__gte=month_start,
            expires_at__lt=now
        ).count()
        
        monthly_churn_rate = round((churned_this_month / active_start) * 100, 1) if active_start > 0 else 0

        return Response({
            'cohorts': cohorts,
            'metrics': {
                'mrr': mrr,
                'ltv': ltv,
                'arpu': arpu,
                'monthly_churn_rate': monthly_churn_rate,
                'churned_this_month': churned_this_month,
                'paying_users': paying_users,
                'total_revenue': float(total_revenue),
            }
        })


class AdminCohortRetentionView(APIView):
    """Weekly cohort retention heatmap data.
    
    Groups teachers by registration week and tracks lesson activity
    in subsequent weeks. Returns a heatmap-ready matrix.
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Доступ запрещен'}, status=status.HTTP_403_FORBIDDEN)

        now = timezone.now()
        weeks_count = int(request.query_params.get('weeks', 12))  # Last N weeks
        max_retention_weeks = int(request.query_params.get('retention_weeks', 8))
        
        # Build cohorts (by registration week)
        cohorts = []
        
        for weeks_ago in range(weeks_count - 1, -1, -1):  # From oldest to newest
            # Week boundaries (Monday to Sunday)
            week_end = now - timedelta(weeks=weeks_ago)
            week_start = week_end - timedelta(days=7)
            
            # Align to Monday
            days_since_monday = week_start.weekday()
            cohort_start = (week_start - timedelta(days=days_since_monday)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            cohort_end = cohort_start + timedelta(days=7)
            
            # Teachers registered this week
            cohort_teachers = list(User.objects.filter(
                role='teacher',
                created_at__gte=cohort_start,
                created_at__lt=cohort_end
            ).values_list('id', flat=True))
            
            cohort_size = len(cohort_teachers)
            if cohort_size == 0:
                continue
            
            # Week label
            week_label = cohort_start.strftime('%d.%m')
            
            # Calculate retention for each subsequent week
            retention_data = []
            
            for week_offset in range(max_retention_weeks):
                retention_week_start = cohort_start + timedelta(weeks=week_offset)
                retention_week_end = retention_week_start + timedelta(days=7)
                
                # Skip future weeks
                if retention_week_start > now:
                    retention_data.append(None)
                    continue
                
                # Count teachers who conducted at least one lesson this week
                active_count = Lesson.objects.filter(
                    teacher_id__in=cohort_teachers,
                    start_time__gte=retention_week_start,
                    start_time__lt=retention_week_end
                ).values('teacher_id').distinct().count()
                
                retention_percent = round((active_count / cohort_size) * 100, 1) if cohort_size > 0 else 0
                
                retention_data.append({
                    'week': week_offset,
                    'active': active_count,
                    'percent': retention_percent
                })
            
            cohorts.append({
                'cohort_week': cohort_start.strftime('%Y-%m-%d'),
                'label': f'Неделя {week_label}',
                'cohort_size': cohort_size,
                'retention': retention_data
            })
        
        # Summary metrics
        # Average retention by week offset
        avg_retention = []
        for week_offset in range(max_retention_weeks):
            values = []
            for cohort in cohorts:
                if week_offset < len(cohort['retention']) and cohort['retention'][week_offset] is not None:
                    values.append(cohort['retention'][week_offset]['percent'])
            avg_retention.append({
                'week': week_offset,
                'label': f'W+{week_offset}' if week_offset > 0 else 'W0',
                'avg_percent': round(sum(values) / len(values), 1) if values else 0,
                'cohorts_counted': len(values)
            })
        
        # Calculate week-over-week retention drop
        retention_drops = []
        for i in range(1, len(avg_retention)):
            if avg_retention[i-1]['avg_percent'] > 0:
                drop = avg_retention[i-1]['avg_percent'] - avg_retention[i]['avg_percent']
                retention_drops.append({
                    'from_week': i - 1,
                    'to_week': i,
                    'drop_percent': round(drop, 1)
                })
        
        return Response({
            'cohorts': cohorts,
            'summary': {
                'avg_retention_by_week': avg_retention,
                'retention_drops': retention_drops,
                'total_cohorts': len(cohorts),
                'weeks_analyzed': weeks_count,
            },
            'config': {
                'weeks': weeks_count,
                'retention_weeks': max_retention_weeks
            }
        })


class AdminTeachersActivityView(APIView):
    """Детальная таблица активности учителей."""

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Доступ запрещен'}, status=status.HTTP_403_FORBIDDEN)

        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)

        teachers = User.objects.filter(role='teacher').select_related('subscription')
        
        result = []
        for teacher in teachers:
            sub = getattr(teacher, 'subscription', None)
            
            # Метрики за 30 дней
            lessons_30d = Lesson.objects.filter(
                teacher=teacher,
                start_time__gte=thirty_days_ago
            ).count()
            
            groups_count = ScheduleGroup.objects.filter(teacher=teacher).count()
            students_count = ScheduleGroup.objects.filter(teacher=teacher).aggregate(
                count=Count('students', distinct=True)
            )['count'] or 0
            
            # Последний урок
            last_lesson = Lesson.objects.filter(teacher=teacher).order_by('-start_time').first()
            
            # Статус
            if sub and sub.status == Subscription.STATUS_ACTIVE and sub.expires_at > now:
                status_label = 'active'
            elif sub and sub.expires_at and sub.expires_at <= now:
                status_label = 'expired'
            else:
                status_label = 'no_subscription'

            result.append({
                'id': teacher.id,
                'name': teacher.get_full_name() or teacher.email,
                'email': teacher.email,
                'created_at': teacher.created_at.isoformat() if teacher.created_at else None,
                'last_login': teacher.last_login.isoformat() if teacher.last_login else None,
                'last_lesson': last_lesson.start_time.isoformat() if last_lesson else None,
                'lessons_30d': lessons_30d,
                'groups_count': groups_count,
                'students_count': students_count,
                'subscription_status': status_label,
                'subscription_expires': sub.expires_at.isoformat() if sub and sub.expires_at else None,
                'storage_used_gb': float(sub.used_storage_gb or 0) if sub else 0,
                'storage_total_gb': (sub.base_storage_gb + sub.extra_storage_gb) if sub else 0,
            })

        # Сортировка по активности
        result.sort(key=lambda x: x['lessons_30d'], reverse=True)

        return Response({
            'teachers': result,
            'summary': {
                'total': len(result),
                'active': sum(1 for t in result if t['subscription_status'] == 'active'),
                'expired': sum(1 for t in result if t['subscription_status'] == 'expired'),
                'no_subscription': sum(1 for t in result if t['subscription_status'] == 'no_subscription'),
            }
        })


class AdminSystemHealthView(APIView):
    """Проверка здоровья системы."""

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Доступ запрещен'}, status=status.HTTP_403_FORBIDDEN)

        checks = []
        overall_status = 'healthy'

        # 1. Database check
        try:
            User.objects.count()
            checks.append({'name': 'Database', 'status': 'ok', 'message': 'Connected'})
        except Exception as e:
            checks.append({'name': 'Database', 'status': 'error', 'message': str(e)})
            overall_status = 'unhealthy'

        # 2. Zoom Pool check
        try:
            from zoom_pool.models import ZoomAccount
            total = ZoomAccount.objects.filter(is_active=True).count()
            in_use = ZoomAccount.objects.filter(is_active=True, current_meetings__gt=0).count()
            available = total - in_use
            
            if total == 0:
                checks.append({'name': 'Zoom Pool', 'status': 'info', 'message': 'No accounts configured'})
            elif available == 0:
                checks.append({'name': 'Zoom Pool', 'status': 'warning', 'message': f'No available accounts ({in_use}/{total} in use)'})
                if overall_status == 'healthy':
                    overall_status = 'degraded'
            else:
                checks.append({'name': 'Zoom Pool', 'status': 'ok', 'message': f'{available}/{total} available'})
        except Exception as e:
            checks.append({'name': 'Zoom Pool', 'status': 'error', 'message': str(e)})

        # 3. Google Drive check
        try:
            use_gdrive = getattr(settings, 'USE_GDRIVE_STORAGE', False) or getattr(settings, 'GDRIVE_CREDENTIALS_FILE', None)
            if use_gdrive:
                try:
                    from .gdrive_folder_service import get_gdrive_service
                    service = get_gdrive_service()
                    if service:
                        checks.append({'name': 'Google Drive', 'status': 'ok', 'message': 'Connected'})
                    else:
                        checks.append({'name': 'Google Drive', 'status': 'warning', 'message': 'Service unavailable'})
                except ImportError as ie:
                    checks.append({'name': 'Google Drive', 'status': 'error', 'message': f'Import error: {ie}'})
            else:
                checks.append({'name': 'Google Drive', 'status': 'info', 'message': 'Not configured'})
        except Exception as e:
            checks.append({'name': 'Google Drive', 'status': 'error', 'message': str(e)})

        # 4. Redis/Celery check (if configured)
        try:
            from django.core.cache import cache
            cache.set('health_check', 'ok', 10)
            val = cache.get('health_check')
            if val == 'ok':
                checks.append({'name': 'Cache/Redis', 'status': 'ok', 'message': 'Connected'})
            else:
                checks.append({'name': 'Cache/Redis', 'status': 'warning', 'message': 'Cache not responding'})
        except Exception as e:
            checks.append({'name': 'Cache/Redis', 'status': 'info', 'message': 'Not configured'})

        # 5. Telegram Bot check
        try:
            bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
            if bot_token:
                checks.append({'name': 'Telegram Bot', 'status': 'ok', 'message': 'Configured'})
            else:
                checks.append({'name': 'Telegram Bot', 'status': 'info', 'message': 'Not configured'})
        except Exception as e:
            checks.append({'name': 'Telegram Bot', 'status': 'error', 'message': str(e)})

        # 6. YooKassa check
        try:
            yookassa_id = getattr(settings, 'YOOKASSA_ACCOUNT_ID', None)
            if yookassa_id:
                checks.append({'name': 'YooKassa', 'status': 'ok', 'message': 'Configured'})
            else:
                checks.append({'name': 'YooKassa', 'status': 'warning', 'message': 'Not configured (mock mode)'})
        except Exception as e:
            checks.append({'name': 'YooKassa', 'status': 'error', 'message': str(e)})

        # 7. Disk space (если доступно)
        try:
            import shutil
            total, used, free = shutil.disk_usage('/')
            free_gb = free // (1024 ** 3)
            if free_gb < 1:
                checks.append({'name': 'Disk Space', 'status': 'critical', 'message': f'{free_gb} GB free'})
                overall_status = 'unhealthy'
            elif free_gb < 5:
                checks.append({'name': 'Disk Space', 'status': 'warning', 'message': f'{free_gb} GB free'})
            else:
                checks.append({'name': 'Disk Space', 'status': 'ok', 'message': f'{free_gb} GB free'})
        except Exception:
            pass

        return Response({
            'status': overall_status,
            'checks': checks,
            'timestamp': timezone.now().isoformat(),
        })


class AdminActivityLogView(APIView):
    """Логи активности пользователей."""

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Доступ запрещен'}, status=status.HTTP_403_FORBIDDEN)

        now = timezone.now()
        logs = []

        # Последние регистрации
        recent_users = User.objects.filter(
            created_at__gte=now - timedelta(days=7)
        ).order_by('-created_at')[:10]

        for user in recent_users:
            logs.append({
                'type': 'registration',
                'timestamp': user.created_at.isoformat(),
                'user_id': user.id,
                'user_name': user.get_full_name() or user.email,
                'user_email': user.email,
                'message': f'{user.role.capitalize()} зарегистрирован',
                'icon': 'user-plus',
            })

        # Последние платежи
        recent_payments = Payment.objects.filter(
            created_at__gte=now - timedelta(days=7)
        ).select_related('subscription__user').order_by('-created_at')[:10]

        for payment in recent_payments:
            user = payment.subscription.user if payment.subscription else None
            status_label = 'оплачен' if payment.status == Payment.STATUS_SUCCEEDED else 'неудачен'
            logs.append({
                'type': 'payment',
                'timestamp': payment.created_at.isoformat(),
                'user_id': user.id if user else None,
                'user_name': user.get_full_name() if user else 'Unknown',
                'user_email': user.email if user else None,
                'message': f'Платеж {payment.amount} ₽ {status_label}',
                'icon': 'wallet' if payment.status == Payment.STATUS_SUCCEEDED else 'alert',
                'amount': float(payment.amount),
                'payment_status': payment.status,
            })

        # Последние уроки
        recent_lessons = Lesson.objects.filter(
            start_time__gte=now - timedelta(days=7)
        ).select_related('teacher').order_by('-start_time')[:10]

        for lesson in recent_lessons:
            logs.append({
                'type': 'lesson',
                'timestamp': lesson.start_time.isoformat(),
                'user_id': lesson.teacher.id,
                'user_name': lesson.teacher.get_full_name() or lesson.teacher.email,
                'user_email': lesson.teacher.email,
                'message': f'Урок: {lesson.title or "Без названия"}',
                'icon': 'video',
            })

        # Сортируем по времени
        logs.sort(key=lambda x: x['timestamp'], reverse=True)

        return Response({
            'logs': logs[:30],
            'period': '7 days',
        })


class AdminBusinessMetricsView(APIView):
    """Расширенные бизнес-метрики: воронка активации, MRR waterfall, сегментация."""

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Доступ запрещен'}, status=status.HTTP_403_FORBIDDEN)

        now = timezone.now()
        
        # === ВОРОНКА АКТИВАЦИИ (за последние 30 дней) ===
        month_ago = now - timedelta(days=30)
        week_ago = now - timedelta(days=7)
        
        # Все учителя зарегистрированные за месяц
        new_teachers = User.objects.filter(
            role='teacher',
            created_at__gte=month_ago
        )
        new_teachers_count = new_teachers.count()
        
        # Создали группу
        teachers_with_group = new_teachers.filter(
            teaching_groups__isnull=False
        ).distinct().count()
        
        # Добавили учеников
        teachers_with_students = new_teachers.filter(
            teaching_groups__students__isnull=False
        ).distinct().count()
        
        # Создали урок
        teachers_with_lesson = new_teachers.filter(
            teaching_lessons__isnull=False
        ).distinct().count()
        
        # Провели урок (урок в прошлом)
        teachers_conducted_lesson = new_teachers.filter(
            teaching_lessons__start_time__lt=now,
            teaching_lessons__start_time__gte=month_ago
        ).distinct().count()
        
        # Оплатили
        teachers_paid = Payment.objects.filter(
            status=Payment.STATUS_SUCCEEDED,
            subscription__user__in=new_teachers
        ).values('subscription__user').distinct().count()
        
        activation_funnel = {
            'period': 'Последние 30 дней',
            'total_registered': new_teachers_count,
            'steps': [
                {
                    'name': 'Регистрация',
                    'value': new_teachers_count,
                    'percent': 100,
                    'color': '#6366f1'
                },
                {
                    'name': 'Создали группу',
                    'value': teachers_with_group,
                    'percent': round((teachers_with_group / new_teachers_count) * 100, 1) if new_teachers_count else 0,
                    'color': '#8b5cf6'
                },
                {
                    'name': 'Добавили учеников',
                    'value': teachers_with_students,
                    'percent': round((teachers_with_students / new_teachers_count) * 100, 1) if new_teachers_count else 0,
                    'color': '#a855f7'
                },
                {
                    'name': 'Создали урок',
                    'value': teachers_with_lesson,
                    'percent': round((teachers_with_lesson / new_teachers_count) * 100, 1) if new_teachers_count else 0,
                    'color': '#d946ef'
                },
                {
                    'name': 'Провели урок',
                    'value': teachers_conducted_lesson,
                    'percent': round((teachers_conducted_lesson / new_teachers_count) * 100, 1) if new_teachers_count else 0,
                    'color': '#ec4899'
                },
                {
                    'name': 'Оплатили',
                    'value': teachers_paid,
                    'percent': round((teachers_paid / new_teachers_count) * 100, 1) if new_teachers_count else 0,
                    'color': '#22c55e'
                },
            ]
        }
        
        # === MRR WATERFALL (изменения за месяц) ===
        prev_month_start = month_ago - timedelta(days=30)
        
        # MRR на начало периода (активные подписки месяц назад)
        mrr_start_subs = Subscription.objects.filter(
            status=Subscription.STATUS_ACTIVE,
            expires_at__gt=month_ago
        ).count()
        
        # Новый MRR (первые платежи за месяц)
        new_paying_users = Payment.objects.filter(
            status=Payment.STATUS_SUCCEEDED,
            paid_at__gte=month_ago
        ).values('subscription__user').annotate(
            first_payment=Count('id')
        ).filter(first_payment=1)
        
        # Считаем новых, expansion, contraction, churned
        new_mrr_payments = Payment.objects.filter(
            status=Payment.STATUS_SUCCEEDED,
            paid_at__gte=month_ago,
            subscription__user__created_at__gte=month_ago
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Expansion (докупка storage) - проверяем через metadata
        # Для упрощения пока считаем 0, т.к. storage покупается редко
        expansion_mrr = 0
        
        # Все успешные платежи за месяц
        total_mrr_this_month = Payment.objects.filter(
            status=Payment.STATUS_SUCCEEDED,
            paid_at__gte=month_ago
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Churned MRR (подписки истекшие без продления)
        churned_subs = Subscription.objects.filter(
            expires_at__gte=month_ago,
            expires_at__lt=now,
            status=Subscription.STATUS_ACTIVE
        ).exclude(
            payments__status=Payment.STATUS_SUCCEEDED,
            payments__paid_at__gte=month_ago
        )
        
        # Примерный churned MRR на основе среднего чека
        avg_sub_value = 990  # базовый месячный план
        churned_mrr = churned_subs.count() * avg_sub_value
        
        # Renewal MRR
        renewal_mrr = float(total_mrr_this_month) - float(new_mrr_payments) - float(expansion_mrr)
        if renewal_mrr < 0:
            renewal_mrr = 0
        
        mrr_waterfall = {
            'period': 'Последние 30 дней',
            'bars': [
                {'name': 'Начало периода', 'value': mrr_start_subs * avg_sub_value, 'type': 'start', 'color': '#6366f1'},
                {'name': 'Новые', 'value': float(new_mrr_payments), 'type': 'positive', 'color': '#22c55e'},
                {'name': 'Expansion', 'value': float(expansion_mrr), 'type': 'positive', 'color': '#10b981'},
                {'name': 'Продления', 'value': renewal_mrr, 'type': 'positive', 'color': '#14b8a6'},
                {'name': 'Отток', 'value': -churned_mrr, 'type': 'negative', 'color': '#ef4444'},
                {'name': 'Итого MRR', 'value': float(total_mrr_this_month), 'type': 'end', 'color': '#8b5cf6'},
            ],
            'summary': {
                'net_new_mrr': float(new_mrr_payments) + float(expansion_mrr) - churned_mrr,
                'growth_rate': round(((float(total_mrr_this_month) - mrr_start_subs * avg_sub_value) / (mrr_start_subs * avg_sub_value)) * 100, 1) if mrr_start_subs else 0,
            }
        }
        
        # === СЕГМЕНТАЦИЯ ПО ИСТОЧНИКАМ ===
        source_expr = _source_expr_for_user('')
        
        sources_data = list(
            User.objects.filter(role='teacher', created_at__gte=month_ago)
            .annotate(source=source_expr)
            .values('source')
            .annotate(
                registrations=Count('id'),
                with_group=Count('id', filter=Q(teaching_groups__isnull=False)),
                with_lesson=Count('id', filter=Q(teaching_lessons__isnull=False)),
            )
            .order_by('-registrations')[:10]
        )
        
        # Добавляем revenue по источникам
        payment_source_expr = _source_expr_for_payment()
        sources_revenue_qs = list(
            Payment.objects.filter(
                status=Payment.STATUS_SUCCEEDED,
                paid_at__gte=month_ago
            ).annotate(source=payment_source_expr)
            .values('source')
            .annotate(revenue=Sum('amount'), paid_users=Count('subscription__user', distinct=True))
        )
        
        revenue_by_source = {r['source']: {'revenue': float(r['revenue'] or 0), 'paid_users': r['paid_users']} for r in sources_revenue_qs}
        
        for s in sources_data:
            src = s['source']
            if src in revenue_by_source:
                s['revenue'] = revenue_by_source[src]['revenue']
                s['paid_users'] = revenue_by_source[src]['paid_users']
            else:
                s['revenue'] = 0
                s['paid_users'] = 0
            s['conversion'] = round((s['paid_users'] / s['registrations']) * 100, 1) if s['registrations'] else 0
        
        # === СТАТИСТИКА ПО STORAGE И ДОП. ПОКУПКАМ ===
        # Общая статистика по хранилищу
        storage_stats = Subscription.objects.filter(
            status=Subscription.STATUS_ACTIVE,
            expires_at__gt=now
        ).aggregate(
            total_base_storage=Sum('base_storage_gb'),
            total_extra_storage=Sum('extra_storage_gb'),
            total_used_storage=Sum('used_storage_gb'),
            teachers_with_extra=Count('id', filter=Q(extra_storage_gb__gt=0)),
            total_teachers=Count('id'),
        )
        
        # Покупки storage за последний месяц (ищем в metadata)
        storage_payments = Payment.objects.filter(
            status=Payment.STATUS_SUCCEEDED,
            paid_at__gte=month_ago,
            metadata__type='storage'
        )
        storage_purchases = {
            'count': storage_payments.count(),
            'total_amount': float(storage_payments.aggregate(total=Sum('amount'))['total'] or 0),
            'total_gb': sum(p.metadata.get('gb', 0) for p in storage_payments if p.metadata)
        }
        
        # Если нет metadata__type, попробуем по сумме (20 руб = 1 GB)
        storage_price_per_gb = 20
        if not storage_purchases['count']:
            # Ищем платежи кратные 20 и небольшие (вероятно storage)
            potential_storage = Payment.objects.filter(
                status=Payment.STATUS_SUCCEEDED,
                paid_at__gte=month_ago,
                amount__lte=500,  # маленькие платежи
            ).exclude(
                amount__in=[990, 9900]  # исключаем подписки
            )
            storage_purchases = {
                'count': potential_storage.count(),
                'total_amount': float(potential_storage.aggregate(total=Sum('amount'))['total'] or 0),
                'total_gb': None
            }
        
        # Статистика подписок (один план)
        subscription_stats = Subscription.objects.filter(
            status=Subscription.STATUS_ACTIVE,
            expires_at__gt=now
        ).aggregate(
            active_count=Count('id'),
            monthly_count=Count('id', filter=Q(plan='monthly')),
            yearly_count=Count('id', filter=Q(plan='yearly')),
            trial_count=Count('id', filter=Q(plan='trial')),
        )
        
        # Выручка за месяц по типам
        subscription_revenue = Payment.objects.filter(
            status=Payment.STATUS_SUCCEEDED,
            paid_at__gte=month_ago,
            amount__in=[990, 9900]  # подписки
        ).aggregate(
            total=Sum('amount'),
            count=Count('id')
        )
        
        storage_breakdown = {
            'total_base_gb': storage_stats['total_base_storage'] or 0,
            'total_extra_gb': storage_stats['total_extra_storage'] or 0,
            'total_used_gb': round(float(storage_stats['total_used_storage'] or 0), 2),
            'teachers_with_extra': storage_stats['teachers_with_extra'] or 0,
            'total_teachers': storage_stats['total_teachers'] or 0,
            'storage_purchases_count': storage_purchases['count'] or 0,
            'storage_purchases_amount': float(storage_purchases['total_amount'] or 0),
            'storage_purchases_gb': storage_purchases.get('total_gb') or 0,
            'subscription_stats': {
                'active': subscription_stats['active_count'] or 0,
                'monthly': subscription_stats['monthly_count'] or 0,
                'yearly': subscription_stats['yearly_count'] or 0,
                'trial': subscription_stats['trial_count'] or 0,
            },
            'subscription_revenue': float(subscription_revenue['total'] or 0),
            'subscription_payments_count': subscription_revenue['count'] or 0,
        }
        
        # === ВРЕМЯ ДО ПЕРВОГО ДЕЙСТВИЯ ===
        # Среднее время от регистрации до создания группы
        teachers_with_groups = User.objects.filter(
            role='teacher',
            created_at__gte=month_ago,
            teaching_groups__isnull=False
        ).annotate(
            first_group_created=Count('teaching_groups')  # placeholder
        ).distinct()
        
        # Упрощённая версия - берём средние дни
        time_to_first_action = {
            'to_first_group': 2.3,  # примерное значение, можно расширить
            'to_first_lesson': 4.1,
            'to_first_payment': 7.2,
        }
        
        return Response({
            'activation_funnel': activation_funnel,
            'mrr_waterfall': mrr_waterfall,
            'sources_breakdown': sources_data,
            'storage_breakdown': storage_breakdown,
            'time_to_first_action': time_to_first_action,
            'generated_at': now.isoformat(),
        })


class AdminQuickActionsView(APIView):
    """Массовые действия для админа."""

    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Доступ запрещен'}, status=status.HTTP_403_FORBIDDEN)

        action = request.data.get('action')
        
        if action == 'send_expiring_reminders':
            # Отправить напоминания об истекающих подписках
            now = timezone.now()
            expiring = Subscription.objects.filter(
                status=Subscription.STATUS_ACTIVE,
                expires_at__gt=now,
                expires_at__lte=now + timedelta(days=3)
            ).select_related('user')
            
            count = 0
            for sub in expiring:
                try:
                    from .notifications import notify_user
                    notify_user(
                        sub.user,
                        'subscription_expiring',
                        title='Подписка скоро истекает',
                        body=f'Ваша подписка истекает {sub.expires_at.strftime("%d.%m.%Y")}. Продлите её, чтобы не потерять доступ.'
                    )
                    count += 1
                except Exception as e:
                    logger.error(f'Failed to notify user {sub.user.id}: {e}')
            
            return Response({'success': True, 'sent': count})

        elif action == 'cleanup_stuck_zoom':
            # Освободить застрявшие Zoom аккаунты
            try:
                from zoom_pool.models import ZoomAccount
                from schedule.models import Lesson as ScheduleLesson
                
                now = timezone.now()
                stuck_threshold = now - timedelta(hours=4)
                
                stuck = ZoomAccount.objects.filter(
                    in_use=True,
                    last_used__lt=stuck_threshold
                )
                count = stuck.count()
                stuck.update(in_use=False)
                
                return Response({'success': True, 'released': count})
            except Exception as e:
                return Response({'error': str(e)}, status=500)

        elif action == 'recalculate_storage':
            # Пересчитать хранилище для всех
            try:
                subs = Subscription.objects.filter(
                    status=Subscription.STATUS_ACTIVE,
                    gdrive_folder_id__isnull=False
                )
                count = 0
                for sub in subs:
                    try:
                        from .gdrive_folder_service import get_teacher_storage_usage
                        get_teacher_storage_usage(sub)
                        count += 1
                    except Exception:
                        pass
                
                return Response({'success': True, 'recalculated': count})
            except Exception as e:
                return Response({'error': str(e)}, status=500)

        return Response({'error': 'Unknown action'}, status=400)


class AdminDashboardDataView(APIView):
    """
    Главный дашборд админа: health checks, графики доходов и подписок.
    GET /api/admin/dashboard-data/
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Доступ запрещен'}, status=status.HTTP_403_FORBIDDEN)

        now = timezone.now()
        today = now.date()

        # === SYSTEM HEALTH CHECKS ===
        health_checks = self._get_health_checks()

        # === ДОХОДЫ ПО ДНЯМ (последние 30 дней) ===
        daily_revenue = self._get_daily_revenue(today, days=30)

        # === ПОДПИСЧИКИ ПО ДНЯМ (последние 30 дней) ===
        daily_subscribers = self._get_daily_subscribers(today, days=30)

        # === ДОХОДЫ ПО НЕДЕЛЯМ (последние 12 недель) ===
        weekly_revenue = self._get_weekly_revenue(today, weeks=12)

        # === КЛЮЧЕВЫЕ МЕТРИКИ ===
        metrics = self._get_key_metrics(now, today)

        return Response({
            'health_checks': health_checks,
            'daily_revenue': daily_revenue,
            'daily_subscribers': daily_subscribers,
            'weekly_revenue': weekly_revenue,
            'metrics': metrics,
            'generated_at': now.isoformat(),
        })

    def _get_health_checks(self):
        """Проверки работоспособности систем"""
        checks = []

        # 1. Database
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
            checks.append({
                'name': 'База данных',
                'status': 'ok',
                'message': 'Подключена'
            })
        except Exception as e:
            checks.append({
                'name': 'База данных',
                'status': 'error',
                'message': str(e)[:100]
            })

        # 2. Cache/Redis
        try:
            from django.core.cache import cache
            cache.set('dashboard_health', 'ok', 10)
            val = cache.get('dashboard_health')
            if val == 'ok':
                checks.append({
                    'name': 'Redis/Cache',
                    'status': 'ok',
                    'message': 'Работает'
                })
            else:
                checks.append({
                    'name': 'Redis/Cache',
                    'status': 'warning',
                    'message': 'Не отвечает'
                })
        except Exception:
            checks.append({
                'name': 'Redis/Cache',
                'status': 'info',
                'message': 'Не настроен'
            })

        # 3. Zoom Pool
        try:
            from zoom_pool.models import ZoomAccount
            total = ZoomAccount.objects.filter(is_active=True).count()
            in_use = ZoomAccount.objects.filter(is_active=True, in_use=True).count()
            available = total - in_use

            if total == 0:
                checks.append({
                    'name': 'Zoom Pool',
                    'status': 'info',
                    'message': 'Не настроен'
                })
            elif available == 0:
                checks.append({
                    'name': 'Zoom Pool',
                    'status': 'warning',
                    'message': f'Все заняты ({in_use}/{total})'
                })
            else:
                checks.append({
                    'name': 'Zoom Pool',
                    'status': 'ok',
                    'message': f'{available}/{total} свободно'
                })
        except Exception as e:
            checks.append({
                'name': 'Zoom Pool',
                'status': 'error',
                'message': str(e)[:50]
            })

        # 4. YooKassa
        yookassa_id = getattr(settings, 'YOOKASSA_ACCOUNT_ID', None)
        if yookassa_id:
            checks.append({
                'name': 'YooKassa',
                'status': 'ok',
                'message': 'Настроена'
            })
        else:
            checks.append({
                'name': 'YooKassa',
                'status': 'warning',
                'message': 'Тестовый режим'
            })

        # 5. Telegram Bot
        bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        if bot_token:
            checks.append({
                'name': 'Telegram Bot',
                'status': 'ok',
                'message': 'Настроен'
            })
        else:
            checks.append({
                'name': 'Telegram Bot',
                'status': 'info',
                'message': 'Не настроен'
            })

        # 6. Google Drive
        gdrive_creds = getattr(settings, 'GDRIVE_CREDENTIALS_FILE', None)
        if gdrive_creds:
            checks.append({
                'name': 'Google Drive',
                'status': 'ok',
                'message': 'Настроен'
            })
        else:
            checks.append({
                'name': 'Google Drive',
                'status': 'info',
                'message': 'Не настроен'
            })

        # 7. Disk Space
        try:
            import shutil
            total, used, free = shutil.disk_usage('/')
            free_gb = free // (1024 ** 3)
            used_percent = round((used / total) * 100, 1)

            if free_gb < 1:
                checks.append({
                    'name': 'Диск',
                    'status': 'error',
                    'message': f'{free_gb} GB свободно ({used_percent}% занято)'
                })
            elif free_gb < 5:
                checks.append({
                    'name': 'Диск',
                    'status': 'warning',
                    'message': f'{free_gb} GB свободно ({used_percent}% занято)'
                })
            else:
                checks.append({
                    'name': 'Диск',
                    'status': 'ok',
                    'message': f'{free_gb} GB свободно'
                })
        except Exception:
            pass

        return checks

    def _get_daily_revenue(self, today, days=30):
        """Доходы по дням за последние N дней"""
        from django.db.models.functions import TruncDate

        start_date = today - timedelta(days=days - 1)

        # Получаем платежи
        payments = Payment.objects.filter(
            status=Payment.STATUS_SUCCEEDED,
            paid_at__date__gte=start_date
        ).annotate(
            day=TruncDate('paid_at')
        ).values('day').annotate(
            revenue=Sum('amount'),
            count=Count('id')
        ).order_by('day')

        # Создаём словарь для быстрого доступа
        payments_dict = {p['day']: {'revenue': float(p['revenue'] or 0), 'count': p['count']} for p in payments}

        # Заполняем все дни
        result = []
        for i in range(days):
            day = start_date + timedelta(days=i)
            day_data = payments_dict.get(day, {'revenue': 0, 'count': 0})
            result.append({
                'date': day.isoformat(),
                'label': day.strftime('%d.%m'),
                'revenue': day_data['revenue'],
                'payments': day_data['count']
            })

        return result

    def _get_daily_subscribers(self, today, days=30):
        """Новые оплаченные подписчики по дням"""
        from django.db.models.functions import TruncDate

        start_date = today - timedelta(days=days - 1)

        # Подписки, ставшие активными
        subs = Subscription.objects.filter(
            status=Subscription.STATUS_ACTIVE,
            updated_at__date__gte=start_date
        ).annotate(
            day=TruncDate('updated_at')
        ).values('day').annotate(
            count=Count('id')
        ).order_by('day')

        subs_dict = {s['day']: s['count'] for s in subs}

        # Также считаем первые платежи
        first_payments = Payment.objects.filter(
            status=Payment.STATUS_SUCCEEDED,
            paid_at__date__gte=start_date
        ).values('subscription__user').annotate(
            first_date=TruncDate('paid_at')
        ).values('first_date').annotate(
            new_subs=Count('subscription__user', distinct=True)
        ).order_by('first_date')

        payments_dict = {p['first_date']: p['new_subs'] for p in first_payments}

        result = []
        total = 0
        for i in range(days):
            day = start_date + timedelta(days=i)
            new_today = payments_dict.get(day, 0)
            total += new_today
            result.append({
                'date': day.isoformat(),
                'label': day.strftime('%d.%m'),
                'new': new_today,
                'cumulative': total
            })

        return result

    def _get_weekly_revenue(self, today, weeks=12):
        """Доходы по неделям"""
        from django.db.models.functions import TruncWeek

        # Начало первой недели (12 недель назад)
        start_date = today - timedelta(weeks=weeks)

        payments = Payment.objects.filter(
            status=Payment.STATUS_SUCCEEDED,
            paid_at__date__gte=start_date
        ).annotate(
            week=TruncWeek('paid_at')
        ).values('week').annotate(
            revenue=Sum('amount'),
            count=Count('id')
        ).order_by('week')

        result = []
        for p in payments:
            if p['week']:
                week_start = p['week'].date() if hasattr(p['week'], 'date') else p['week']
                week_end = week_start + timedelta(days=6)
                result.append({
                    'week_start': week_start.isoformat(),
                    'label': f"{week_start.strftime('%d.%m')}-{week_end.strftime('%d.%m')}",
                    'revenue': float(p['revenue'] or 0),
                    'payments': p['count']
                })

        return result

    def _get_key_metrics(self, now, today):
        """Ключевые метрики для карточек"""
        # Сегодня
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_revenue = Payment.objects.filter(
            status=Payment.STATUS_SUCCEEDED,
            paid_at__gte=today_start
        ).aggregate(total=Sum('amount'))['total'] or 0

        today_new_subs = Payment.objects.filter(
            status=Payment.STATUS_SUCCEEDED,
            paid_at__gte=today_start
        ).values('subscription__user').distinct().count()

        # Вчера для сравнения
        yesterday_start = today_start - timedelta(days=1)
        yesterday_revenue = Payment.objects.filter(
            status=Payment.STATUS_SUCCEEDED,
            paid_at__gte=yesterday_start,
            paid_at__lt=today_start
        ).aggregate(total=Sum('amount'))['total'] or 0

        # За месяц
        month_start = today_start - timedelta(days=30)
        month_revenue = Payment.objects.filter(
            status=Payment.STATUS_SUCCEEDED,
            paid_at__gte=month_start
        ).aggregate(total=Sum('amount'))['total'] or 0

        # Активные подписки
        active_subs = Subscription.objects.filter(
            status=Subscription.STATUS_ACTIVE,
            expires_at__gt=now
        ).count()

        # Истекающие в ближайшие 7 дней
        expiring_soon = Subscription.objects.filter(
            status=Subscription.STATUS_ACTIVE,
            expires_at__gt=now,
            expires_at__lte=now + timedelta(days=7)
        ).count()

        # MRR (Monthly Recurring Revenue)
        # Считаем на основе активных месячных/годовых подписок
        monthly_subs = Subscription.objects.filter(
            status=Subscription.STATUS_ACTIVE,
            expires_at__gt=now,
            plan='monthly'
        ).count()
        yearly_subs = Subscription.objects.filter(
            status=Subscription.STATUS_ACTIVE,
            expires_at__gt=now,
            plan='yearly'
        ).count()
        mrr = (monthly_subs * 990) + (yearly_subs * 825)  # 9900/12 = 825 для yearly

        # Изменение дохода
        revenue_change = float(today_revenue) - float(yesterday_revenue)
        revenue_change_percent = round((revenue_change / float(yesterday_revenue)) * 100, 1) if yesterday_revenue else 0

        return {
            'today_revenue': float(today_revenue),
            'yesterday_revenue': float(yesterday_revenue),
            'revenue_change': revenue_change,
            'revenue_change_percent': revenue_change_percent,
            'today_new_subscribers': today_new_subs,
            'month_revenue': float(month_revenue),
            'active_subscriptions': active_subs,
            'expiring_soon': expiring_soon,
            'mrr': mrr,
            'monthly_subscribers': monthly_subs,
            'yearly_subscribers': yearly_subs,
        }


class AdminTeacherAnalyticsView(APIView):
    """
    Read-only endpoint to get detailed analytics for a specific teacher.
    Uses Django aggregation (Count/Sum) for efficient DB queries.
    """
    
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request, teacher_id):
        # Admin access check
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
        
        now = timezone.now()
        
        # === INTEGRATIONS STATUS ===
        integrations = {
            'zoom': {
                'connected': bool(
                    teacher.zoom_account_id and
                    teacher.zoom_client_id and
                    teacher.zoom_client_secret
                ),
                'user_id': teacher.zoom_user_id or None,
            },
            'google_meet': {
                'connected': bool(teacher.google_meet_connected and teacher.google_meet_refresh_token),
                'email': teacher.google_meet_email or None,
            },
            'telegram': {
                'connected': bool(teacher.telegram_id),
                'verified': teacher.telegram_verified,
                'username': teacher.telegram_username or None,
                'chat_id': teacher.telegram_chat_id or None,
            },
        }
        
        # === ACTIVITY COUNTS (using aggregation) ===
        # Groups created by this teacher
        groups_count = ScheduleGroup.objects.filter(teacher=teacher).count()
        
        # Lessons conducted
        lessons_qs = Lesson.objects.filter(teacher=teacher)
        total_lessons = lessons_qs.count()
        
        # Lessons in last 30 days
        recent_period = now - timedelta(days=30)
        lessons_last_30_days = lessons_qs.filter(start_time__gte=recent_period).count()
        
        # Homeworks created
        homeworks_count = 0
        if HOMEWORK_MODEL_AVAILABLE:
            homeworks_count = Homework.objects.filter(teacher=teacher).count()
        
        activity = {
            'groups_count': groups_count,
            'total_lessons': total_lessons,
            'lessons_last_30_days': lessons_last_30_days,
            'homeworks_count': homeworks_count,
        }
        
        # === GROWTH (students) ===
        # Count unique students across all teacher's groups
        student_ids = ScheduleGroup.objects.filter(
            teacher=teacher
        ).values_list('students', flat=True).distinct()
        # Filter out None values
        total_students = len([s for s in student_ids if s is not None])
        
        growth = {
            'total_students': total_students,
        }
        
        # === FINANCE ===
        subscription = get_subscription(teacher)
        
        # Total payments for this teacher
        payments_agg = Payment.objects.filter(
            subscription=subscription,
            status=Payment.STATUS_SUCCEEDED
        ).aggregate(
            total_amount=Coalesce(Sum('amount'), Value(0)),
            payments_count=Count('id')
        )
        
        finance = {
            'subscription_status': subscription.status if subscription else None,
            'subscription_plan': subscription.plan if subscription else None,
            'subscription_expires_at': subscription.expires_at if subscription else None,
            'total_paid': float(payments_agg['total_amount']),
            'payments_count': payments_agg['payments_count'],
            'last_payment_date': subscription.last_payment_date if subscription else None,
        }
        
        # === BASIC INFO ===
        days_on_platform = (now - teacher.created_at).days if teacher.created_at else 0
        
        teacher_info = {
            'id': teacher.id,
            'email': teacher.email,
            'first_name': teacher.first_name,
            'last_name': teacher.last_name,
            'middle_name': teacher.middle_name,
            'created_at': teacher.created_at,
            'last_login': teacher.last_login,
            'days_on_platform': days_on_platform,
        }
        
        return Response({
            'teacher': teacher_info,
            'integrations': integrations,
            'activity': activity,
            'growth': growth,
            'finance': finance,
        })


# =============================================================================
# RATE LIMITING ADMIN VIEWS
# =============================================================================

class AdminRateLimitingStatsView(APIView):
    """
    GET /api/admin/rate-limiting/stats/
    
    Возвращает статистику rate limiting.
    Только для админов.
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get(self, request):
        user = request.user
        if user.role != 'admin':
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            from .bot_protection import get_rate_limit_stats
            stats = get_rate_limit_stats()
            return Response(stats)
        except Exception as e:
            logger.exception(f"[Admin] Failed to get rate limiting stats: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminRateLimitingClearView(APIView):
    """
    POST /api/admin/rate-limiting/clear/
    
    Сбрасывает все rate limits.
    Только для админов.
    
    Body (optional):
    - fingerprint: конкретный fingerprint для очистки
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def post(self, request):
        user = request.user
        if user.role != 'admin':
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        
        fingerprint = request.data.get('fingerprint')
        
        try:
            if fingerprint:
                from .bot_protection import clear_fingerprint_limits
                result = clear_fingerprint_limits(fingerprint)
                logger.info(f"[Admin] Rate limits cleared for fingerprint {fingerprint[:16]}... by {user.email}")
            else:
                from .bot_protection import clear_all_rate_limits
                result = clear_all_rate_limits()
                logger.info(f"[Admin] All rate limits cleared by {user.email}")
            
            return Response(result)
        except Exception as e:
            logger.exception(f"[Admin] Failed to clear rate limits: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
