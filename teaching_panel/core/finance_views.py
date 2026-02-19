"""
Финансовая статистика — API.

Предоставляет агрегированные данные по продажам курсов:
- общая выручка,
- количество покупок по типам,
- динамика продаж по месяцам,
- детализация по курсам.
"""

from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum, Count, F, Q, Value, CharField
from django.db.models.functions import TruncMonth, Coalesce
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Course, CourseAccess


class FinanceStatsView(APIView):
    """
    GET /api/finance/stats/

    Возвращает финансовую сводку для текущего тенанта.
    Доступно только admin и teacher.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        role = getattr(user, 'role', None)
        if role not in ('admin', 'teacher'):
            return Response({'error': 'Доступ только для admin/teacher'}, status=403)

        tenant = getattr(request, 'tenant', None)

        # ── Базовые querysets ──────────────────────────────────
        courses_qs = Course.objects.all()
        if tenant:
            courses_qs = courses_qs.filter(tenant=tenant)
        if role == 'teacher':
            courses_qs = courses_qs.filter(teacher=user)

        course_ids = list(courses_qs.values_list('id', flat=True))

        accesses_qs = CourseAccess.objects.filter(course_id__in=course_ids)

        # ── Общая статистика ──────────────────────────────────
        total_accesses = accesses_qs.count()
        purchased = accesses_qs.filter(access_type='purchased').count()
        granted = accesses_qs.filter(access_type='granted').count()
        trial = accesses_qs.filter(access_type='trial').count()

        # Выручка — сумма price курсов, к которым дан access_type=purchased
        revenue_qs = (
            accesses_qs
            .filter(access_type='purchased', is_active=True)
            .select_related('course')
        )
        total_revenue = Decimal('0')
        for access in revenue_qs:
            price = access.course.price or Decimal('0')
            total_revenue += price

        # Активные / истёкшие
        now = timezone.now()
        active_accesses = accesses_qs.filter(is_active=True).count()
        expired_accesses = accesses_qs.filter(
            Q(is_active=False) | Q(expires_at__lt=now)
        ).count()

        # ── Динамика по месяцам (последние 12 мес) ────────────
        twelve_months_ago = now - timedelta(days=365)
        monthly_raw = (
            accesses_qs
            .filter(granted_at__gte=twelve_months_ago)
            .annotate(month=TruncMonth('granted_at'))
            .values('month')
            .annotate(
                count=Count('id'),
                purchased_count=Count('id', filter=Q(access_type='purchased')),
            )
            .order_by('month')
        )
        monthly = []
        for row in monthly_raw:
            label = row['month'].strftime('%Y-%m') if row['month'] else '—'
            # Подсчитываем примерную выручку за месяц
            month_revenue = Decimal('0')
            month_accesses = accesses_qs.filter(
                access_type='purchased',
                is_active=True,
                granted_at__year=row['month'].year,
                granted_at__month=row['month'].month,
            ).select_related('course')
            for a in month_accesses:
                month_revenue += (a.course.price or Decimal('0'))
            monthly.append({
                'month': label,
                'total': row['count'],
                'purchased': row['purchased_count'],
                'revenue': str(month_revenue),
            })

        # ── Детализация по курсам ─────────────────────────────
        courses_detail = []
        for course in courses_qs.order_by('-created_at'):
            c_accesses = accesses_qs.filter(course=course)
            c_purchased = c_accesses.filter(access_type='purchased').count()
            c_granted = c_accesses.filter(access_type='granted').count()
            c_trial = c_accesses.filter(access_type='trial').count()
            c_revenue = (course.price or Decimal('0')) * c_purchased
            courses_detail.append({
                'id': course.id,
                'title': course.title,
                'price': str(course.price) if course.price else None,
                'status': course.status,
                'is_published': course.is_published,
                'purchased': c_purchased,
                'granted': c_granted,
                'trial': c_trial,
                'total_accesses': c_purchased + c_granted + c_trial,
                'revenue': str(c_revenue),
                'created_at': course.created_at.isoformat(),
            })

        # ── Последние продажи (15 шт.) ───────────────────────
        recent_sales = (
            accesses_qs
            .select_related('user', 'course')
            .order_by('-granted_at')[:15]
        )
        recent = []
        for sale in recent_sales:
            recent.append({
                'id': sale.id,
                'user_name': f'{sale.user.first_name} {sale.user.last_name}'.strip() or sale.user.email,
                'user_email': sale.user.email,
                'course_title': sale.course.title,
                'access_type': sale.access_type,
                'granted_at': sale.granted_at.isoformat(),
                'is_active': sale.is_active,
                'amount': str(sale.course.price) if sale.access_type == 'purchased' and sale.course.price else '0',
            })

        return Response({
            'summary': {
                'total_revenue': str(total_revenue),
                'total_accesses': total_accesses,
                'purchased': purchased,
                'granted': granted,
                'trial': trial,
                'active_accesses': active_accesses,
                'expired_accesses': expired_accesses,
                'courses_count': courses_qs.count(),
                'published_courses': courses_qs.filter(is_published=True).count(),
            },
            'monthly': monthly,
            'courses': courses_detail,
            'recent_sales': recent,
        })
