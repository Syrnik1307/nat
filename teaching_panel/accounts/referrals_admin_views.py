"""
Admin API для управления реферальными ссылками и статистикой.
Доступно только для role='admin'.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.conf import settings
from decimal import Decimal

from .models import (
    ReferralLink, 
    ReferralClick, 
    ReferralAttribution, 
    ReferralCommission,
    CustomUser,
    Payment,
)


class IsAdmin:
    """Permission: только админы"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'


class AdminReferralLinksListView(APIView):
    """
    GET: Список всех реферальных ссылок с статистикой
    POST: Создать новую реферальную ссылку
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if request.user.role != 'admin':
            return Response({'detail': 'Доступ запрещён'}, status=status.HTTP_403_FORBIDDEN)
        
        links = ReferralLink.objects.all().order_by('-created_at')
        
        result = []
        for link in links:
            result.append({
                'id': link.id,
                'code': link.code,
                'name': link.name,
                'partner_name': link.partner_name,
                'partner_contact': link.partner_contact,
                'commission_amount': str(link.commission_amount),
                'utm_source': link.utm_source,
                'utm_medium': link.utm_medium,
                'utm_campaign': link.utm_campaign,
                'full_url': link.get_full_url(),
                'clicks_count': link.clicks_count,
                'registrations_count': link.registrations_count,
                'payments_count': link.payments_count,
                'total_earned': str(link.total_earned),
                'total_paid_out': str(link.total_paid_out),
                'pending_payout': str(link.total_earned - link.total_paid_out),
                'is_active': link.is_active,
                'created_at': link.created_at,
                'notes': link.notes,
            })
        
        # Общая статистика
        totals = ReferralLink.objects.aggregate(
            total_clicks=Sum('clicks_count'),
            total_registrations=Sum('registrations_count'),
            total_payments=Sum('payments_count'),
            total_earned=Sum('total_earned'),
            total_paid_out=Sum('total_paid_out'),
        )
        
        return Response({
            'links': result,
            'totals': {
                'clicks': totals['total_clicks'] or 0,
                'registrations': totals['total_registrations'] or 0,
                'payments': totals['total_payments'] or 0,
                'earned': str(totals['total_earned'] or Decimal('0.00')),
                'paid_out': str(totals['total_paid_out'] or Decimal('0.00')),
                'pending': str((totals['total_earned'] or Decimal('0.00')) - (totals['total_paid_out'] or Decimal('0.00'))),
            }
        })
    
    def post(self, request):
        if request.user.role != 'admin':
            return Response({'detail': 'Доступ запрещён'}, status=status.HTTP_403_FORBIDDEN)
        
        data = request.data
        name = data.get('name', '').strip()
        if not name:
            return Response({'detail': 'Название обязательно'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Генерируем или используем заданный код
        code = data.get('code', '').strip().upper()
        if not code:
            code = ReferralLink.generate_code()
        elif ReferralLink.objects.filter(code=code).exists():
            return Response({'detail': 'Код уже существует'}, status=status.HTTP_400_BAD_REQUEST)
        
        link = ReferralLink.objects.create(
            code=code,
            name=name,
            partner_name=data.get('partner_name', ''),
            partner_contact=data.get('partner_contact', ''),
            commission_amount=Decimal(data.get('commission_amount', '750.00')),
            utm_source=data.get('utm_source', 'telegram'),
            utm_medium=data.get('utm_medium', 'referral'),
            utm_campaign=data.get('utm_campaign', ''),
            notes=data.get('notes', ''),
            is_active=data.get('is_active', True),
        )
        
        return Response({
            'id': link.id,
            'code': link.code,
            'full_url': link.get_full_url(),
            'detail': 'Ссылка создана'
        }, status=status.HTTP_201_CREATED)


class AdminReferralLinkDetailView(APIView):
    """
    GET: Детальная информация о ссылке + список регистраций/оплат
    PUT: Обновить ссылку
    DELETE: Удалить ссылку
    """
    permission_classes = [IsAuthenticated]
    
    def get_link(self, link_id):
        try:
            return ReferralLink.objects.get(id=link_id)
        except ReferralLink.DoesNotExist:
            return None
    
    def get(self, request, link_id):
        if request.user.role != 'admin':
            return Response({'detail': 'Доступ запрещён'}, status=status.HTTP_403_FORBIDDEN)
        
        link = self.get_link(link_id)
        if not link:
            return Response({'detail': 'Ссылка не найдена'}, status=status.HTTP_404_NOT_FOUND)
        
        # Регистрации по этой ссылке
        attributions = ReferralAttribution.objects.filter(referral_code__iexact=link.code).select_related('user')
        registrations = []
        for attr in attributions:
            user = attr.user
            # Проверяем, была ли оплата
            has_payment = False
            payment_amount = None
            try:
                if hasattr(user, 'subscription'):
                    payments = user.subscription.payments.filter(status='succeeded')
                    if payments.exists():
                        has_payment = True
                        payment_amount = str(payments.aggregate(total=Sum('amount'))['total'] or 0)
            except:
                pass
            
            registrations.append({
                'user_id': user.id,
                'email': user.email,
                'name': user.get_full_name(),
                'registered_at': attr.created_at,
                'has_payment': has_payment,
                'payment_amount': payment_amount,
            })
        
        # Последние клики
        clicks = ReferralClick.objects.filter(link=link).order_by('-created_at')[:50]
        clicks_data = [
            {
                'id': c.id,
                'ip': c.ip_address,
                'created_at': c.created_at,
                'resulted_in_registration': c.resulted_in_registration,
                'user_email': c.registered_user.email if c.registered_user else None,
            }
            for c in clicks
        ]
        
        return Response({
            'link': {
                'id': link.id,
                'code': link.code,
                'name': link.name,
                'partner_name': link.partner_name,
                'partner_contact': link.partner_contact,
                'commission_amount': str(link.commission_amount),
                'utm_source': link.utm_source,
                'utm_medium': link.utm_medium,
                'utm_campaign': link.utm_campaign,
                'full_url': link.get_full_url(),
                'clicks_count': link.clicks_count,
                'registrations_count': link.registrations_count,
                'payments_count': link.payments_count,
                'total_earned': str(link.total_earned),
                'total_paid_out': str(link.total_paid_out),
                'pending_payout': str(link.total_earned - link.total_paid_out),
                'is_active': link.is_active,
                'created_at': link.created_at,
                'notes': link.notes,
            },
            'registrations': registrations,
            'clicks': clicks_data,
        })
    
    def put(self, request, link_id):
        if request.user.role != 'admin':
            return Response({'detail': 'Доступ запрещён'}, status=status.HTTP_403_FORBIDDEN)
        
        link = self.get_link(link_id)
        if not link:
            return Response({'detail': 'Ссылка не найдена'}, status=status.HTTP_404_NOT_FOUND)
        
        data = request.data
        
        # Обновляем поля
        if 'name' in data:
            link.name = data['name']
        if 'partner_name' in data:
            link.partner_name = data['partner_name']
        if 'partner_contact' in data:
            link.partner_contact = data['partner_contact']
        if 'commission_amount' in data:
            link.commission_amount = Decimal(data['commission_amount'])
        if 'utm_source' in data:
            link.utm_source = data['utm_source']
        if 'utm_medium' in data:
            link.utm_medium = data['utm_medium']
        if 'utm_campaign' in data:
            link.utm_campaign = data['utm_campaign']
        if 'notes' in data:
            link.notes = data['notes']
        if 'is_active' in data:
            link.is_active = data['is_active']
        
        link.save()
        
        return Response({'detail': 'Ссылка обновлена', 'id': link.id})
    
    def delete(self, request, link_id):
        if request.user.role != 'admin':
            return Response({'detail': 'Доступ запрещён'}, status=status.HTTP_403_FORBIDDEN)
        
        link = self.get_link(link_id)
        if not link:
            return Response({'detail': 'Ссылка не найдена'}, status=status.HTTP_404_NOT_FOUND)
        
        link.delete()
        return Response({'detail': 'Ссылка удалена'}, status=status.HTTP_204_NO_CONTENT)


class AdminReferralPayoutView(APIView):
    """
    POST: Отметить выплату партнёру
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, link_id):
        if request.user.role != 'admin':
            return Response({'detail': 'Доступ запрещён'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            link = ReferralLink.objects.get(id=link_id)
        except ReferralLink.DoesNotExist:
            return Response({'detail': 'Ссылка не найдена'}, status=status.HTTP_404_NOT_FOUND)
        
        amount = Decimal(request.data.get('amount', '0'))
        if amount <= 0:
            return Response({'detail': 'Укажите сумму выплаты'}, status=status.HTTP_400_BAD_REQUEST)
        
        pending = link.total_earned - link.total_paid_out
        if amount > pending:
            return Response({'detail': f'Сумма превышает ожидающую выплату ({pending})'}, status=status.HTTP_400_BAD_REQUEST)
        
        link.record_payout(amount)
        
        return Response({
            'detail': f'Выплата {amount} записана',
            'total_paid_out': str(link.total_paid_out),
            'pending_payout': str(link.total_earned - link.total_paid_out),
        })


class AdminReferralCommissionsView(APIView):
    """
    GET: Список всех комиссий (pending/paid)
    POST: Массовая отметка выплаты
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if request.user.role != 'admin':
            return Response({'detail': 'Доступ запрещён'}, status=status.HTTP_403_FORBIDDEN)
        
        status_filter = request.query_params.get('status', '')
        qs = ReferralCommission.objects.select_related('referrer', 'referred_user', 'payment').order_by('-created_at')
        
        if status_filter:
            qs = qs.filter(status=status_filter)
        
        result = []
        for c in qs[:200]:
            result.append({
                'id': c.id,
                'referrer_email': c.referrer.email,
                'referrer_name': c.referrer.get_full_name(),
                'referred_user_email': c.referred_user.email,
                'referred_user_name': c.referred_user.get_full_name(),
                'amount': str(c.amount),
                'status': c.status,
                'payment_id': c.payment.payment_id if c.payment else None,
                'created_at': c.created_at,
                'paid_at': c.paid_at,
                'notes': c.notes,
            })
        
        totals = ReferralCommission.objects.aggregate(
            pending=Sum('amount', filter=Q(status='pending')),
            paid=Sum('amount', filter=Q(status='paid')),
        )
        
        return Response({
            'commissions': result,
            'totals': {
                'pending': str(totals['pending'] or Decimal('0.00')),
                'paid': str(totals['paid'] or Decimal('0.00')),
            }
        })
    
    def post(self, request):
        """Массовая отметка выплаты"""
        if request.user.role != 'admin':
            return Response({'detail': 'Доступ запрещён'}, status=status.HTTP_403_FORBIDDEN)
        
        commission_ids = request.data.get('commission_ids', [])
        if not commission_ids:
            return Response({'detail': 'Укажите commission_ids'}, status=status.HTTP_400_BAD_REQUEST)
        
        updated = ReferralCommission.objects.filter(
            id__in=commission_ids,
            status=ReferralCommission.STATUS_PENDING
        ).update(status=ReferralCommission.STATUS_PAID, paid_at=timezone.now())
        
        return Response({'detail': f'Отмечено выплачено: {updated} комиссий'})


class AdminReferralStatsView(APIView):
    """
    GET: Общая статистика по реферальной программе
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if request.user.role != 'admin':
            return Response({'detail': 'Доступ запрещён'}, status=status.HTTP_403_FORBIDDEN)
        
        # Ссылки
        links_count = ReferralLink.objects.count()
        active_links = ReferralLink.objects.filter(is_active=True).count()
        
        # Клики
        total_clicks = ReferralLink.objects.aggregate(s=Sum('clicks_count'))['s'] or 0
        
        # Регистрации через рефералку
        ref_registrations = ReferralAttribution.objects.exclude(referral_code='').count()
        
        # Оплаты
        total_payments = ReferralLink.objects.aggregate(s=Sum('payments_count'))['s'] or 0
        
        # Комиссии
        commissions = ReferralCommission.objects.aggregate(
            pending=Sum('amount', filter=Q(status='pending')),
            paid=Sum('amount', filter=Q(status='paid')),
            total=Sum('amount'),
        )
        
        # Конверсии
        click_to_reg = (ref_registrations / total_clicks * 100) if total_clicks > 0 else 0
        reg_to_payment = (total_payments / ref_registrations * 100) if ref_registrations > 0 else 0
        
        return Response({
            'links': {
                'total': links_count,
                'active': active_links,
            },
            'clicks': total_clicks,
            'registrations': ref_registrations,
            'payments': total_payments,
            'commissions': {
                'pending': str(commissions['pending'] or Decimal('0.00')),
                'paid': str(commissions['paid'] or Decimal('0.00')),
                'total': str(commissions['total'] or Decimal('0.00')),
            },
            'conversions': {
                'click_to_registration': round(click_to_reg, 2),
                'registration_to_payment': round(reg_to_payment, 2),
            }
        })


class ReferralClickTrackView(APIView):
    """
    GET: Эндпоинт для трекинга кликов (можно вызывать как pixel или redirect)
    """
    permission_classes = []  # Публичный
    
    def get(self, request):
        code = request.query_params.get('ref', '').strip().upper()
        if not code:
            return Response({'detail': 'No ref code'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            link = ReferralLink.objects.get(code__iexact=code, is_active=True)
        except ReferralLink.DoesNotExist:
            return Response({'detail': 'Invalid ref code'}, status=status.HTTP_404_NOT_FOUND)
        
        # Записываем клик
        ip = self._get_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        referer = request.META.get('HTTP_REFERER', '')[:500]
        cookie_id = request.query_params.get('cookie_id', '')
        
        ReferralClick.objects.create(
            link=link,
            ip_address=ip,
            user_agent=user_agent,
            referer=referer,
            cookie_id=cookie_id,
        )
        
        link.increment_clicks()
        
        return Response({'tracked': True, 'code': link.code})
    
    def _get_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
