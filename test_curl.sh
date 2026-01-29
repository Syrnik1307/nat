#!/bin/bash
cd /var/www/teaching_panel/teaching_panel
source ../venv/bin/activate

# Получаем токен студента
TOKEN=$(python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

User = get_user_model()
student = User.objects.filter(role='student').first()
refresh = RefreshToken.for_user(student)
print(str(refresh.access_token))
" 2>/dev/null)

echo "Token obtained for student"

# Делаем запрос через curl
echo "Testing /api/homework/..."
time curl -s -X GET "http://127.0.0.1:8000/api/homework/" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" | python -c "import sys,json; d=json.load(sys.stdin); print(f'Results: {len(d.get(\"results\", d) if isinstance(d, dict) else d)} items')"
