#!/bin/bash
cd /var/www/teaching_panel/teaching_panel
source ../venv/bin/activate

# Запускаем тестовый HTTP запрос через Django
python -c "
import os
import time
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from django.test import RequestFactory, Client
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()
student = User.objects.filter(role='student').first()

client = APIClient()
client.force_authenticate(user=student)

print(f'Testing with student: {student.email} (id={student.id})')

# Тест homework list
start = time.time()
response = client.get('/api/homework/')
elapsed = time.time() - start

print(f'Status: {response.status_code}')
print(f'Time: {elapsed*1000:.2f}ms')
if hasattr(response, 'data'):
    if isinstance(response.data, list):
        print(f'Results: {len(response.data)} items')
    elif 'results' in response.data:
        print(f'Results: {len(response.data[\"results\"])} items')
    else:
        print(f'Response: {response.data}')
" 2>&1
