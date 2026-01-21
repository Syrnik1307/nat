#!/bin/bash
cd /var/www/teaching_panel/teaching_panel

# Get admin token
TOKEN=$(../venv/bin/python manage.py shell -c "
from rest_framework_simplejwt.tokens import RefreshToken
from accounts.models import User
u = User.objects.filter(role='admin').first()
if u:
    token = RefreshToken.for_user(u)
    print(str(token.access_token))
else:
    print('NO_ADMIN')
" 2>/dev/null)

echo "Token prefix: ${TOKEN:0:20}..."

# Test with -L to follow redirects
echo ""
echo "=== Testing with -L (follow redirects) ==="
curl -s -L -w '\n\nHTTP_CODE:%{http_code}' \
  "http://localhost:8000/schedule/api/storage/gdrive-stats/all/" \
  -H "Authorization: Bearer $TOKEN" | tail -30

echo ""
echo "=== Checking storage_views exists ==="
ls -la ../schedule/storage_views.py 2>/dev/null | head -2
