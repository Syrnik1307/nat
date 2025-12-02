#!/usr/bin/env python
"""Установка валидного пароля с заглавной буквой"""
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

# Установить пароль с заглавной буквой
new_password = 'Testpass123'
teacher.set_password(new_password)
teacher.save()

print(f"\n✓ Password updated to: {new_password}")
print("  (с заглавной буквы T)")

# Проверить
is_correct = teacher.check_password(new_password)
print(f"\nVerification: {'SUCCESS ✓' if is_correct else 'FAILED ✗'}")
