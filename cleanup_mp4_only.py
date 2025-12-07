#!/usr/bin/env python
import os, sys, django
sys.path.insert(0, '/var/www/teaching_panel/teaching_panel')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from schedule.models import LessonRecording

# Удалим все non-MP4 записи (M4A, JSON timeline)
deleted = 0
for lr in LessonRecording.objects.filter(lesson_id=17):
    if lr.recording_type not in ['shared_screen_with_speaker_view', 'mp4']:
        print(f'Deleting {lr.id}: {lr.recording_type}')
        lr.delete()
        deleted += 1

print(f'Deleted {deleted} non-MP4 recordings')

# Обновим MP4 с правильной длительностью (32 секунды)
DURATION_SECONDS = 32
updated = 0

for lr in LessonRecording.objects.filter(lesson_id=17):
    if lr.duration != DURATION_SECONDS:
        lr.duration = DURATION_SECONDS
        lr.save(update_fields=['duration'])
        updated += 1
        print(f'Updated {lr.id}: duration={DURATION_SECONDS}s')

print(f'Updated {updated} MP4 recordings with correct duration')
