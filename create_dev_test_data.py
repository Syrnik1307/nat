import os
import sys
import django
from datetime import date, time

sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from accounts.models import CustomUser
from schedule.models import Group, RecurringLesson

# Получаем или создаем учителя
teacher, created = CustomUser.objects.get_or_create(
    email='dev_teacher@test.com',
    defaults={
        'first_name': 'Dev',
        'last_name': 'Teacher',
        'role': 'teacher',
        'is_active': True,
    }
)
teacher.set_password('dev123')
teacher.save()
print(f'✅ Teacher: {teacher.email}')

# Получаем или создаем группу
group, created = Group.objects.get_or_create(
    name='Dev Test Group',
    teacher=teacher,
    defaults={'description': 'Group for dev testing'}
)
print(f'✅ Group: {group.name}')

# Даты для регулярных уроков
start_date = date(2025, 12, 1)
end_date = date(2025, 12, 31)

# Создаем регулярные уроки
recurring, created = RecurringLesson.objects.get_or_create(
    title='Dev Recurring Lesson - Monday',
    group=group,
    teacher=teacher,
    day_of_week=0,
    defaults={
        'start_time': time(15, 0),
        'end_time': time(16, 30),
        'start_date': start_date,
        'end_date': end_date,
    }
)
status = '✅ CREATED' if created else '⚠️ EXISTS'
print(f'{status}: Dev Recurring Lesson - Monday')

recurring, created = RecurringLesson.objects.get_or_create(
    title='Dev Recurring Lesson - Wednesday',
    group=group,
    teacher=teacher,
    day_of_week=2,
    defaults={
        'start_time': time(17, 0),
        'end_time': time(18, 30),
        'start_date': start_date,
        'end_date': end_date,
    }
)
status = '✅ CREATED' if created else '⚠️ EXISTS'
print(f'{status}: Dev Recurring Lesson - Wednesday')

recurring, created = RecurringLesson.objects.get_or_create(
    title='Dev Recurring Lesson - Friday',
    group=group,
    teacher=teacher,
    day_of_week=4,
    defaults={
        'start_time': time(14, 0),
        'end_time': time(15, 30),
        'start_date': start_date,
        'end_date': end_date,
    }
)
status = '✅ CREATED' if created else '⚠️ EXISTS'
print(f'{status}: Dev Recurring Lesson - Friday')

print('\n✅ Test data created successfully!')
print(f'Login with: dev_teacher@test.com / dev123')
