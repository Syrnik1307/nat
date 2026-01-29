#!/bin/bash
cd /var/www/teaching_panel/teaching_panel
source ../venv/bin/activate
python -c "
import os
import time
import django

start = time.time()
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()
setup_time = time.time() - start
print(f'Django setup time: {setup_time*1000:.2f}ms')

from accounts.models import CustomUser
from homework.views import HomeworkViewSet
from django.test import RequestFactory

# Получаем студента
student = CustomUser.objects.filter(role='student').first()
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
qs_time = time.time() - start
print(f'Queryset build time: {qs_time*1000:.2f}ms')

start = time.time()
count = qs.count()
count_time = time.time() - start
print(f'Queryset count() time: {count_time*1000:.2f}ms')
print(f'Results count: {count}')

# Теперь проверим list() - материализация
start = time.time()
items = list(qs[:10])
list_time = time.time() - start
print(f'List first 10 time: {list_time*1000:.2f}ms')
print(f'Items fetched: {len(items)}')
" 2>&1
