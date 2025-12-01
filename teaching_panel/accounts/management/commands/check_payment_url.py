"""
Management command to test payment URL generation
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth import get_user_model
from accounts.payments_service import PaymentService
from accounts.models import Subscription

User = get_user_model()


class Command(BaseCommand):
    help = 'Test payment URL generation for mock mode'

    def handle(self, *args, **options):
        # Find first teacher user
        teacher = User.objects.filter(role='teacher').first()
        if not teacher:
            self.stdout.write(self.style.ERROR('No teacher found'))
            return
        
        subscription = Subscription.objects.filter(user=teacher).first()
        if not subscription:
            self.stdout.write(self.style.ERROR(f'No subscription for {teacher.email}'))
            return
        
        result = PaymentService.create_subscription_payment(subscription, 'monthly')
        
        self.stdout.write(f'FRONTEND_URL: {settings.FRONTEND_URL}')
        self.stdout.write(f'Payment URL: {result["payment_url"]}')
        self.stdout.write(self.style.SUCCESS('✓ Check complete'))
