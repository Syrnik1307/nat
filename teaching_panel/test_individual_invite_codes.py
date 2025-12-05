#!/usr/bin/env python
"""
Тест индивидуальных инвайт-кодов - Individual Invite Codes Testing
"""

import requests
import json
from datetime import datetime

BASE_URL = 'http://127.0.0.1:8000/api'

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_response(response, label="Response"):
    print(f"\n{label}:")
    print(f"Status: {response.status_code}")
    try:
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except:
        print(response.text[:500])

def main():
    print_section("ТЕСТИРОВАНИЕ ИНДИВИДУАЛЬНЫХ ИНВАЙТ-КОДОВ")
    
    # 1. Создание учителя
    print_section("1. Регистрация учителя")
    teacher_email = f"teacher_{datetime.now().timestamp():.0f}@test.com"
    teacher_data = {
        'email': teacher_email,
        'password': 'TestPass123!',
        'first_name': 'Иван',
        'last_name': 'Петров',
        'role': 'teacher'
    }
    
    resp = requests.post(f'{BASE_URL}/jwt/register/', json=teacher_data)
    print_response(resp, "Teacher Registration")
    
    if resp.status_code != 201 and resp.status_code != 200:
        print("❌ Ошибка регистрации учителя")
        return
    
    teacher_resp = resp.json()
    teacher_token = teacher_resp.get('access') or teacher_resp.get('access_token')
    teacher_id = teacher_resp.get('user', {}).get('id')
    print(f"\n✅ Учитель создан: {teacher_email}")
    print(f"   Token: {teacher_token[:50]}...")
    print(f"   ID: {teacher_id}")
    
    # 2. Создание ученика
    print_section("2. Регистрация ученика")
    student_email = f"student_{datetime.now().timestamp():.0f}@test.com"
    student_data = {
        'email': student_email,
        'password': 'TestPass123!',
        'first_name': 'Петр',
        'last_name': 'Сидоров',
        'role': 'student'
    }
    
    resp = requests.post(f'{BASE_URL}/jwt/register/', json=student_data)
    print_response(resp, "Student Registration")
    
    if resp.status_code not in [201, 200]:
        print("❌ Ошибка регистрации ученика")
        return
    
    student_resp = resp.json()
    student_token = student_resp.get('access') or student_resp.get('access_token')
    student_id = student_resp.get('user', {}).get('id')
    print(f"\n✅ Ученик создан: {student_email}")
    print(f"   Token: {student_token[:50]}...")
    print(f"   ID: {student_id}")
    
    # 3. Создание индивидуального инвайт-кода (учитель)
    print_section("3. Создание индивидуального инвайт-кода")
    
    headers = {'Authorization': f'Bearer {teacher_token}'}
    code_data = {'subject': 'Математика (Алгебра)'}
    
    resp = requests.post(f'{BASE_URL}/individual-invite-codes/', json=code_data, headers=headers)
    print_response(resp, "Create Individual Invite Code")
    
    if resp.status_code not in [201, 200]:
        print("❌ Ошибка создания кода")
        return
    
    code_obj = resp.json()
    invite_code = code_obj.get('invite_code')
    code_id = code_obj.get('id')
    print(f"\n✅ Инвайт-код создан: {invite_code}")
    print(f"   ID: {code_id}")
    print(f"   Предмет: {code_obj.get('subject')}")
    print(f"   Использован: {code_obj.get('is_used')}")
    
    # 4. Получение списка кодов учителя
    print_section("4. Получение списка индивидуальных кодов")
    
    resp = requests.get(f'{BASE_URL}/individual-invite-codes/', headers=headers)
    print_response(resp, "Teacher's Individual Invite Codes")
    
    if resp.status_code == 200:
        codes = resp.json().get('results', resp.json() if isinstance(resp.json(), list) else [])
        print(f"\n✅ Найдено кодов: {len(codes)}")
        for code in codes[:3]:
            print(f"   - {code.get('subject')}: {code.get('invite_code')} (использован: {code.get('is_used')})")
    
    # 5. Просмотр кода без присоединения
    print_section("5. Просмотр информации о коде")
    
    student_headers = {'Authorization': f'Bearer {student_token}'}
    resp = requests.get(f'{BASE_URL}/individual-invite-codes/preview_by_code/?code={invite_code}', headers=student_headers)
    print_response(resp, "Preview Individual Invite Code")
    
    if resp.status_code == 200:
        print("✅ Информация о коде получена")
    
    # 6. Присоединение ученика по коду
    print_section("6. Присоединение ученика по коду")
    
    join_data = {'invite_code': invite_code}
    resp = requests.post(f'{BASE_URL}/individual-invite-codes/join_by_code/', json=join_data, headers=student_headers)
    print_response(resp, "Join by Individual Invite Code")
    
    if resp.status_code == 200:
        result = resp.json()
        print(f"\n✅ Ученик присоединился!")
        print(f"   Сообщение: {result.get('message')}")
        print(f"   Предмет: {result.get('code', {}).get('subject')}")
        print(f"   Преподаватель: {result.get('teacher', {}).get('first_name')} {result.get('teacher', {}).get('last_name')}")
    else:
        print(f"\n❌ Ошибка присоединения: {resp.status_code}")
    
    # 7. Проверка что код помечен как использованный
    print_section("7. Проверка использования кода")
    
    resp = requests.get(f'{BASE_URL}/individual-invite-codes/', headers=headers)
    print_response(resp, "Check Code Status")
    
    if resp.status_code == 200:
        codes = resp.json().get('results', resp.json() if isinstance(resp.json(), list) else [])
        for code in codes:
            if code.get('invite_code') == invite_code:
                print(f"\n✅ Код статус:")
                print(f"   Использован: {code.get('is_used')}")
                print(f"   Использован учеником: {code.get('used_by_email')}")
                print(f"   Дата использования: {code.get('used_at')}")
    
    # 8. Попытка использовать код дважды (должна быть ошибка)
    print_section("8. Попытка использовать код дважды (должна быть ошибка)")
    
    join_data = {'invite_code': invite_code}
    resp = requests.post(f'{BASE_URL}/individual-invite-codes/join_by_code/', json=join_data, headers=student_headers)
    print_response(resp, "Second Join Attempt")
    
    if resp.status_code != 200:
        print(f"\n✅ Код ожидаемо отклонен: {resp.status_code}")
    else:
        print(f"\n⚠️  Код был принят (возможна допустимая логика)")
    
    # 9. Регенерация кода (создание нового)
    print_section("9. Создание еще одного кода и регенерация")
    
    code_data = {'subject': 'Физика'}
    resp = requests.post(f'{BASE_URL}/individual-invite-codes/', json=code_data, headers=headers)
    
    if resp.status_code in [201, 200]:
        code_obj = resp.json()
        code_id2 = code_obj.get('id')
        old_code = code_obj.get('invite_code')
        print(f"✅ Новый код создан: {old_code}")
        
        # Теперь регенерируем
        regen_data = {'id': code_id2}
        resp = requests.post(f'{BASE_URL}/individual-invite-codes/regenerate/', json=regen_data, headers=headers)
        print_response(resp, "Regenerate Code")
        
        if resp.status_code == 200:
            new_code = resp.json().get('code', {}).get('invite_code')
            print(f"\n✅ Код регенерирован:")
            print(f"   Старый: {old_code}")
            print(f"   Новый: {new_code}")
            print(f"   Разные: {old_code != new_code}")
    
    # 10. Удаление кода
    print_section("10. Удаление неиспользованного кода")
    
    if code_id2:
        resp = requests.delete(f'{BASE_URL}/individual-invite-codes/{code_id2}/', headers=headers)
        print_response(resp, "Delete Code")
        
        if resp.status_code == 204:
            print("\n✅ Код успешно удален")
        else:
            print(f"\n⚠️  Статус удаления: {resp.status_code}")
    
    # 11. Попытка удалить использованный код (должна быть ошибка)
    print_section("11. Попытка удалить использованный код (должна быть ошибка)")
    
    if code_id:
        resp = requests.delete(f'{BASE_URL}/individual-invite-codes/{code_id}/', headers=headers)
        print_response(resp, "Delete Used Code")
        
        if resp.status_code != 204:
            print(f"\n✅ Удаление корректно отклонено: {resp.status_code}")
        else:
            print(f"\n⚠️  Использованный код был удален (может быть позволено)")
    
    print_section("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО ✅")

if __name__ == '__main__':
    main()
