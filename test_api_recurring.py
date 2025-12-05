import requests
import json

# Логин
response = requests.post('http://127.0.0.1:8000/api/jwt/token/', json={
    'email': 'dev_teacher@test.com',
    'password': 'dev123'
})

if response.status_code != 200:
    print(f'❌ Login failed: {response.status_code}')
    print(response.text)
else:
    tokens = response.json()
    access_token = tokens['access']
    print(f'✅ Login successful')
    print(f'Token: {access_token[:30]}...')
    
    # Тестируем API с регулярными уроками
    headers = {'Authorization': f'Bearer {access_token}'}
    
    # Получаем уроки за декабрь (с регулярными)
    response = requests.get(
        'http://127.0.0.1:8000/api/schedule/lessons/',
        params={
            'include_recurring': 'true',
            'start': '2025-12-01',
            'end': '2025-12-31'
        },
        headers=headers
    )
    
    if response.status_code == 200:
        lessons = response.json()
        print(f'\n✅ Lessons API works!')
        print(f'Total lessons (including recurring expanded): {len(lessons) if isinstance(lessons, list) else lessons.get("count", 0)}')
        
        # Выводим регулярные уроки
        if isinstance(lessons, list):
            recurring_lessons = [l for l in lessons if l.get('is_recurring')]
        else:
            recurring_lessons = [l for l in lessons.get('results', []) if l.get('is_recurring')]
            
        print(f'Recurring lessons: {len(recurring_lessons)}')
        
        if recurring_lessons:
            print(f'\nFirst recurring lesson:')
            print(json.dumps(recurring_lessons[0], indent=2, default=str))
    else:
        print(f'❌ API error: {response.status_code}')
        print(response.text[:500])
