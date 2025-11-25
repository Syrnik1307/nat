# Скрипт для генерации нового SECRET_KEY
# Запустите: python generate_secret_key.py

from django.core.management.utils import get_random_secret_key
import os
from pathlib import Path

print("=" * 60)
print("🔐 Генератор SECRET_KEY для Django")
print("=" * 60)
print()

# Генерируем новый ключ
new_secret_key = get_random_secret_key()

print("✅ Новый SECRET_KEY успешно сгенерирован!")
print()
print("📋 Скопируйте следующую строку в ваш .env файл:")
print("-" * 60)
print(f"SECRET_KEY={new_secret_key}")
print("-" * 60)
print()

# Проверяем существование .env файла
env_path = Path(__file__).parent / '.env'

if env_path.exists():
    print(f"📁 Файл .env найден: {env_path}")
    print()
    response = input("❓ Хотите автоматически обновить .env файл? (y/N): ")
    
    if response.lower() in ('y', 'yes', 'д', 'да'):
        try:
            # Читаем текущий .env
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Обновляем SECRET_KEY
            updated = False
            for i, line in enumerate(lines):
                if line.startswith('SECRET_KEY='):
                    old_key = line.strip().split('=', 1)[1] if '=' in line else ''
                    lines[i] = f"SECRET_KEY={new_secret_key}\n"
                    updated = True
                    print(f"✅ SECRET_KEY обновлен!")
                    if old_key.startswith('django-insecure'):
                        print("   (Заменен небезопасный дефолтный ключ)")
                    break
            
            if not updated:
                # Добавляем в начало файла если не нашли
                lines.insert(0, f"SECRET_KEY={new_secret_key}\n")
                print("✅ SECRET_KEY добавлен в .env файл!")
            
            # Сохраняем
            with open(env_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            print()
            print("🎉 Готово! Перезапустите Django сервер для применения изменений.")
            
        except Exception as e:
            print(f"❌ Ошибка при обновлении файла: {e}")
            print("   Скопируйте ключ вручную из строки выше.")
    else:
        print("ℹ️  Скопируйте ключ вручную в .env файл.")
else:
    print(f"⚠️  Файл .env не найден: {env_path}")
    print("   Создайте файл .env и скопируйте строку выше.")

print()
print("=" * 60)
print("📚 Дополнительная информация:")
print("   - SECURITY_QUICK_START.md - Быстрый старт")
print("   - SECURITY_AUDIT_REPORT.md - Полный отчет")
print("=" * 60)
