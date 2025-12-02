#!/usr/bin/env python
"""Проверка записей в базе данных"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, '/var/www/teaching_panel/teaching_panel')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from accounts.models import CustomUser
from schedule.models import LessonRecording, Lesson

# Найти преподавателя
teacher = CustomUser.objects.get(email='syrnik131313@gmail.com')
print(f"Teacher: {teacher.email}, Role: {teacher.role}")
print(f"Teacher ID: {teacher.id}")

# Проверить уроки
lessons = Lesson.objects.filter(teacher=teacher)
print(f"\nLessons by this teacher: {lessons.count()}")

# Проверить записи
recordings = LessonRecording.objects.filter(lesson__teacher=teacher)
print(f"\n=== Recordings ===")
print(f"Total recordings: {recordings.count()}")
print(f"Ready: {recordings.filter(status='ready').count()}")
print(f"Processing: {recordings.filter(status='processing').count()}")
print(f"Failed: {recordings.filter(status='failed').count()}")

if recordings.exists():
    print("\nList of recordings:")
    for r in recordings[:5]:
        print(f"- ID {r.id}: {r.lesson.title}")
        print(f"  Status: {r.status}")
        print(f"  GDrive ID: {r.gdrive_file_id[:30] if r.gdrive_file_id else 'None'}...")
        print(f"  File size: {r.file_size / (1024**2):.2f} MB" if r.file_size else "  File size: Unknown")
        print(f"  Created: {r.created_at}")
else:
    print("\n⚠ NO RECORDINGS FOUND!")
    print("\nNeed to create test recording. Checking if lessons have record_lesson=True...")
    
    lessons_with_recording = lessons.filter(record_lesson=True)
    print(f"Lessons with record_lesson=True: {lessons_with_recording.count()}")
