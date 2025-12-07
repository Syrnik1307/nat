#!/usr/bin/env python
import os, sys, django
sys.path.insert(0, '/var/www/teaching_panel/teaching_panel')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from schedule.models import LessonRecording

print("=== Lesson 17 Recordings ===")
for lr in LessonRecording.objects.filter(lesson_id=17):
    print(f'ID: {lr.id}')
    print(f'  Duration (seconds): {lr.duration}')
    print(f'  Recording start: {lr.recording_start}')
    print(f'  Recording end: {lr.recording_end}')
    print(f'  Type: {lr.recording_type}')
    if lr.duration:
        print(f'  Duration (minutes): {int(round(lr.duration / 60.0))} min')
    print()
