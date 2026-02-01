#!/bin/bash
# Скрипт для выполнения на продакшн сервере
cd /var/www/teaching_panel/teaching_panel
source ../venv/bin/activate

python manage.py shell << 'EOF'
from django.contrib.auth import get_user_model
from django.core.cache import cache

User = get_user_model()
TARGET_USER_ID = 46
NEW_PASSWORD = 'Guriev2026'

try:
    user = User.objects.get(pk=TARGET_USER_ID)
    print(f"User found: {user.email} (ID: {user.id}, role: {user.role})")
    
    # Set new password
    user.set_password(NEW_PASSWORD)
    user.save()
    print(f"Password changed to: {NEW_PASSWORD}")
    
    # Clear lockout cache
    email_lower = user.email.lower()
    fail_key = f'login_fail:{email_lower}'
    lock_key = f'login_lock:{email_lower}'
    cache.delete_many([fail_key, lock_key])
    print(f"Cache keys deleted: {fail_key}, {lock_key}")
    
    # Verify
    fresh = User.objects.get(pk=TARGET_USER_ID)
    ok = fresh.check_password(NEW_PASSWORD)
    print(f"Password verify: {ok}")
    print("SUCCESS!" if ok else "FAILED!")
    
except User.DoesNotExist:
    print(f"ERROR: User ID {TARGET_USER_ID} not found!")
except Exception as e:
    print(f"ERROR: {e}")
EOF
