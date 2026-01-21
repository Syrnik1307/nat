#!/bin/bash
set -euo pipefail

PAYMENT_ID="$1"

ENV=$(systemctl show teaching_panel.service -p Environment --value)
getvar(){ printf "%s" "$ENV" | tr " " "\n" | sed -n "s/^$1=//p" | tail -n 1; }

export TELEGRAM_BOT_TOKEN="$(getvar TELEGRAM_BOT_TOKEN)"
export TELEGRAM_BOT_USERNAME="$(getvar TELEGRAM_BOT_USERNAME)"
export ADMIN_PAYMENT_TELEGRAM_CHAT_ID="$(getvar ADMIN_PAYMENT_TELEGRAM_CHAT_ID)"

cd /var/www/teaching_panel/teaching_panel
source ../venv/bin/activate

python manage.py shell <<PYEOF
from accounts.models import Payment
from accounts.notifications import notify_admin_payment

p = Payment.objects.select_related('subscription','subscription__user').get(payment_id='${PAYMENT_ID}')
sub = p.subscription
ok = notify_admin_payment(p, sub, plan_name=(p.metadata or {}).get('plan'))
print('notify_ok:', ok)
PYEOF
