#!/bin/bash
set -euo pipefail

cd /var/www/teaching_panel/teaching_panel
source ../venv/bin/activate

# Подхватываем секреты T-Bank из окружения systemd сервиса (иначе в ssh-сессии их нет)
ENV=$(systemctl show teaching_panel.service -p Environment --value)
getvar(){ printf "%s" "$ENV" | tr " " "\n" | sed -n "s/^$1=//p" | tail -n 1; }

export TBANK_TERMINAL_KEY="$(getvar TBANK_TERMINAL_KEY)"
export TBANK_PASSWORD="$(getvar TBANK_PASSWORD)"

# 1) Создаём тестового учителя + pending платёж, печатаем JSON payload для webhook
PAYLOAD_JSON=$(python manage.py shell -c "
from accounts.models import CustomUser, Subscription, Payment
from accounts.tbank_service import TBankService
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
import uuid, json

email = f'test_teacher_payment_{uuid.uuid4().hex[:8]}@lectio.space'
user = CustomUser.objects.create_user(email=email, password=uuid.uuid4().hex, role='teacher', first_name='Test', last_name='Teacher', is_active=True)
sub = Subscription.objects.create(user=user, plan=Subscription.PLAN_TRIAL, status=Subscription.STATUS_PENDING, expires_at=timezone.now(), base_storage_gb=10)

payment_id = str(900000000000 + (uuid.uuid4().int % 100000000000))
order_id = f'test-order-{uuid.uuid4().hex[:8]}'
Payment.objects.create(subscription=sub, amount=Decimal('990.00'), currency='RUB', status=Payment.STATUS_PENDING, payment_system='tbank', payment_id=payment_id, payment_url='', metadata={'plan':'monthly','order_id':order_id})

notification = {'TerminalKey': getattr(settings,'TBANK_TERMINAL_KEY',''), 'PaymentId': payment_id, 'Status': 'CONFIRMED', 'OrderId': order_id}
notification['Token'] = TBankService._generate_token(notification)
print(json.dumps(notification))
" | tail -n 1)

echo "Webhook payload: $PAYLOAD_JSON"

# 2) Дёргаем webhook endpoint локально (чтобы код выполнился в контексте gunicorn service)
HTTP_CODE=$(curl -sS -o /tmp/tbank_webhook_resp.txt -w "%{http_code}" \
  --resolve "lectio.space:443:127.0.0.1" \
  -X POST "https://lectio.space/api/payments/tbank/webhook/" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD_JSON")

echo "Webhook HTTP: $HTTP_CODE"
echo -n "Webhook body: "
cat /tmp/tbank_webhook_resp.txt || true
echo

# 3) Показываем последние строки логов по уведомлению админа
journalctl -u teaching_panel -n 200 --no-pager | egrep -i 'Admin payment notification|Failed to send admin payment notification|T-Bank notification: PaymentId' | tail -n 50 || true
