import requests
import json
from datetime import datetime, timedelta

# Логин
response = requests.post('http://127.0.0.1:8000/api/jwt/token/', json={
    'email': 'dev_teacher@test.com',
    'password': 'dev123'
})

tokens = response.json()
access_token = tokens['access']
headers = {'Authorization': f'Bearer {access_token}'}

# Тест 1: Расписание на сегодня (как делает TeacherHomePage)
today = datetime.now().strftime('%Y-%m-%d')
print(f'\n=== Test 1: Today lessons (date={today}) ===')
response = requests.get(
    'http://127.0.0.1:8000/api/schedule/lessons/',
    params={'date': today, 'include_recurring': 'true'},
    headers=headers
)
print(f'Status: {response.status_code}')
lessons = response.json()
print(f'Type: {type(lessons).__name__}')
print(f'Count: {len(lessons) if isinstance(lessons, list) else lessons.get("count", "N/A")}')

if isinstance(lessons, list) and lessons:
    print(f'\nFirst lesson:')
    print(json.dumps(lessons[0], indent=2, default=str))

# Тест 2: Расписание на месяц (как делает Calendar)
start_date = (datetime.now().replace(day=1)).strftime('%Y-%m-%d')
end_date = ((datetime.now().replace(day=1) + timedelta(days=90)).replace(day=1) - timedelta(days=1)).strftime('%Y-%m-%d')

print(f'\n\n=== Test 2: Month lessons (start={start_date}, end={end_date}) ===')
response = requests.get(
    'http://127.0.0.1:8000/api/schedule/lessons/',
    params={'include_recurring': 'true', 'start': start_date, 'end': end_date},
    headers=headers
)
print(f'Status: {response.status_code}')
lessons = response.json()
print(f'Type: {type(lessons).__name__}')
print(f'Count: {len(lessons) if isinstance(lessons, list) else lessons.get("count", "N/A")}')

# Посчитаем регулярные уроки
if isinstance(lessons, list):
    recurring_count = sum(1 for l in lessons if l.get('is_recurring'))
else:
    recurring_count = sum(1 for l in lessons.get('results', []) if l.get('is_recurring'))
print(f'Regular lessons: {recurring_count}')

# Тест 3: Без регулярных (только реальные уроки)
print(f'\n\n=== Test 3: Without recurring (start={start_date}, end={end_date}) ===')
response = requests.get(
    'http://127.0.0.1:8000/api/schedule/lessons/',
    params={'include_recurring': 'false', 'start': start_date, 'end': end_date},
    headers=headers
)
print(f'Status: {response.status_code}')
lessons = response.json()
print(f'Type: {type(lessons).__name__}')
if isinstance(lessons, dict):
    print(f'Count: {lessons.get("count", "N/A")}')
    print(f'Has pagination: {bool(lessons.get("results"))}')
    print(f'Results: {len(lessons.get("results", []))}')
else:
    print(f'Count: {len(lessons)}')

print('\n✅ All tests completed!')
