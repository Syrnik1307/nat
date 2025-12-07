#!/usr/bin/env python
import os, sys, django, requests
from datetime import datetime

sys.path.insert(0, '/var/www/teaching_panel/teaching_panel')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from schedule.zoom_client import my_zoom_api_client
from schedule.models import LessonRecording

MEETING_ID = '83743093059'

access_token = my_zoom_api_client._get_access_token()
url = f'https://api.zoom.us/v2/meetings/{MEETING_ID}/recordings'
resp = requests.get(url, headers={'Authorization': f'Bearer {access_token}'}, timeout=20)
resp.raise_for_status()
data = resp.json()

print('From Zoom API:')
for f in data.get('recording_files', []):
    rec_id = f.get('id')
    print(f'  {rec_id}')

print('\nFrom DB:')
for lr in LessonRecording.objects.filter(lesson_id=17):
    print(f'  {lr.zoom_recording_id}')
