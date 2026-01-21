#!/bin/bash
cd /var/www/teaching_panel/teaching_panel

echo "=== Checking admin user ==="
../venv/bin/python manage.py shell <<'EOF'
from accounts.models import User
admins = User.objects.filter(role='admin')
print(f"Admin count: {admins.count()}")
for a in admins[:3]:
    print(f"  {a.id}: {a.email}")
EOF

echo ""
echo "=== Getting token ==="
TOKEN=$(../venv/bin/python manage.py shell <<'EOF'
from rest_framework_simplejwt.tokens import RefreshToken
from accounts.models import User
u = User.objects.filter(role='admin').first()
if u:
    token = RefreshToken.for_user(u)
    print(str(token.access_token))
EOF
)

echo "Token length: ${#TOKEN}"
echo "Token prefix: ${TOKEN:0:30}..."

echo ""
echo "=== Testing API endpoint ==="
RESP=$(curl -s -L -w '\n---HTTP_CODE:%{http_code}---' \
  "http://localhost:8000/schedule/api/storage/gdrive-stats/all/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json")

echo "$RESP"
