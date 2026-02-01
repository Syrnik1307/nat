"""
Одноразовый скрипт для сброса пароля пользователя ID 46 (guriev.dmitriy.y@gmail.com)
и снятия блокировки.

Запуск: python manage.py shell < reset_user46.py
ИЛИ: python -c "exec(open('reset_user46.py').read())"
"""
import os
import sys
import django

# Setup Django если запущен напрямую
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    django.setup()

from django.contrib.auth import get_user_model
from django.core.cache import cache

User = get_user_model()

TARGET_USER_ID = 46
NEW_PASSWORD = 'Guriev2026'

print("=" * 50)
print("СРОЧНЫЙ СБРОС ПАРОЛЯ + СНЯТИЕ БЛОКИРОВКИ")
print("=" * 50)

try:
    # Найти пользователя
    user = User.objects.get(pk=TARGET_USER_ID)
    print(f"Пользователь найден:")
    print(f"  ID: {user.id}")
    print(f"  Email: {user.email}")
    print(f"  Role: {user.role}")
    print(f"  Active: {user.is_active}")

    # Установить новый пароль
    user.set_password(NEW_PASSWORD)
    user.save()
    print(f"\nПароль изменён на: {NEW_PASSWORD}")

    # Сбросить блокировку в кеше
    email_lower = user.email.lower()
    fail_key = f'login_fail:{email_lower}'
    lock_key = f'login_lock:{email_lower}'
    cache.delete_many([fail_key, lock_key])
    print(f"\nКлючи кеша удалены:")
    print(f"  {fail_key}")
    print(f"  {lock_key}")

    # Проверка
    fresh_user = User.objects.get(pk=TARGET_USER_ID)
    password_ok = fresh_user.check_password(NEW_PASSWORD)
    lock_status = cache.get(lock_key)
    fail_count = cache.get(fail_key, 0)
    
    print(f"\nПроверка:")
    print(f"  Пароль корректен: {password_ok}")
    print(f"  Блокировка: {lock_status}")
    print(f"  Счётчик неудач: {fail_count}")
    
    if password_ok and lock_status is None:
        print("\n✓ УСПЕХ! Пользователь может войти с паролем: Guriev2026")
    else:
        print("\n✗ ОШИБКА! Проверьте вручную")

except User.DoesNotExist:
    print(f"ОШИБКА: Пользователь с ID {TARGET_USER_ID} не найден!")
except Exception as e:
    print(f"ОШИБКА: {e}")

print("=" * 50)
