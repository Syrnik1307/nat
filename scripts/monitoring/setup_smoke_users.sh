#!/bin/bash
# ============================================================
# СОЗДАНИЕ SMOKE TEST ПОЛЬЗОВАТЕЛЕЙ
# ============================================================
# Запускается один раз после установки мониторинга
# Создаёт тестовых teacher и student для smoke checks
#
# Использование: ./setup_smoke_users.sh
# ============================================================

set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/var/www/teaching_panel}"
PYTHON="${PROJECT_ROOT}/venv/bin/python"
MANAGE="${PROJECT_ROOT}/teaching_panel/manage.py"

echo "=============================================="
echo " СОЗДАНИЕ SMOKE TEST ПОЛЬЗОВАТЕЛЕЙ"
echo "=============================================="

cd "${PROJECT_ROOT}/teaching_panel"

# Создаём smoke_teacher
$PYTHON -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
import django
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

# Teacher
email = 'smoke_teacher@test.local'
if not User.objects.filter(email=email).exists():
    user = User.objects.create_user(
        email=email,
        password='SmokeTest123!',
        first_name='Smoke',
        last_name='Teacher',
        role='teacher',
        is_active=True
    )
    print(f'✓ Created teacher: {email}')
else:
    print(f'○ Teacher already exists: {email}')

# Student
email = 'smoke_student@test.local'
if not User.objects.filter(email=email).exists():
    user = User.objects.create_user(
        email=email,
        password='SmokeTest123!',
        first_name='Smoke',
        last_name='Student',
        role='student',
        is_active=True
    )
    print(f'✓ Created student: {email}')
else:
    print(f'○ Student already exists: {email}')

print('')
print('Smoke users ready!')
"

echo ""
echo "=============================================="
echo " ГОТОВО"
echo "=============================================="
echo ""
echo "Тестовые пользователи:"
echo "  Teacher: smoke_teacher@test.local / SmokeTest123!"
echo "  Student: smoke_student@test.local / SmokeTest123!"
echo ""
