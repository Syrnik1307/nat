#!/usr/bin/env python3
"""
Создание тестовых пользователей на сервере для проверки функционала.
"""
import requests
import json

BASE_URL = "http://72.56.81.163/api"

# Спробуем создать нового пользователя через регистрацию
test_credentials = {
    "email": f"teacher_test_{int(__import__('time').time())}@test.com",
    "password": "TestPassword123!",
    "password_confirm": "TestPassword123!",
    "first_name": "Test",
    "last_name": "Teacher"
}

print(f"Попытка регистрации: {test_credentials['email']}")
print("-" * 60)

r = requests.post(
    f"{BASE_URL}/jwt/register/",
    json=test_credentials,
    timeout=5
)

print(f"Статус: {r.status_code}")
print(f"Ответ: {json.dumps(r.json(), indent=2, ensure_ascii=False)}")

if r.status_code == 201 or r.status_code == 200:
    tokens = r.json()
    if 'access' in tokens:
        print(f"\n✅ Регистрация успешна!")
        print(f"Email: {test_credentials['email']}")
        print(f"Access Token: {tokens['access'][:50]}...")
        
        # Теперь используем токен для проверки API
        print("\n" + "-" * 60)
        print("Проверка API с авторизацией...")
        
        headers = {
            "Authorization": f"Bearer {tokens['access']}",
            "Content-Type": "application/json",
        }
        
        # Проверим /me/
        r = requests.get(f"{BASE_URL}/me/", headers=headers, timeout=5)
        if r.status_code == 200:
            me = r.json()
            print(f"✅ /me/ endpoint: {me.get('email')}")
        else:
            print(f"❌ /me/ вернул {r.status_code}")
        
        # Проверим группы
        r = requests.get(f"{BASE_URL}/groups/", headers=headers, timeout=5)
        if r.status_code == 200:
            groups = r.json()
            print(f"✅ /groups/ endpoint: {len(groups.get('results', []))} групп")
        else:
            print(f"❌ /groups/ вернул {r.status_code}")
        
        # Проверим индивидуальных учеников  
        r = requests.get(f"{BASE_URL}/individual-students/", headers=headers, timeout=5)
        if r.status_code == 200:
            students = r.json()
            print(f"✅ /individual-students/ endpoint: {len(students.get('results', []))} учеников")
        else:
            print(f"❌ /individual-students/ вернул {r.status_code}")
            
else:
    print(f"❌ Ошибка регистрации: {r.text}")
