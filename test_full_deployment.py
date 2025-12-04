#!/usr/bin/env python3
"""
Полный тест развёрнутого фронтенда и API на продакшене.
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://72.56.81.163/api"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
}

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def test_api():
    """Тестирует все критические API эндпоинты."""
    
    log("=" * 60)
    log("ПОЛНЫЙ ТЕСТ РАЗВЁРНУТОГО ПРИЛОЖЕНИЯ")
    log("=" * 60)
    
    # 1. Проверим доступность frontend'а
    log("\n1️⃣ Проверка доступности фронтенда...")
    try:
        r = requests.get("http://72.56.81.163/", timeout=5)
        if r.status_code == 200:
            log(f"✅ Фронтенд доступен (статус: {r.status_code})")
            # Проверим наличие главного JS файла
            if "main.69776127.js" in r.text:
                log("✅ Найден новый JS bundle (main.69776127.js)")
            else:
                log("❌ Не найден JS bundle в index.html")
        else:
            log(f"❌ Фронтенд вернул {r.status_code}")
    except Exception as e:
        log(f"❌ Ошибка подключения: {e}")
    
    # 2. Проверим API доступ без авторизации (должно быть 401 или 403)
    log("\n2️⃣ Проверка доступности API (без авторизации)...")
    try:
        r = requests.get(f"{BASE_URL}/groups/", timeout=5)
        if r.status_code in [401, 403]:
            log(f"✅ API требует авторизацию (статус: {r.status_code})")
        elif r.status_code == 200:
            log(f"⚠️  API доступен без авторизации (статус: {r.status_code})")
        else:
            log(f"❌ API вернул {r.status_code}")
    except Exception as e:
        log(f"❌ Ошибка подключения к API: {e}")
    
    # 3. Проверим доступ с JWT токеном (используем существующего учителя)
    log("\n3️⃣ Попытка авторизации с учителем...")
    try:
        # Используем существующие credentials из create_test_data_for_attendance.py
        login_data = {
            "email": "teacher@example.com",
            "password": "password123"
        }
        r = requests.post(
            f"{BASE_URL}/jwt/token/",
            json=login_data,
            headers=HEADERS,
            timeout=5
        )
        if r.status_code == 200:
            tokens = r.json()
            access_token = tokens.get("access")
            log(f"✅ Авторизация успешна")
            log(f"   Токен получен: {access_token[:20]}...")
            
            # 4. С токеном проверим API
            log("\n4️⃣ Проверка API с авторизацией...")
            auth_headers = {**HEADERS, "Authorization": f"Bearer {access_token}"}
            
            # Проверим группы
            r = requests.get(f"{BASE_URL}/groups/", headers=auth_headers, timeout=5)
            if r.status_code == 200:
                groups = r.json()
                group_count = len(groups.get("results", []))
                log(f"✅ Группы загружены: {group_count} найдено")
                
                # Если есть группы, проверим эндпоинты для посещений
                if group_count > 0:
                    group_id = groups["results"][0]["id"]
                    log(f"\n5️⃣ Проверка эндпоинтов для группы {group_id}...")
                    
                    # Журнал посещений
                    r = requests.get(
                        f"{BASE_URL}/groups/{group_id}/attendance-log/",
                        headers=auth_headers,
                        timeout=5
                    )
                    if r.status_code == 200:
                        log(f"✅ Журнал посещений: {len(r.json().get('results', []))} записей")
                    else:
                        log(f"❌ Журнал посещений вернул {r.status_code}")
                    
                    # Рейтинг
                    r = requests.get(
                        f"{BASE_URL}/groups/{group_id}/rating/",
                        headers=auth_headers,
                        timeout=5
                    )
                    if r.status_code == 200:
                        log(f"✅ Рейтинг: {len(r.json().get('results', []))} записей")
                    else:
                        log(f"❌ Рейтинг вернул {r.status_code}")
                    
                    # Отчёты
                    r = requests.get(
                        f"{BASE_URL}/groups/{group_id}/report/",
                        headers=auth_headers,
                        timeout=5
                    )
                    if r.status_code == 200:
                        log(f"✅ Отчеты: загружены")
                    else:
                        log(f"❌ Отчеты вернули {r.status_code}")
                        
            else:
                log(f"❌ Группы вернули {r.status_code}: {r.text}")
                
        else:
            log(f"❌ Авторизация не удалась ({r.status_code})")
            log(f"   Ответ: {r.text[:200]}")
    except Exception as e:
        log(f"❌ Ошибка авторизации: {e}")
    
    # 5. Проверим индивидуальных учеников
    log("\n6️⃣ Проверка индивидуальных учеников...")
    try:
        if 'auth_headers' in locals():
            r = requests.get(
                f"{BASE_URL}/individual-students/",
                headers=auth_headers,
                timeout=5
            )
            if r.status_code == 200:
                students = r.json()
                count = len(students.get("results", []))
                log(f"✅ Индивидуальные ученики: {count} найдено")
            else:
                log(f"❌ Индивидуальные ученики вернули {r.status_code}")
    except Exception as e:
        log(f"❌ Ошибка при получении индивидуальных учеников: {e}")
    
    log("\n" + "=" * 60)
    log("ТЕСТ ЗАВЕРШЁН")
    log("=" * 60)

if __name__ == "__main__":
    test_api()
