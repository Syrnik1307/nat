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

echo "Token: ${TOKEN:0:50}..."
echo "Token length: ${#TOKEN}"
echo ""

# Test directly to gunicorn with HTTP/1.0 to avoid issues
echo "=== Testing via gunicorn (HTTP/1.1) ==="
RESPONSE=$(curl -s --http1.1 -w '\n---HTTP_CODE:%{http_code}---' \
  "http://127.0.0.1:8000/schedule/api/storage/gdrive-stats/all/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json")

echo "$RESPONSE" | tail -20

echo ""
echo "=== Try external URL ==="
curl -s -w '\n---HTTP_CODE:%{http_code}---' \
  "https://lectio.tw1.ru/schedule/api/storage/gdrive-stats/all/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | tail -10
