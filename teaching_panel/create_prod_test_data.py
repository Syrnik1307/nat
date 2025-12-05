#!/usr/bin/env python
"""Создание тестовых данных на production"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from accounts.models import CustomUser
from schedule.models import Group, RecurringLesson
from django.utils import timezone
from datetime import time, timedelta

# Получаем или создаем тестового учителя
teacher, created = CustomUser.objects.get_or_create(
    email='prod_test_teacher@example.com',
    defaults={
        'first_name': 'Prod',
        'last_name': 'Teacher',
        'role': 'teacher'
    }
)
if created:
    teacher.set_password('test123')
    teacher.save()
    print(f'✅ Created teacher: {teacher.email}')
else:
    print(f'✅ Teacher exists: {teacher.email}')

# Получаем или создаем тестовую группу
group, created = Group.objects.get_or_create(
    name='ProdTestGroup',
    defaults={'teacher': teacher}
)
print(f'✅ Group: {group.name} (ID: {group.id})')

# Создаем регулярный урок
recurring, created = RecurringLesson.objects.get_or_create(
    title='Prod Regular Lesson - Monday',
    group=group,
    teacher=teacher,
    day_of_week=0,
    defaults={
        'start_time': time(15, 0),
        'end_time': time(16, 30),
        'week_type': 'ALL',
        'start_date': timezone.now().date(),
        'end_date': (timezone.now() + timedelta(days=90)).date(),
    }
)
print(f'✅ Recurring lesson: {recurring.title} (ID: {recurring.id})')
print(f'   Time: {recurring.start_time} - {recurring.end_time}')
print(f'   Period: {recurring.start_date} to {recurring.end_date}')
print(f'   Day of week: {recurring.day_of_week} (0=Monday)')
