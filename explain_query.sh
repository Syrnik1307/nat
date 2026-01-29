#!/bin/bash
cd /var/www/teaching_panel/teaching_panel
source ../venv/bin/activate
python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from accounts.models import CustomUser
from homework.views import HomeworkViewSet
from django.test import RequestFactory

# Получаем студента
student = CustomUser.objects.filter(role='student').first()

# Создаем mock request
factory = RequestFactory()
request = factory.get('/api/homework/')
request.user = student

# Создаем viewset
viewset = HomeworkViewSet()
viewset.request = request
viewset.action = 'list'
viewset.format_kwarg = None

# Получаем queryset
qs = viewset.get_queryset()

# Выводим SQL
print('=== SQL Query ===')
print(qs.query)
print()

# Проверим EXPLAIN ANALYZE
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute('EXPLAIN ANALYZE ' + str(qs.query))
    print('=== EXPLAIN ANALYZE ===')
    for row in cursor.fetchall():
        print(row[0])
" 2>&1
