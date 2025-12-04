#!/usr/bin/env python3
"""
Тест удаления записи урока
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from schedule.models import LessonRecording, Lesson
from accounts.models import CustomUser
from django.utils import timezone
from datetime import timedelta

print("=" * 60)
print("🧪 ТЕСТ УДАЛЕНИЯ ЗАПИСЕЙ")
print("=" * 60)

# Найти преподавателя
teacher = CustomUser.objects.filter(role='teacher').first()
if not teacher:
    print("❌ Преподаватель не найден")
    sys.exit(1)

print(f"\n✅ Преподаватель: {teacher.email}")

# Найти урок
lesson = Lesson.objects.filter(teacher=teacher).first()
if not lesson:
    print("❌ Урок не найден")
    sys.exit(1)

print(f"✅ Урок: {lesson.title} (ID={lesson.id})")

# Создать тестовую запись
recording = LessonRecording.objects.create(
    lesson=lesson,
    storage_provider='zoom',
    status='ready',
    visibility=LessonRecording.Visibility.LESSON_GROUP,
    recording_start=timezone.now(),
    recording_end=timezone.now() + timedelta(hours=1),
    file_size=1024 * 1024,  # 1 MB
    download_url='https://test.zoom.us/rec/download/test',
    play_url='https://test.zoom.us/rec/play/test'
)
recording.allowed_groups.add(lesson.group)

print(f"\n✅ Тестовая запись создана:")
print(f"   ID: {recording.id}")
print(f"   Урок: {recording.lesson.title}")
print(f"   Статус: {recording.status}")

print("\n📋 Для тестирования удаления:")
print(f"   1. Войти как {teacher.email}")
print(f"   2. Перейти в раздел 'Записи'")
print(f"   3. Найти запись ID={recording.id}")
print(f"   4. Нажать кнопку 'Удалить'")
print(f"   5. Подтвердить удаление")
print("\n✅ Ожидается: запись исчезнет из списка без ошибок")
print("=" * 60)
