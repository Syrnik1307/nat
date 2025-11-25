"""
Тестовый скрипт для проверки подключения к Zoom API
Запуск: python manage.py shell < test_zoom_connection.py
Или: python test_zoom_connection.py
"""
import os
import sys
import django

# Настройка Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from schedule.zoom_client import my_zoom_api_client
from datetime import datetime, timedelta

def test_zoom_connection():
    """Тест подключения к Zoom API"""
    print("\n" + "="*60)
    print("🔍 Тестирование подключения к Zoom API")
    print("="*60 + "\n")
    
    try:
        # Шаг 1: Получение OAuth токена
        print("📡 Шаг 1: Получение OAuth токена...")
        token = my_zoom_api_client._get_access_token()
        print(f"✅ Токен получен: {token[:20]}...")
        
        # Шаг 2: Создание тестовой встречи
        print("\n📅 Шаг 2: Создание тестовой встречи...")
        start_time = datetime.now() + timedelta(hours=1)
        
        meeting_data = my_zoom_api_client.create_meeting(
            user_id='me',
            topic='Тестовая встреча - Teaching Panel',
            start_time=start_time,
            duration=30
        )
        
        print(f"✅ Встреча создана успешно!")
        print(f"   Meeting ID: {meeting_data['id']}")
        print(f"   Start URL: {meeting_data['start_url'][:50]}...")
        print(f"   Join URL: {meeting_data['join_url'][:50]}...")
        print(f"   Password: {meeting_data.get('password', 'Нет пароля')}")
        
        print("\n" + "="*60)
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Zoom API работает корректно.")
        print("="*60 + "\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {str(e)}")
        print("\n" + "="*60)
        print("Возможные причины:")
        print("1. Неверные credentials (Account ID, Client ID, Client Secret)")
        print("2. Недостаточные права (scopes) в Zoom App")
        print("3. Проблема с интернет-соединением")
        print("="*60 + "\n")
        return False


if __name__ == '__main__':
    success = test_zoom_connection()
    sys.exit(0 if success else 1)
