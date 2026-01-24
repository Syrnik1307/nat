#!/usr/bin/env python3
"""Check recording 14 details"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from schedule.models import LessonRecording

r = LessonRecording.objects.get(id=14)
print(f"Recording ID: {r.id}")
print(f"play_url: {r.play_url}")
print(f"gdrive_file_id: {r.gdrive_file_id}")
print(f"download_url: {r.download_url}")
print(f"archive_url: {r.archive_url}")
print(f"storage_provider: {r.storage_provider}")
print(f"status: {r.status}")
