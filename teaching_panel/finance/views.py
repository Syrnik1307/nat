"""
Finance API views.

Endpoints:
- /api/finance/wallets/ - CRUD кошельков учеников (для учителей)
- /api/finance/wallets/{id}/deposit/ - пополнение баланса
- /api/finance/wallets/{id}/charge/ - ручное списание за урок
- /api/finance/wallets/{id}/adjust/ - корректировка баланса
- /api/finance/wallets/{id}/refund/ - возврат за урок
- /api/finance/my-balance/ - баланс для ученика (у всех его учителей)
- /api/finance/dashboard/ - дашборд с финансовой статистикой (для учителей)
"""
from decimal import Decimal
from datetime import timedelta
import logging

from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Sum, Count, Avg, Q, F
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from schedule.models import Lesson, Group
from .models import StudentFinancialProfile, Transaction
from .services import FinanceService, DuplicateChargeError
from .serializers import (
    WalletSerializer,
    WalletListSerializer,
    WalletCreateSerializer,
    WalletUpdateSerializer,
    TransactionSerializer,
    DepositSerializer,
    ChargeSerializer,
    AdjustSerializer,
    RefundSerializer,
    StudentBalanceSerializer,
)
from .permissions import IsTeacher, IsStudent
from core.tenant_mixins import TenantViewSetMixin

logger = logging.getLogger(__name__)


class WalletViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    """
    Кошельки учеников (для учителя).

    GET /api/finance/wallets/ — список кошельков моих учеников
    GET /api/finance/wallets/{id}/ — детали + история транзакций
    POST /api/finance/wallets/ — создать кошелёк ученику
    PATCH /api/finance/wallets/{id}/ — изменить цену урока, лимит долга
    DELETE /api/finance/wallets/{id}/ — удалить кошелёк (только если нет транзакций)

    POST /api/finance/wallets/{id}/deposit/ — пополнить баланс
    POST /api/finance/wallets/{id}/charge/ — ручное списание урока
    POST /api/finance/wallets/{id}/adjust/ — корректировка (+/- деньги)
    POST /api/finance/wallets/{id}/refund/ — возврат за урок
    """

    permission_classes = [IsAuthenticated, IsTeacher]

    def get_queryset(self):
        """Возвращаем только кошельки учеников текущего учителя в рамках tenant."""
        qs = StudentFinancialProfile.objects.filter(
            teacher=self.request.user
        ).select_related('student').prefetch_related('transactions')
        # Tenant isolation: дополнительно фильтруем по tenant если модель поддерживает
        tenant = getattr(self.request, 'tenant', None)
        if tenant and hasattr(StudentFinancialProfile, 'tenant'):
            qs = qs.filter(tenant=tenant)
        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return WalletListSerializer
        elif self.action == 'create':
            return WalletCreateSerializer
        elif self.action in ('update', 'partial_update'):
            return WalletUpdateSerializer
        return WalletSerializer

    def perform_create(self, serializer):
        """При создании автоматически устанавливаем teacher."""
        serializer.save(teacher=self.request.user)

    def destroy(self, request, *args, **kwargs):
        """Удаление только если нет транзакций."""
        wallet = self.get_object()
        if wallet.transactions.exists():
            return Response(
                {'detail': 'Невозможно удалить кошелёк с историей транзакций'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def deposit(self, request, pk=None):
        """
        Внести оплату от ученика.

        POST /api/finance/wallets/{id}/deposit/
        Body: {"amount": 5000, "description": "Оплата за октябрь"}
        """
        wallet = self.get_object()
        serializer = DepositSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            txn = FinanceService.deposit(
                wallet=wallet,
                amount=Decimal(str(serializer.validated_data['amount'])),
                created_by=request.user,
                description=serializer.validated_data.get('description', '')
            )

            # Возвращаем обновлённый кошелёк
            wallet.refresh_from_db()
            return Response({
                'transaction': TransactionSerializer(txn).data,
                'wallet': WalletSerializer(wallet).data,
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f'Deposit error: {e}')
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def charge(self, request, pk=None):
        """
        Ручное списание за урок.

        POST /api/finance/wallets/{id}/charge/
        Body: {"lesson_id": 123, "override_price": 1000, "description": "Пробный урок"}
        """
        wallet = self.get_object()
        serializer = ChargeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        lesson = get_object_or_404(
            Lesson,
            id=serializer.validated_data['lesson_id'],
            teacher=request.user
        )

        override_price = serializer.validated_data.get('override_price')
        if override_price is not None:
            override_price = Decimal(str(override_price))

        try:
            txn = FinanceService.charge_lesson(
                wallet=wallet,
                lesson=lesson,
                created_by=request.user,
                override_price=override_price,
                description=serializer.validated_data.get('description', ''),
                auto_created=False
            )

            if txn is None:
                return Response(
                    {'detail': 'Списание не выполнено: цена урока = 0'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            wallet.refresh_from_db()
            return Response({
                'transaction': TransactionSerializer(txn).data,
                'wallet': WalletSerializer(wallet).data,
            }, status=status.HTTP_201_CREATED)

        except DuplicateChargeError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_409_CONFLICT
            )
        except Exception as e:
            logger.error(f'Charge error: {e}')
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def adjust(self, request, pk=None):
        """
        Корректировка баланса.

        POST /api/finance/wallets/{id}/adjust/
        Body: {"amount": -1500, "description": "Ошибочное списание"}
        """
        wallet = self.get_object()
        serializer = AdjustSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            txn = FinanceService.adjust(
                wallet=wallet,
                amount=Decimal(str(serializer.validated_data['amount'])),
                created_by=request.user,
                description=serializer.validated_data['description']
            )

            wallet.refresh_from_db()
            return Response({
                'transaction': TransactionSerializer(txn).data,
                'wallet': WalletSerializer(wallet).data,
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f'Adjust error: {e}')
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def refund(self, request, pk=None):
        """
        Возврат за урок.

        POST /api/finance/wallets/{id}/refund/
        Body: {"lesson_id": 123, "description": "Урок отменён"}
        """
        wallet = self.get_object()
        serializer = RefundSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        lesson = get_object_or_404(
            Lesson,
            id=serializer.validated_data['lesson_id'],
            teacher=request.user
        )

        try:
            txn = FinanceService.refund_lesson(
                wallet=wallet,
                lesson=lesson,
                created_by=request.user,
                description=serializer.validated_data.get('description', '')
            )

            wallet.refresh_from_db()
            return Response({
                'transaction': TransactionSerializer(txn).data,
                'wallet': WalletSerializer(wallet).data,
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f'Refund error: {e}')
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'])
    def transactions(self, request, pk=None):
        """
        Полная история транзакций кошелька.

        GET /api/finance/wallets/{id}/transactions/
        Query params: ?limit=100&offset=0
        """
        wallet = self.get_object()

        limit = int(request.query_params.get('limit', 100))
        offset = int(request.query_params.get('offset', 0))

        txns = wallet.transactions.all()[offset:offset + limit]
        total = wallet.transactions.count()

        return Response({
            'results': TransactionSerializer(txns, many=True).data,
            'total': total,
            'limit': limit,
            'offset': offset,
        })


class StudentBalanceView(APIView):
    """
    Баланс для ученика.

    GET /api/finance/my-balance/

    Возвращает балансы у всех учителей ученика.
    Показывает только остаток уроков и статус (без детальной истории).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'student':
            return Response(
                {'detail': 'Доступно только для учеников'},
                status=status.HTTP_403_FORBIDDEN
            )

        wallets = StudentFinancialProfile.objects.filter(
            student=request.user
        ).select_related('teacher')
        # Tenant isolation
        tenant = getattr(request, 'tenant', None)
        if tenant and hasattr(StudentFinancialProfile, 'tenant'):
            wallets = wallets.filter(tenant=tenant)

        return Response({
            'balances': StudentBalanceSerializer(wallets, many=True).data
        })


class FinanceDashboardView(APIView):
    """
    Финансовый дашборд для учителя.

    GET /api/finance/dashboard/
    Query params:
        ?group_id=123 - фильтр по группе
        ?student_id=456 - фильтр по ученику

    Возвращает:
        - summary: общая статистика (ученики, баланс, долги)
        - earnings: доходы текущего/прошлого месяца + рост %
        - average_lesson_price: средняя цена урока
        - by_group: разбивка по группам
    """

    permission_classes = [IsAuthenticated, IsTeacher]

    def get(self, request):
        teacher = request.user
        tenant = getattr(request, 'tenant', None)

        # Фильтры
        group_id = request.query_params.get('group_id')
        student_id = request.query_params.get('student_id')

        # Базовый queryset кошельков
        wallets = StudentFinancialProfile.objects.filter(teacher=teacher)
        # Tenant isolation
        if tenant and hasattr(StudentFinancialProfile, 'tenant'):
            wallets = wallets.filter(tenant=tenant)

        # Применяем фильтры
        if student_id:
            wallets = wallets.filter(student_id=student_id)

        if group_id:
            # Получаем студентов из группы
            try:
                group = Group.objects.get(id=group_id, teacher=teacher)
                student_ids = group.students.values_list('id', flat=True)
                wallets = wallets.filter(student_id__in=student_ids)
            except Group.DoesNotExist:
                pass

        # === SUMMARY ===
        wallet_stats = wallets.aggregate(
            total_students=Count('id'),
            total_balance=Sum('balance'),
            debtors_count=Count('id', filter=Q(balance__lt=0)),
            total_debt=Sum('balance', filter=Q(balance__lt=0)),
        )

        # Кто превысил лимит долга
        over_limit_count = wallets.filter(
            balance__lt=0
        ).annotate(
            debt_exceeded=F('balance') + F('debt_limit')  # balance + limit < 0 means exceeded
        ).filter(debt_exceeded__lt=0).count()

        # Low balance (< 2 уроков)
        low_balance_wallets = []
        for w in wallets.filter(balance__lt=F('default_lesson_price') * 2):
            low_balance_wallets.append({
                'id': w.id,
                'student_name': w.student.get_full_name() or w.student.email,
                'balance': float(w.balance),
                'lessons_left': w.lessons_left,
            })

        # === EARNINGS (текущий месяц vs прошлый) ===
        now = timezone.now()
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        prev_month_start = (current_month_start - timedelta(days=1)).replace(day=1)

        # Базовый queryset транзакций
        txn_base = Transaction.objects.filter(wallet__teacher=teacher)
        # Tenant isolation для транзакций
        if tenant and hasattr(Transaction, 'tenant'):
            txn_base = txn_base.filter(tenant=tenant)
        elif tenant and hasattr(StudentFinancialProfile, 'tenant'):
            txn_base = txn_base.filter(wallet__tenant=tenant)

        if student_id:
            txn_base = txn_base.filter(wallet__student_id=student_id)
        if group_id and 'student_ids' in dir():
            txn_base = txn_base.filter(wallet__student_id__in=student_ids)

        # Доходы = DEPOSIT транзакции (деньги полученные от учеников)
        current_month_deposits = txn_base.filter(
            transaction_type='DEPOSIT',
            created_at__gte=current_month_start
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        prev_month_deposits = txn_base.filter(
            transaction_type='DEPOSIT',
            created_at__gte=prev_month_start,
            created_at__lt=current_month_start
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        # Рост в %
        if prev_month_deposits > 0:
            deposit_growth = float((current_month_deposits - prev_month_deposits) / prev_month_deposits * 100)
        else:
            deposit_growth = 100 if current_month_deposits > 0 else 0

        # Проведено уроков (LESSON_CHARGE) за текущий месяц
        current_month_charges = txn_base.filter(
            transaction_type='LESSON_CHARGE',
            created_at__gte=current_month_start
        ).aggregate(
            total=Sum('amount'),
            count=Count('id')
        )

        lessons_conducted = current_month_charges['count'] or 0
        lessons_revenue = abs(float(current_month_charges['total'] or 0))

        # === AVERAGE LESSON PRICE ===
        avg_price = wallets.aggregate(avg=Avg('default_lesson_price'))['avg'] or Decimal('0')

        # === BY GROUP ===
        groups_data = []
        teacher_groups = Group.objects.filter(teacher=teacher).prefetch_related('students')
        # Tenant isolation для групп
        if tenant and hasattr(Group, 'tenant'):
            teacher_groups = teacher_groups.filter(tenant=tenant)

        for group in teacher_groups:
            group_student_ids = list(group.students.values_list('id', flat=True))
            group_wallets = wallets.filter(student_id__in=group_student_ids)

            stats = group_wallets.aggregate(
                students=Count('id'),
                balance=Sum('balance'),
                debtors=Count('id', filter=Q(balance__lt=0)),
            )

            if stats['students'] > 0:
                groups_data.append({
                    'group_id': group.id,
                    'group_name': group.name,
                    'students_count': stats['students'],
                    'total_balance': float(stats['balance'] or 0),
                    'debtors_count': stats['debtors'],
                })

        # === TOP DEBTORS ===
        top_debtors = []
        for w in wallets.filter(balance__lt=0).order_by('balance')[:5]:
            top_debtors.append({
                'id': w.id,
                'student_id': w.student_id,
                'student_name': w.student.get_full_name() or w.student.email,
                'balance': float(w.balance),
                'debt_limit': float(w.debt_limit),
                'limit_exceeded': float(w.balance) < -float(w.debt_limit),
            })

        return Response({
            'summary': {
                'total_students': wallet_stats['total_students'] or 0,
                'total_balance': float(wallet_stats['total_balance'] or 0),
                'debtors_count': wallet_stats['debtors_count'] or 0,
                'total_debt': float(wallet_stats['total_debt'] or 0),
                'over_limit_count': over_limit_count,
                'low_balance_count': len(low_balance_wallets),
            },
            'earnings': {
                'current_month': float(current_month_deposits),
                'previous_month': float(prev_month_deposits),
                'growth_percent': round(deposit_growth, 1),
                'lessons_conducted': lessons_conducted,
                'lessons_revenue': lessons_revenue,
            },
            'average_lesson_price': float(avg_price),
            'by_group': groups_data,
            'top_debtors': top_debtors,
            'low_balance': low_balance_wallets[:5],
        })
