#!/usr/bin/env python
"""Тест API записей"""
import os
import sys
import django

sys.path.insert(0, '/var/www/teaching_panel/teaching_panel')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from accounts.models import CustomUser
from schedule.models import LessonRecording
from schedule.serializers import LessonRecordingSerializer

teacher = CustomUser.objects.get(email='syrnik131313@gmail.com')
print(f"Teacher: {teacher.email}, Role: {teacher.role}")

recordings = LessonRecording.objects.filter(
    lesson__teacher=teacher
).select_related('lesson', 'lesson__group')

print(f"\nRecordings found: {recordings.count()}")

for recording in recordings:
    print(f"\n=== Recording ID {recording.id} ===")
    print(f"Lesson: {recording.lesson.title}")
    print(f"Group: {recording.lesson.group.name if recording.lesson.group else 'No group'}")
    print(f"Status: {recording.status}")
    print(f"GDrive file ID: {recording.gdrive_file_id}")
    print(f"Archive URL: {recording.archive_url}")
    print(f"Play URL: {recording.play_url}")
    print(f"File size: {recording.file_size}")
    
    # Сериализовать для API
    print("\n--- Serialized data ---")
    serializer = LessonRecordingSerializer(recording)
    import json
    print(json.dumps(serializer.data, indent=2, default=str))
