#!/usr/bin/env python
"""Проверка пароля пользователя"""
import os
import sys
import django

sys.path.insert(0, '/var/www/teaching_panel/teaching_panel')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from accounts.models import CustomUser

teacher = CustomUser.objects.get(email='syrnik131313@gmail.com')
print(f"User: {teacher.email}")
print(f"Role: {teacher.role}")
print(f"Is active: {teacher.is_active}")

# Проверить пароль
test_password = 'testpass123'
is_correct = teacher.check_password(test_password)
print(f"\nPassword '{test_password}' is {'CORRECT' if is_correct else 'WRONG'}")

if not is_correct:
    print("\nSetting new password...")
    teacher.set_password(test_password)
    teacher.save()
    print("✓ Password updated to 'testpass123'")
    
    # Проверить снова
    is_correct_now = teacher.check_password(test_password)
    print(f"Verification: {'SUCCESS' if is_correct_now else 'FAILED'}")
