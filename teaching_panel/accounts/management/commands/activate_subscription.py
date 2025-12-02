"""
Management command для активации подписки пользователя

Использование:
    python manage.py activate_subscription --email user@example.com --days 365
    python manage.py activate_subscription --telegram-id 123456789 --days 30
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from accounts.models import CustomUser, Subscription


class Command(BaseCommand):
    help = 'Активировать подписку пользователя на указанное количество дней'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            help='Email пользователя'
        )
        parser.add_argument(
            '--telegram-id',
            type=str,
            help='Telegram ID пользователя'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=365,
            help='Количество дней активации (по умолчанию 365)'
        )

    def handle(self, *args, **options):
        email = options.get('email')
        telegram_id = options.get('telegram_id')
        days = options['days']

        if not email and not telegram_id:
            self.stdout.write(self.style.ERROR('Укажите --email или --telegram-id'))
            return

        # Найти пользователя
        try:
            if email:
                user = CustomUser.objects.get(email=email)
            else:
                user = CustomUser.objects.get(telegram_id=telegram_id)
        except CustomUser.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Пользователь не найден'))
            return

        self.stdout.write(f'Пользователь: {user.email} (роль: {user.role})')

        # Получить или создать подписку
        subscription, created = Subscription.objects.get_or_create(
            user=user,
            defaults={
                'plan': Subscription.PLAN_YEARLY if days >= 365 else Subscription.PLAN_MONTHLY,
                'status': Subscription.STATUS_ACTIVE,
                'expires_at': timezone.now() + timedelta(days=days),
                'auto_renew': False
            }
        )

        if not created:
            # Обновить существующую подписку
            subscription.status = Subscription.STATUS_ACTIVE
            subscription.expires_at = timezone.now() + timedelta(days=days)
            subscription.save()
            self.stdout.write(self.style.SUCCESS('Подписка обновлена!'))
        else:
            self.stdout.write(self.style.SUCCESS('Подписка создана!'))

        self.stdout.write(f'Статус: {subscription.status}')
        self.stdout.write(f'Истекает: {subscription.expires_at}')
        self.stdout.write(f'Активна: {subscription.is_active()}')
