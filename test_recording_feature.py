#!/usr/bin/env python3
"""
Тест функционала автоматической записи уроков
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from schedule.models import Lesson, LessonRecording
from accounts.models import CustomUser
from django.utils import timezone

print("=" * 60)
print("🧪 ТЕСТИРОВАНИЕ ФУНКЦИОНАЛА ЗАПИСИ УРОКОВ")
print("=" * 60)

# 1. Проверка наличия преподавателей
print("\n1️⃣ Проверка преподавателей:")
teachers = CustomUser.objects.filter(role='teacher')
print(f"   Найдено преподавателей: {teachers.count()}")
if teachers.exists():
    teacher = teachers.first()
    print(f"   Тестовый преподаватель: {teacher.email}")
else:
    print("   ⚠️ Преподавателей не найдено!")
    sys.exit(1)

# 2. Проверка уроков с флагом записи
print("\n2️⃣ Проверка уроков:")
all_lessons = Lesson.objects.filter(teacher=teacher)
recorded_lessons = all_lessons.filter(record_lesson=True)
print(f"   Всего уроков: {all_lessons.count()}")
print(f"   Уроков с записью: {recorded_lessons.count()}")

if all_lessons.exists():
    lesson = all_lessons.first()
    print(f"\n   📚 Тестовый урок:")
    print(f"      ID: {lesson.id}")
    print(f"      Название: {lesson.title}")
    print(f"      Запись включена: {lesson.record_lesson}")
    print(f"      Дней хранения: {lesson.recording_available_for_days}")
else:
    print("   ⚠️ Уроков не найдено!")

# 3. Проверка существующих записей
print("\n3️⃣ Проверка записей:")
all_recordings = LessonRecording.objects.all()
zoom_recordings = all_recordings.filter(storage_provider='zoom')
print(f"   Всего записей: {all_recordings.count()}")
print(f"   Zoom записей: {zoom_recordings.count()}")

if zoom_recordings.exists():
    print("\n   📹 Последние Zoom записи:")
    for rec in zoom_recordings[:3]:
        print(f"      - {rec.title} (Урок #{rec.lesson.id})")
        print(f"        Создана: {rec.created_at.strftime('%Y-%m-%d %H:%M')}")
        print(f"        Статус: {rec.status}")

# 4. Проверка сериализатора
print("\n4️⃣ Проверка API (Serializer):")
from schedule.serializers import LessonSerializer
if all_lessons.exists():
    lesson = all_lessons.first()
    serializer = LessonSerializer(lesson)
    data = serializer.data
    
    has_record_lesson = 'record_lesson' in data
    has_recording_days = 'recording_available_for_days' in data
    
    print(f"   ✅ Поле 'record_lesson' в API: {has_record_lesson}")
    print(f"   ✅ Поле 'recording_available_for_days' в API: {has_recording_days}")
    
    if has_record_lesson:
        print(f"   Значение: record_lesson={data['record_lesson']}")
    if has_recording_days:
        print(f"   Значение: recording_available_for_days={data['recording_available_for_days']}")

# 5. Проверка webhook endpoint
print("\n5️⃣ Проверка Zoom webhook URL:")
print("   URL: http://72.56.81.163/schedule/api/zoom/webhook/")
print("   ⚠️ Требует настройки в Zoom Marketplace!")

# Итог
print("\n" + "=" * 60)
print("✅ БАЗОВАЯ ПРОВЕРКА ЗАВЕРШЕНА")
print("=" * 60)
print("\n📋 Следующие шаги:")
print("   1. Войти на http://72.56.81.163 как преподаватель")
print("   2. Нажать 'Начать занятие' на любом уроке")
print("   3. Проверить появление диалога с чекбоксом записи")
print("   4. Настроить Zoom webhook для автоматического добавления")
print()
