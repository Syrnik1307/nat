from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.conf import settings
from .models import ReferralCommission

User = get_user_model()

class MyReferralLinkView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        # Базовый домен для ссылки
        origin = getattr(settings, 'FRONTEND_URL', '').rstrip('/') or 'https://lectiospace.ru'
        # Ссылка: добавляем ?ref=<code> и рекомендуем UTM
        link = f"{origin}/?ref={user.referral_code}&utm_source=telegram&utm_medium=referral&utm_campaign=teaching_panel"
        return Response({
            'referral_code': user.referral_code,
            'referral_link': link,
            'suggested_utm': {
                'utm_source': 'telegram',
                'utm_medium': 'referral',
                'utm_campaign': 'teaching_panel',
            }
        })

class MyReferralStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        # Кол-во приглашённых
        referred_count = User.objects.filter(referred_by=user).count()
        # Комиссии
        commissions_qs = ReferralCommission.objects.filter(referrer=user)
        total_pending = sum([c.amount for c in commissions_qs.filter(status=ReferralCommission.STATUS_PENDING)])
        total_paid = sum([c.amount for c in commissions_qs.filter(status=ReferralCommission.STATUS_PAID)])
        items = [
            {
                'referred_user_email': c.referred_user.email,
                'amount': str(c.amount),
                'status': c.status,
                'payment_id': c.payment.payment_id if c.payment else None,
                'created_at': c.created_at,
                'paid_at': c.paid_at,
            }
            for c in commissions_qs.order_by('-created_at')[:100]
        ]
        return Response({
            'referred_count': referred_count,
            'commissions': items,
            'total_pending': str(total_pending),
            'total_paid': str(total_paid),
        })
