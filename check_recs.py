#!/usr/bin/env python
"""Проверка и исправление записей"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from schedule.models import LessonRecording

print("=== Записи ===\n")
for r in LessonRecording.objects.filter(status='ready'):
    print(f"ID={r.id}")
    print(f"  gdrive_file_id: {r.gdrive_file_id}")
    print(f"  play_url: {r.play_url[:80]}..." if r.play_url else "  play_url: None")
    print(f"  download_url: {r.download_url[:80]}..." if r.download_url else "  download_url: None")
    print(f"  available_until: {r.available_until}")
    print()
