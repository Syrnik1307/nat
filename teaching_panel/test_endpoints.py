"""
Скрипт для тестирования основных endpoints проекта.
Проверяет регистрацию, авторизацию, Zoom Pool и запуск урока.
"""
import os
import django
import requests
from datetime import datetime, timedelta
from django.utils import timezone as django_timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from django.contrib.auth import get_user_model
from zoom_pool.models import ZoomAccount
from schedule.models import Group, Lesson

User = get_user_model()
BASE_URL = 'http://127.0.0.1:8000'

def test_register():
    """Тест регистрации пользователя"""
    print("\n=== Тест регистрации ===")
    url = f"{BASE_URL}/api/jwt/register/"
    data = {
        "email": f"test_teacher_{datetime.now().timestamp()}@example.com",
        "password": "TestPass123",
        "first_name": "Тест",
        "last_name": "Преподаватель",
        "role": "teacher"
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"Статус: {response.status_code}")
        print(f"Ответ: {response.json()}")
        
        if response.status_code == 201:
            print("✅ Регистрация прошла успешно")
            return data['email'], data['password']
        else:
            print("❌ Регистрация не удалась")
            return None, None
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None, None


def test_login(email, password):
    """Тест авторизации"""
    print("\n=== Тест авторизации ===")
    url = f"{BASE_URL}/api/jwt/token/"
    data = {
        "email": email,
        "password": password
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"Статус: {response.status_code}")
        
        if response.status_code == 200:
            tokens = response.json()
            print(f"✅ Авторизация успешна. Access token получен.")
            return tokens.get('access')
        else:
            print(f"❌ Авторизация не удалась: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None


def test_zoom_pool_stats(access_token):
    """Тест статистики Zoom Pool"""
    print("\n=== Тест статистики Zoom Pool ===")
    url = f"{BASE_URL}/api/zoom-pool/stats/"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Статус: {response.status_code}")
        
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Статистика получена:")
            print(f"   Всего аккаунтов: {stats.get('total', 0)}")
            print(f"   Активных: {stats.get('active', 0)}")
            print(f"   Доступных: {stats.get('available', 0)}")
            print(f"   Используется: {stats.get('in_use', 0)}")
            return True
        else:
            print(f"❌ Не удалось получить статистику: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


def create_test_data():
    """Создать тестовые данные в БД"""
    print("\n=== Создание тестовых данных ===")
    
    # Создать тестового учителя
    teacher_email = f"db_teacher_{datetime.now().timestamp()}@example.com"
    teacher = User.objects.create_user(
        email=teacher_email,
        password="TestPass123",
        first_name="Тест",
        last_name="Учитель",
        role="teacher"
    )
    print(f"✅ Создан учитель: {teacher.email}")
    
    # Создать Zoom аккаунт если нет
    if not ZoomAccount.objects.exists():
        zoom = ZoomAccount.objects.create(
            email="test_zoom@example.com",
            api_key="test_key_123",
            api_secret="test_secret_123",
            zoom_user_id="test_user_123",
            max_concurrent_meetings=2,
            is_active=True
        )
        print(f"✅ Создан Zoom аккаунт: {zoom.email}")
    else:
        zoom = ZoomAccount.objects.first()
        print(f"✅ Используется существующий Zoom аккаунт: {zoom.email}")
    
    # Создать группу
    group = Group.objects.create(
        name=f"Тестовая группа {datetime.now().strftime('%H:%M')}",
        teacher=teacher,
        description="Группа для тестирования"
    )
    print(f"✅ Создана группа: {group.name}")
    
    # Создать урок через 10 минут (чтобы можно было запустить за 15 мин до начала)
    start_time = django_timezone.now() + timedelta(minutes=10)
    end_time = start_time + timedelta(hours=1)
    
    lesson = Lesson.objects.create(
        title="Тестовый урок",
        group=group,
        teacher=teacher,
        start_time=start_time,
        end_time=end_time,
        topics="Тестирование системы",
        location="Онлайн"
    )
    print(f"✅ Создан урок: {lesson.title} в {start_time.strftime('%H:%M')}")
    
    return teacher.email, "TestPass123", lesson.id


def test_start_lesson(access_token, lesson_id):
    """Тест запуска урока"""
    print(f"\n=== Тест запуска урока #{lesson_id} ===")
    url = f"{BASE_URL}/api/schedule/lessons/{lesson_id}/start-new/"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        response = requests.post(url, headers=headers)
        print(f"Статус: {response.status_code}")
        
        if response.status_code in [200, 201]:
            data = response.json()
            print(f"✅ Урок запущен успешно:")
            print(f"   Zoom Meeting ID: {data.get('zoom_meeting_id')}")
            print(f"   Join URL: {data.get('zoom_join_url')[:50]}...")
            print(f"   Account: {data.get('account_email')}")
            return True
        elif response.status_code == 400:
            print(f"⚠️  Невозможно запустить: {response.json().get('detail')}")
            return False
        elif response.status_code == 503:
            print(f"⚠️  Все аккаунты заняты")
            return False
        else:
            print(f"❌ Ошибка: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


def test_rate_limit(access_token, lesson_id):
    """Тест rate limiting"""
    print(f"\n=== Тест rate limiting (4 попытки) ===")
    url = f"{BASE_URL}/api/schedule/lessons/{lesson_id}/start-new/"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    for i in range(4):
        try:
            response = requests.post(url, headers=headers)
            print(f"Попытка {i+1}: Статус {response.status_code}")
            
            if response.status_code == 429:
                print(f"✅ Rate limit сработал на попытке {i+1}")
                return True
        except Exception as e:
            print(f"Ошибка на попытке {i+1}: {e}")
    
    print("⚠️  Rate limit не сработал")
    return False


def main():
    """Основная функция тестирования"""
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ ENDPOINTS TEACHING PANEL")
    print("=" * 60)
    
    # Создать тестовые данные в БД
    teacher_email, password, lesson_id = create_test_data()
    
    # Тест авторизации
    access_token = test_login(teacher_email, password)
    if not access_token:
        print("\n❌ Тестирование прервано: не удалось войти")
        return
    
    # Тест Zoom Pool
    test_zoom_pool_stats(access_token)
    
    # Тест запуска урока
    test_start_lesson(access_token, lesson_id)
    
    # Тест rate limiting
    test_rate_limit(access_token, lesson_id)
    
    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 60)


if __name__ == '__main__':
    main()
