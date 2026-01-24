#!/usr/bin/env python
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
import django
django.setup()

from schedule.models import LessonRecording

r = LessonRecording.objects.filter(status='ready').last()
if r:
    print(f'ID: {r.id}')
    print(f'gdrive_file_id: {r.gdrive_file_id}')
    print(f'play_url: {r.play_url}')
    print(f'storage_provider: {r.storage_provider}')
else:
    print('No ready recordings found')
