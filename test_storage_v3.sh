#!/bin/bash
cd /var/www/teaching_panel/teaching_panel

echo "=== Getting admin token ==="
TOKEN=$(../venv/bin/python manage.py shell -c "
from rest_framework_simplejwt.tokens import RefreshToken
from accounts.models import CustomUser
u = CustomUser.objects.filter(role='admin').first()
if u:
    token = RefreshToken.for_user(u)
    print(str(token.access_token))
" 2>/dev/null | grep -E '^eyJ')

echo "Token prefix: ${TOKEN:0:40}..."
echo ""

# Test through nginx with correct host header
echo "=== Testing via nginx (with Host header) ==="
RESPONSE=$(curl -s -L -w '\n---HTTP_CODE:%{http_code}---' \
  "http://127.0.0.1/schedule/api/storage/gdrive-stats/all/" \
  -H "Host: lectio.tw1.ru" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json")

echo "$RESPONSE" | tail -20
