"""
Получить User ID текущего Zoom аккаунта
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from schedule.zoom_client import ZoomAPIClient
import requests

client = ZoomAPIClient()

try:
    # Получаем OAuth токен
    token = client._get_access_token()
    print(f"✅ OAuth токен получен: {token[:20]}...\n")
    
    # Получаем информацию о текущем пользователе
    response = requests.get(
        f'{client.BASE_URL}/users/me',
        headers={'Authorization': f'Bearer {token}'},
        timeout=10
    )
    
    response.raise_for_status()
    user_data = response.json()
    
    print("=" * 60)
    print("📋 Информация о Zoom аккаунте:")
    print("=" * 60)
    print(f"User ID: {user_data['id']}")
    print(f"Email: {user_data['email']}")
    print(f"First Name: {user_data.get('first_name', 'N/A')}")
    print(f"Last Name: {user_data.get('last_name', 'N/A')}")
    print(f"Type: {user_data.get('type', 'N/A')}")
    print(f"Status: {user_data.get('status', 'N/A')}")
    print("=" * 60)
    
    print(f"\n✅ Используйте этот User ID: {user_data['id']}")
    print(f"✅ Или просто используйте 'me' - Zoom API поддерживает это значение")
    
    # Обновляем аккаунт в БД
    from zoom_pool.models import ZoomAccount
    
    zoom_account = ZoomAccount.objects.first()
    if zoom_account:
        zoom_account.email = user_data['email']
        zoom_account.zoom_user_id = user_data['id']  # или 'me'
        zoom_account.save()
        print(f"\n✅ Zoom аккаунт обновлен в БД (ID: {zoom_account.id})")
    
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
