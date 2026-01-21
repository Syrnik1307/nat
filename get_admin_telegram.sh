#!/bin/bash
cd /var/www/teaching_panel/teaching_panel
source ../venv/bin/activate
python manage.py shell <<'EOF'
from accounts.models import CustomUser
u = CustomUser.objects.get(email='syromyatnikovnk@gmail.com')
print(f"id: {u.id}")
print(f"telegram_id: {u.telegram_id}")
print(f"is_superuser: {u.is_superuser}")
EOF
