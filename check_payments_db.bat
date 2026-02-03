@echo off
ssh tp "cd /var/www/teaching_panel/teaching_panel && . ../venv/bin/activate && python -c \"
import django
django.setup()
from accounts.models import Payment
from django.utils import timezone
from datetime import timedelta

# Last 20 succeeded payments
payments = Payment.objects.filter(status='succeeded').order_by('-paid_at')[:20]
print('=== Last 20 SUCCEEDED payments ===')
for p in payments:
    notified = p.admin_notified_at.strftime('%%Y-%%m-%%d %%H:%%M') if p.admin_notified_at else 'NULL'
    paid = p.paid_at.strftime('%%Y-%%m-%%d %%H:%%M') if p.paid_at else 'NULL'
    delta = ''
    if p.admin_notified_at and p.paid_at:
        diff = (p.admin_notified_at - p.paid_at).total_seconds()
        delta = f' (delta: {int(diff)}s)'
    print(f'{p.payment_id[:20]:20} | paid: {paid} | notified: {notified}{delta} | {p.payment_system}')
\""
