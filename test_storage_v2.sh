#!/bin/bash
cd /var/www/teaching_panel/teaching_panel

echo "=== Getting admin user and token ==="
TOKEN=$(../venv/bin/python manage.py shell <<'EOF'
from rest_framework_simplejwt.tokens import RefreshToken
from accounts.models import CustomUser
u = CustomUser.objects.filter(role='admin').first()
if u:
    print(f"Admin: {u.email}")
    token = RefreshToken.for_user(u)
    print(str(token.access_token))
else:
    print("NO_ADMIN")
EOF
2>&1 | tail -1)

echo "Token prefix: ${TOKEN:0:40}..."
echo ""

# Test through nginx (external)
echo "=== Testing via localhost:8000 (Gunicorn) ==="
curl -s -L -w '\nHTTP_CODE:%{http_code}' \
  "http://localhost:8000/schedule/api/storage/gdrive-stats/all/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | tail -10

echo ""
echo "=== Testing via nginx (127.0.0.1:80) ==="
curl -s -L -w '\nHTTP_CODE:%{http_code}' \
  "http://127.0.0.1/schedule/api/storage/gdrive-stats/all/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | tail -10
