"""Тест регистрации пользователей через API"""
import requests
import json
from datetime import datetime

BASE_URL = 'http://127.0.0.1:8000'

def test_successful_registration():
    """Тест успешной регистрации"""
    print("\n=== Тест 1: Успешная регистрация ===")
    
    email = f"test_{int(datetime.now().timestamp())}@example.com"
    data = {
        "email": email,
        "password": "TestPass123",
        "first_name": "Иван",
        "last_name": "Тестовый",
        "role": "student",
        "birth_date": "2000-01-15"
    }
    
    response = requests.post(f"{BASE_URL}/api/jwt/register/", json=data)
    print(f"Статус: {response.status_code}")
    print(f"Ответ: {response.json()}")
    
    if response.status_code == 201:
        print("✅ Регистрация прошла успешно!")
        return email
    else:
        print("❌ Ошибка регистрации")
        return None


def test_duplicate_email():
    """Тест регистрации с существующим email"""
    print("\n=== Тест 2: Дубликат email ===")
    
    data = {
        "email": "test@example.com",
        "password": "TestPass123",
        "role": "student"
    }
    
    # Первая регистрация
    requests.post(f"{BASE_URL}/api/jwt/register/", json=data)
    
    # Вторая регистрация с тем же email
    response = requests.post(f"{BASE_URL}/api/jwt/register/", json=data)
    print(f"Статус: {response.status_code}")
    print(f"Ответ: {response.json()}")
    
    if response.status_code == 400 and "уже существует" in response.json().get('detail', ''):
        print("✅ Валидация дубликата работает!")
    else:
        print("❌ Валидация не сработала")


def test_weak_passwords():
    """Тест слабых паролей"""
    print("\n=== Тест 3: Слабые пароли ===")
    
    weak_passwords = [
        ("123", "короткий"),
        ("testtest", "нет заглавных и цифр"),
        ("TESTTEST", "нет строчных и цифр"),
        ("TestTest", "нет цифр"),
        ("test123", "нет заглавных"),
    ]
    
    for password, reason in weak_passwords:
        email = f"test_{int(datetime.now().timestamp())}@example.com"
        data = {
            "email": email,
            "password": password,
            "role": "student"
        }
        
        response = requests.post(f"{BASE_URL}/api/jwt/register/", json=data)
        print(f"\nПароль '{password}' ({reason})")
        print(f"Статус: {response.status_code}")
        
        if response.status_code == 400:
            print(f"✅ Отклонен: {response.json().get('detail')}")
        else:
            print(f"❌ Принят (ошибка валидации!)")


def test_login_after_registration():
    """Тест входа после регистрации"""
    print("\n=== Тест 4: Вход после регистрации ===")
    
    # Регистрация
    email = f"login_test_{int(datetime.now().timestamp())}@example.com"
    password = "TestPass123"
    
    reg_data = {
        "email": email,
        "password": password,
        "role": "teacher",
        "first_name": "Учитель",
        "last_name": "Тестовый"
    }
    
    reg_response = requests.post(f"{BASE_URL}/api/jwt/register/", json=reg_data)
    print(f"Регистрация: {reg_response.status_code}")
    
    if reg_response.status_code != 201:
        print("❌ Регистрация не удалась")
        return
    
    # Вход
    login_data = {
        "email": email,
        "password": password
    }
    
    login_response = requests.post(f"{BASE_URL}/api/jwt/token/", json=login_data)
    print(f"Вход: {login_response.status_code}")
    
    if login_response.status_code == 200:
        tokens = login_response.json()
        print(f"✅ Вход успешен! Access token получен (длина: {len(tokens.get('access', ''))})")
        
        # Проверка токена
        verify_response = requests.post(
            f"{BASE_URL}/api/jwt/verify/",
            json={"token": tokens.get('access')}
        )
        print(f"Верификация токена: {verify_response.status_code}")
        
        if verify_response.status_code == 200:
            print("✅ Токен валидный!")
        else:
            print("❌ Токен невалидный")
    else:
        print(f"❌ Вход не удался: {login_response.text}")


def test_missing_fields():
    """Тест обязательных полей"""
    print("\n=== Тест 5: Обязательные поля ===")
    
    test_cases = [
        ({}, "пустой запрос"),
        ({"email": "test@test.com"}, "без пароля"),
        ({"password": "TestPass123"}, "без email"),
        ({"email": "", "password": "TestPass123"}, "пустой email"),
    ]
    
    for data, description in test_cases:
        response = requests.post(f"{BASE_URL}/api/jwt/register/", json=data)
        print(f"\n{description}")
        print(f"Статус: {response.status_code}")
        
        if response.status_code == 400:
            print(f"✅ Отклонен: {response.json().get('detail')}")
        else:
            print(f"❌ Принят (ошибка валидации!)")


def main():
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ РЕГИСТРАЦИИ ПОЛЬЗОВАТЕЛЕЙ")
    print("=" * 60)
    
    try:
        test_successful_registration()
        test_duplicate_email()
        test_weak_passwords()
        test_login_after_registration()
        test_missing_fields()
        
        print("\n" + "=" * 60)
        print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")


if __name__ == '__main__':
    main()
