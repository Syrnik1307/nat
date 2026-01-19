#!/usr/bin/env python
"""Проверка записей в БД"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from schedule.models import LessonRecording

recs = LessonRecording.objects.all().select_related('lesson')
print(f"Всего записей в БД: {recs.count()}")
print("-" * 80)

for r in recs:
    gdrive = "GDrive" if r.gdrive_file_id else "no-gdrive"
    zoom = r.zoom_recording_id[:15] if r.zoom_recording_id else "no-zoom-rec"
    size = (r.file_size or 0) / (1024**2)
    meeting = r.lesson.zoom_meeting_id if r.lesson else "no-lesson"
    print(f"ID={r.id} | {r.status:12} | {gdrive:10} | zoom_rec={zoom:15} | {size:7.1f}MB | meeting={meeting}")
