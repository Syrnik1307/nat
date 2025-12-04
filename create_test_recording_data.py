#!/usr/bin/env python3
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from accounts.models import CustomUser
from schedule.models import Lesson, Group
from django.utils import timezone

# Проверяем существующего преподавателя
teacher = CustomUser.objects.filter(role='teacher').first()

if not teacher:
    print("Создаём тестового преподавателя...")
    teacher = CustomUser.objects.create_user(
        email='test_teacher_recording@example.com',
        password='test123456',
        role='teacher',
        first_name='Test',
        last_name='Recording Teacher'
    )
    print(f"✅ Создан: {teacher.email}")
else:
    print(f"✅ Найден преподаватель: {teacher.email}")

# Проверяем группу
group = Group.objects.filter(teacher=teacher).first()
if not group:
    print("Создаём тестовую группу...")
    group = Group.objects.create(
        name='Test Recording Group',
        teacher=teacher
    )
    print(f"✅ Создана группа: {group.name}")
else:
    print(f"✅ Найдена группа: {group.name}")

# Создаём урок с записью
from datetime import timedelta
print("Создаём урок с включённой записью...")
start = timezone.now()
lesson = Lesson.objects.create(
    teacher=teacher,
    group=group,
    title='Test Lesson with Recording',
    start_time=start,
    end_time=start + timedelta(hours=1),
    record_lesson=True,
    recording_available_for_days=90
)
print(f"✅ Создан урок ID={lesson.id}: {lesson.title}")
print(f"   record_lesson={lesson.record_lesson}")
print(f"   recording_available_for_days={lesson.recording_available_for_days}")

print("\n" + "="*60)
print("✅ Тестовые данные созданы!")
print(f"   Преподаватель: {teacher.email} / test123456")
print(f"   Урок ID: {lesson.id}")
print("="*60)
