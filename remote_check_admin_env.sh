#!/bin/bash
set -euo pipefail

ENV=$(systemctl show teaching_panel.service -p Environment --value)
getvar(){ printf "%s" "$ENV" | tr " " "\n" | sed -n "s/^$1=//p" | tail -n 1; }

export TELEGRAM_BOT_TOKEN="$(getvar TELEGRAM_BOT_TOKEN)"
export TELEGRAM_BOT_USERNAME="$(getvar TELEGRAM_BOT_USERNAME)"
export ADMIN_PAYMENT_TELEGRAM_CHAT_ID="$(getvar ADMIN_PAYMENT_TELEGRAM_CHAT_ID)"

echo "bash ADMIN_PAYMENT_TELEGRAM_CHAT_ID: ${ADMIN_PAYMENT_TELEGRAM_CHAT_ID:-EMPTY}"

cd /var/www/teaching_panel/teaching_panel
source ../venv/bin/activate

python manage.py shell <<'PYEOF'
from django.conf import settings
import os
import teaching_panel.settings as project_settings

def mask(s: str) -> str:
    if not s:
        return 'EMPTY'
    if len(s) <= 8:
        return s
    return s[:6] + '…' + s[-4:]

print('settings.TELEGRAM_BOT_TOKEN:', mask(getattr(settings,'TELEGRAM_BOT_TOKEN','')))
print('settings.TELEGRAM_BOT_USERNAME:', getattr(settings,'TELEGRAM_BOT_USERNAME','') or 'EMPTY')
print('settings.ADMIN_PAYMENT_TELEGRAM_CHAT_ID:', getattr(settings,'ADMIN_PAYMENT_TELEGRAM_CHAT_ID','') or 'EMPTY')
print('os.environ ADMIN_PAYMENT_TELEGRAM_CHAT_ID:', os.environ.get('ADMIN_PAYMENT_TELEGRAM_CHAT_ID') or 'EMPTY')
print('module teaching_panel.settings.ADMIN_PAYMENT_TELEGRAM_CHAT_ID:', getattr(project_settings,'ADMIN_PAYMENT_TELEGRAM_CHAT_ID','MISSING') or 'EMPTY')
print('module teaching_panel.settings.__file__:', getattr(project_settings, '__file__', 'UNKNOWN'))
PYEOF
