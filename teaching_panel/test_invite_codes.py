"""
Тестирование системы инвайт-кодов
"""
import os
import django
import requests
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from django.contrib.auth import get_user_model
from schedule.models import Group

User = get_user_model()
BASE_URL = 'http://127.0.0.1:8000'

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

def test_teacher_login():
    """Получить токен учителя"""
    print_section("1. Авторизация учителя")
    
    url = f"{BASE_URL}/api/jwt/token/"
    data = {
        "email": "admin@school.com",
        "password": "admin123"
    }
    
    response = requests.post(url, json=data)
    print(f"Статус: {response.status_code}")
    
    if response.status_code == 200:
        tokens = response.json()
        print(f"✅ Токен получен")
        return tokens['access']
    else:
        print(f"❌ Ошибка: {response.text}")
        return None

def test_student_login():
    """Получить токен ученика или создать тестового ученика"""
    print_section("2. Авторизация ученика")
    
    # Попробуем найти существующего ученика
    students = User.objects.filter(role='student')
    if students.exists():
        student = students.first()
        print(f"Найден ученик: {student.email}")
    else:
        # Создадим тестового ученика
        print("Создаём тестового ученика...")
        email = f"test_student_{int(datetime.now().timestamp())}@example.com"
        student = User.objects.create_user(
            email=email,
            password="student123",
            first_name="Тест",
            last_name="Ученик",
            role="student"
        )
        print(f"Создан ученик: {student.email}")
    
    url = f"{BASE_URL}/api/jwt/token/"
    data = {
        "email": student.email,
        "password": "student123" if not students.exists() else "admin123"  # используем дефолтный пароль
    }
    
    response = requests.post(url, json=data)
    print(f"Статус: {response.status_code}")
    
    if response.status_code == 200:
        tokens = response.json()
        print(f"✅ Токен получен")
        return tokens['access'], student.email
    else:
        print(f"❌ Ошибка авторизации")
        # Попробуем создать нового ученика через API регистрации
        print("Регистрируем нового ученика через API...")
        reg_url = f"{BASE_URL}/api/jwt/register/"
        email = f"test_student_{int(datetime.now().timestamp())}@example.com"
        reg_data = {
            "email": email,
            "password": "TestPass123",
            "first_name": "Тестовый",
            "last_name": "Ученик",
            "role": "student"
        }
        reg_response = requests.post(reg_url, json=reg_data)
        if reg_response.status_code == 201:
            print(f"✅ Ученик создан: {email}")
            # Логинимся
            login_response = requests.post(url, json={"email": email, "password": "TestPass123"})
            if login_response.status_code == 200:
                tokens = login_response.json()
                return tokens['access'], email
        
        return None, None

def test_get_groups(token):
    """Получить список групп"""
    print_section("3. Получение списка групп")
    
    url = f"{BASE_URL}/api/groups/"
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(url, headers=headers)
    print(f"Статус: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        groups = data.get('results', [])
        print(f"✅ Найдено групп: {len(groups)}")
        for group in groups:
            print(f"\n  Группа: {group['name']}")
            print(f"  ID: {group['id']}")
            print(f"  Invite Code: {group['invite_code']}")
            print(f"  Учеников: {group['student_count']}")
        return groups
    else:
        print(f"❌ Ошибка: {response.text}")
        return []

def test_regenerate_code(token, group_id):
    """Регенерация инвайт-кода"""
    print_section("4. Регенерация инвайт-кода")
    
    url = f"{BASE_URL}/api/groups/{group_id}/regenerate_code/"
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.post(url, headers=headers)
    print(f"Статус: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Новый код: {data['invite_code']}")
        return data['invite_code']
    else:
        print(f"❌ Ошибка: {response.text}")
        return None

def test_join_group(token, invite_code, student_email):
    """Присоединение к группе по коду"""
    print_section("5. Присоединение ученика к группе")
    
    url = f"{BASE_URL}/api/groups/join_by_code/"
    headers = {"Authorization": f"Bearer {token}"}
    data = {"invite_code": invite_code}
    
    print(f"Ученик: {student_email}")
    print(f"Код: {invite_code}")
    
    response = requests.post(url, json=data, headers=headers)
    print(f"Статус: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Успешно присоединился к группе")
        print(f"  Группа: {data.get('group_name', data.get('name', 'N/A'))}")
        print(f"  ID: {data.get('group_id', data.get('id', 'N/A'))}")
        if 'student_count' in data:
            print(f"  Теперь учеников: {data['student_count']}")
        return True
    else:
        print(f"❌ Ошибка: {response.text}")
        return False

def test_student_groups(token):
    """Проверка групп ученика после присоединения"""
    print_section("6. Группы ученика после присоединения")
    
    url = f"{BASE_URL}/api/groups/"
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(url, headers=headers)
    print(f"Статус: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        groups = data.get('results', [])
        print(f"✅ Ученик состоит в группах: {len(groups)}")
        for group in groups:
            print(f"\n  Группа: {group['name']}")
            print(f"  Преподаватель: {group['teacher']['first_name']} {group['teacher']['last_name']}")
            print(f"  Учеников: {group['student_count']}")
        return groups
    else:
        print(f"❌ Ошибка: {response.text}")
        return []

def main():
    print("\n" + "="*60)
    print("  ТЕСТИРОВАНИЕ СИСТЕМЫ ИНВАЙТ-КОДОВ")
    print("="*60)
    
    # 1. Логин учителя
    teacher_token = test_teacher_login()
    if not teacher_token:
        print("\n❌ Не удалось авторизоваться как учитель")
        return
    
    # 2. Логин ученика
    student_token, student_email = test_student_login()
    if not student_token:
        print("\n❌ Не удалось авторизоваться как ученик")
        return
    
    # 3. Получить группы (от имени учителя)
    groups = test_get_groups(teacher_token)
    if not groups:
        print("\n❌ Нет доступных групп для теста")
        return
    
    # Берём первую группу
    group = groups[0]
    group_id = group['id']
    invite_code = group['invite_code']
    
    # 4. Регенерация кода (опционально)
    print("\nХотите регенерировать код? (y/n): ", end='')
    # Автоматически пропускаем
    print("n (автоматически)")
    
    # 5. Присоединение ученика
    success = test_join_group(student_token, invite_code, student_email)
    
    if success:
        # 6. Проверка групп ученика
        test_student_groups(student_token)
    
    print("\n" + "="*60)
    print("  ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("="*60 + "\n")

if __name__ == '__main__':
    main()
