#!/bin/bash
set -euo pipefail

ENV=$(systemctl show teaching_panel.service -p Environment --value)
getvar(){ printf "%s" "$ENV" | tr " " "\n" | sed -n "s/^$1=//p" | tail -n 1; }

export TELEGRAM_BOT_TOKEN="$(getvar TELEGRAM_BOT_TOKEN)"
export TELEGRAM_BOT_USERNAME="$(getvar TELEGRAM_BOT_USERNAME)"
export ADMIN_PAYMENT_TELEGRAM_CHAT_ID="$(getvar ADMIN_PAYMENT_TELEGRAM_CHAT_ID)"
export TBANK_TERMINAL_KEY="$(getvar TBANK_TERMINAL_KEY)"
export TBANK_PASSWORD="$(getvar TBANK_PASSWORD)"

cd /var/www/teaching_panel/teaching_panel
source ../venv/bin/activate

python manage.py shell <<'PYEOF'
from accounts.models import CustomUser, Subscription, Payment
from accounts.tbank_service import TBankService
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
import uuid

# 1) создаём тестового учителя (уникальный email)
email = f"test_teacher_payment_{uuid.uuid4().hex[:8]}@lectio.space"
user = CustomUser.objects.create_user(
    email=email,
    password=uuid.uuid4().hex,
    role='teacher',
    first_name='Test',
    last_name='Teacher',
    is_active=True,
)

# 2) создаём подписку (pending)
sub = Subscription.objects.create(
    user=user,
    plan=Subscription.PLAN_TRIAL,
    status=Subscription.STATUS_PENDING,
    expires_at=timezone.now(),
    base_storage_gb=10,
)

# 3) создаём платёж (pending)
payment_id = str(900000000000 + (uuid.uuid4().int % 100000000000))
order_id = f"test-order-{uuid.uuid4().hex[:8]}"

payment = Payment.objects.create(
    subscription=sub,
    amount=Decimal('990.00'),
    currency='RUB',
    status=Payment.STATUS_PENDING,
    payment_system='tbank',
    payment_id=payment_id,
    payment_url='',
    metadata={'plan': 'monthly', 'order_id': order_id},
)

# 4) симулируем webhook CONFIRMED от T-Bank (с корректным Token)
notification_data = {
    'TerminalKey': getattr(settings, 'TBANK_TERMINAL_KEY', ''),
    'PaymentId': payment_id,
    'Status': 'CONFIRMED',
    'OrderId': order_id,
}
notification_data['Token'] = TBankService._generate_token(notification_data)

ok = TBankService.process_notification(notification_data)

sub.refresh_from_db()
payment.refresh_from_db()

print('created_user_email:', user.email)
print('payment_id:', payment.payment_id)
print('process_ok:', ok)
print('payment_status:', payment.status)
print('subscription_status:', sub.status)
print('subscription_plan:', sub.plan)
print('subscription_expires_at:', sub.expires_at.strftime('%Y-%m-%d %H:%M:%S'))
PYEOF
