#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from django.contrib.auth import authenticate
from accounts.models import CustomUser

email = 'Syrnik1307@gmail.com'
password = 'Syrnik13'

print(f"=== Проверка аутентификации для {email} ===\n")

# 1. Проверяем существование пользователя
try:
    user = CustomUser.objects.get(email__iexact=email)
    print(f"✅ Пользователь найден: {user.email}")
    print(f"   ID: {user.id}")
    print(f"   Имя: {user.first_name} {user.last_name}")
    print(f"   Роль: {user.role}")
    print(f"   Активен: {user.is_active}")
    print(f"   Email подтверждён: {user.email_verified}")
    print(f"   Есть пароль: {user.has_usable_password()}")
    
    # 2. Проверяем пароль напрямую
    password_check = user.check_password(password)
    print(f"\n   Проверка пароля '{password}': {password_check}")
    
    # 3. Пробуем аутентификацию
    auth_user = authenticate(email=email, password=password)
    print(f"\n   Django authenticate(): {auth_user}")
    
    if not auth_user:
        print("\n❌ ОШИБКА: authenticate() вернул None")
        print("   Возможные причины:")
        print("   - Неправильный пароль")
        print("   - Пользователь не активен (is_active=False)")
        print("   - Кастомный бэкенд аутентификации блокирует вход")
        
        # Попробуем с точным email (без iexact)
        auth_user2 = authenticate(email=user.email, password=password)
        print(f"\n   Попытка с точным email: {auth_user2}")
        
except CustomUser.DoesNotExist:
    print(f"❌ Пользователь с email {email} не найден")
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
