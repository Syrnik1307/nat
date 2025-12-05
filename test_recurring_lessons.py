#!/usr/bin/env python
"""Тест API регулярных уроков"""
import requests
import json
from datetime import datetime, timedelta

# Получаем токен
response = requests.post('http://localhost:8000/api/jwt/token/', json={
    'email': 'test_teacher@example.com',
    'password': 'test123'
})

if response.status_code != 200:
    print('❌ Ошибка получения токена:', response.status_code)
    print(response.text)
    exit(1)

data = response.json()
token = data['access']
print(f'✅ Токен получен')

# Получаем уроки с include_recurring=true и диапазоном дат
headers = {'Authorization': f'Bearer {token}'}

now = datetime.now()
start_date = now.strftime('%Y-%m-%d')
end_date = (now + timedelta(days=30)).strftime('%Y-%m-%d')

url = f'http://localhost:8000/api/schedule/lessons/?include_recurring=true&start={start_date}&end={end_date}'
print(f'📌 Запрос: {url}')

response = requests.get(url, headers=headers)
print(f'Статус: {response.status_code}')

if response.status_code == 200:
    lessons = response.json()
    print(f'✅ Получено уроков: {len(lessons)}')
    
    # Показываем регулярные уроки
    recurring_lessons = [l for l in lessons if l.get('is_recurring', False)]
    print(f'📅 Регулярных уроков: {len(recurring_lessons)}')
    
    if recurring_lessons:
        print('\n📚 Первые регулярные уроки:')
        for lesson in recurring_lessons[:3]:
            start_time = lesson.get('start_time', '')
            end_time = lesson.get('end_time', '')
            title = lesson.get('title', 'N/A')
            print(f'  - {title}')
            print(f'    Начало: {start_time}')
            print(f'    Конец: {end_time}')
    
    # Проверим структуру первого урока
    if lessons:
        print(f'\n📋 Структура первого урока:')
        print(json.dumps(lessons[0], indent=2, ensure_ascii=False)[:500])
else:
    print(f'❌ Ошибка: {response.text}')
