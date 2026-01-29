#!/bin/bash
cd /var/www/teaching_panel/teaching_panel
source ../venv/bin/activate
python -c "
import os
import django
import time
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from accounts.models import CustomUser
from homework.views import HomeworkViewSet
from django.test import RequestFactory

# Получаем студента
student = CustomUser.objects.filter(role='student').first()
if not student:
    print('No student found')
    exit(1)

print(f'Testing with student: {student.email} (id={student.id})')

# Создаем mock request
factory = RequestFactory()
request = factory.get('/api/homework/')
request.user = student

# Создаем viewset
viewset = HomeworkViewSet()
viewset.request = request
viewset.action = 'list'
viewset.format_kwarg = None

# Измеряем время queryset
start = time.time()
qs = viewset.get_queryset()
count = qs.count()
end = time.time()

print(f'Queryset execution time: {(end-start)*1000:.2f}ms')
print(f'Results count: {count}')

# Проверяем SQL запрос
from django.db import connection
print(f'Total queries: {len(connection.queries)}')
for q in connection.queries[-5:]:
    print(f'  - {q[\"time\"]}s: {q[\"sql\"][:100]}...')
"
