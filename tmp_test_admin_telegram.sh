#!/bin/bash
set -e
cd /var/www/teaching_panel/teaching_panel
source ../venv/bin/activate
python manage.py shell <<'EOF'
from django.conf import settings
import requests

chat_id = getattr(settings, 'ADMIN_PAYMENT_TELEGRAM_CHAT_ID', '')
token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
print('chat_id set:', bool(chat_id))
print('token set:', bool(token))

url = f"https://api.telegram.org/bot{token}/sendMessage"
payload = {
    'chat_id': chat_id,
    'text': 'Тест: уведомления об оплатах для админа включены.',
    'disable_web_page_preview': True,
}
resp = requests.post(url, json=payload, timeout=10)
print('status_code:', resp.status_code)
try:
    print('json:', resp.json())
except Exception:
    print('text:', resp.text[:500])
EOF
