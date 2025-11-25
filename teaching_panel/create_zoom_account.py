"""
Скрипт для создания Zoom аккаунта в пуле
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from zoom_pool.models import ZoomAccount

# Создаем основной Zoom аккаунт
zoom_account = ZoomAccount.objects.create(
    email='main@yourschool.com',
    api_key='vNl9EzZTy6h2UifsGVERg',  # Client ID
    api_secret='jqMJb4R3UgOQ1Q2FEHtkv6Tkz3CxNX87',  # Client Secret
    zoom_user_id='me',  # Используем 'me' для текущего аккаунта
    max_concurrent_meetings=1,
    is_active=True
)

print("\n" + "="*60)
print("✅ Zoom аккаунт создан успешно!")
print("="*60)
print(f"Email: {zoom_account.email}")
print(f"ID: {zoom_account.id}")
print(f"Max concurrent meetings: {zoom_account.max_concurrent_meetings}")
print(f"Active: {zoom_account.is_active}")
print("="*60 + "\n")
print("Теперь можно начинать занятия! 🎉")
print("Преподаватели смогут нажать '▶️ Начать занятие' на главной странице.")
