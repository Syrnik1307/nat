#!/usr/bin/env python
"""
Проверка конфигурации Zoom webhook
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'teaching_panel'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from django.conf import settings
from schedule.models import Lesson, LessonRecording

# Check Zoom settings
print("=== ZOOM WEBHOOK CONFIG CHECK ===")
print(f"ZOOM_WEBHOOK_SECRET_TOKEN set: {bool(getattr(settings, 'ZOOM_WEBHOOK_SECRET_TOKEN', ''))}")
print(f"ZOOM_ACCOUNT_ID set: {bool(getattr(settings, 'ZOOM_ACCOUNT_ID', ''))}")
print(f"ZOOM_CLIENT_ID set: {bool(getattr(settings, 'ZOOM_CLIENT_ID', ''))}")
print(f"ZOOM_CLIENT_SECRET set: {bool(getattr(settings, 'ZOOM_CLIENT_SECRET', ''))}")

# Check lesson 64
print("\n=== LESSON 64 STATUS ===")
try:
    lesson = Lesson.objects.get(id=64)
    print(f"Title: {lesson.title}")
    print(f"Group: {lesson.group}")
    print(f"zoom_meeting_id: {lesson.zoom_meeting_id}")
    print(f"record_lesson: {lesson.record_lesson}")
    print(f"status: {lesson.status}")
    print(f"start_time: {lesson.start_time}")
    print(f"end_time: {lesson.end_time}")
    print(f"ended_at: {lesson.ended_at}")
    print(f"recordings count: {lesson.recordings.count()}")
except Lesson.DoesNotExist:
    print("Lesson 64 not found")

# Check all recordings
print("\n=== RECENT RECORDINGS ===")
recs = LessonRecording.objects.order_by('-created_at')[:10]
if recs:
    for r in recs:
        print(f"ID={r.id}, lesson={r.lesson_id}, created={r.created_at}, title={r.title[:30] if r.title else 'N/A'}")
else:
    print("No recordings in database")

print("\n=== WEBHOOK ENDPOINTS ===")
print("Expected URL: https://72.56.81.163/schedule/api/zoom/webhook/")
print("Alternative: https://72.56.81.163/api/schedule/webhook/zoom/")
