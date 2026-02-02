"""
Management command для маркировки старых платежей как "уведомление отправлено".

Используется для очистки "очереди" старых платежей без фактической отправки уведомлений.
Запускать ОДИН РАЗ после деплоя миграции с полем admin_notified_at.

Usage:
    python manage.py mark_old_payments_notified
    python manage.py mark_old_payments_notified --dry-run  # только показать что будет сделано
"""
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'Mark old succeeded payments as admin_notified to prevent duplicate notifications'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Only show what would be done, do not modify database',
        )

    def handle(self, *args, **options):
        from accounts.models import Payment
        
        dry_run = options['dry_run']
        
        # Найти все SUCCEEDED платежи без отметки об уведомлении
        payments_to_mark = Payment.objects.filter(
            status=Payment.STATUS_SUCCEEDED,
            admin_notified_at__isnull=True
        )
        
        count = payments_to_mark.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No payments to mark. All succeeded payments already have admin_notified_at set.'))
            return
        
        self.stdout.write(f'Found {count} succeeded payments without admin_notified_at')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN: No changes made'))
            
            # Показать первые 10 для примера
            for payment in payments_to_mark[:10]:
                self.stdout.write(
                    f'  - Payment {payment.payment_id} | {payment.amount} {payment.currency} | '
                    f'paid_at={payment.paid_at} | system={payment.payment_system}'
                )
            if count > 10:
                self.stdout.write(f'  ... and {count - 10} more')
            return
        
        # Массовое обновление — быстрее чем по одному
        now = timezone.now()
        updated = payments_to_mark.update(admin_notified_at=now)
        
        self.stdout.write(self.style.SUCCESS(
            f'Successfully marked {updated} payments as notified (admin_notified_at={now.isoformat()})'
        ))
