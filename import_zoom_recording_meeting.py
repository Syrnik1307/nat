#!/usr/bin/env python
import os, sys, django, requests
from datetime import datetime

sys.path.insert(0, '/var/www/teaching_panel/teaching_panel')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from schedule.zoom_client import my_zoom_api_client
from schedule.models import Lesson, LessonRecording
from django.utils import timezone

MEETING_ID = '83743093059'
LESSON_ID = 17

access_token = my_zoom_api_client._get_access_token()
url = f'https://api.zoom.us/v2/meetings/{MEETING_ID}/recordings'
resp = requests.get(url, headers={'Authorization': f'Bearer {access_token}'}, timeout=20)
resp.raise_for_status()
data = resp.json()

lesson = Lesson.objects.get(id=LESSON_ID)
print(f'Lesson {lesson.id}: {lesson.title}')

created = 0
for f in data.get('recording_files', []):
    rec_id = f.get('id')
    if LessonRecording.objects.filter(lesson=lesson, zoom_recording_id=rec_id).exists():
        print(f'Skip existing {rec_id}')
        continue
    start = f.get('recording_start')
    end = f.get('recording_end')
    def parse(dt):
        if not dt:
            return None
        return datetime.fromisoformat(dt.replace('Z', '+00:00'))
    lr = LessonRecording.objects.create(
        lesson=lesson,
        zoom_recording_id=rec_id,
        download_url=f.get('download_url',''),
        play_url=f.get('play_url',''),
        recording_type=f.get('recording_type',''),
        file_size=f.get('file_size') or None,
        recording_start=parse(start),
        recording_end=parse(end),
        status='ready'
    )
    created +=1
    print(f'Created recording {lr.id} {rec_id} {lr.recording_type}')

print(f'Done. Created {created}')
