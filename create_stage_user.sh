#!/bin/bash
cd /var/www/teaching-panel-stage/teaching_panel/teaching_panel
source ../../venv/bin/activate
export $(grep -v '^#' ../../.env.staging | xargs)
python manage.py shell << 'PYEOF'
from accounts.models import CustomUser
try:
    user = CustomUser.objects.get(email__iexact="Syrnik131313@gmail.com")
    print(f"User already exists: {user.email}")
except CustomUser.DoesNotExist:
    user = CustomUser.objects.create_user(
        email="Syrnik131313@gmail.com",
        password="Syrnik131313",
        first_name="Admin",
        last_name="Test",
        role="teacher"
    )
    user.is_staff = True
    user.is_superuser = True
    user.save()
    print(f"Created user: {user.email} (id={user.id}, role={user.role})")
PYEOF
