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

def parse_dt(val):
    if not val:
        return None
    return datetime.fromisoformat(val.replace('Z', '+00:00'))

updated = 0
for f in data.get('recording_files', []):
    rec_id = f.get('id')
    try:
        lr = LessonRecording.objects.get(zoom_recording_id=rec_id)
    except LessonRecording.DoesNotExist:
        print(f'Recording {rec_id} not found')
        continue
    
    rec_start = parse_dt(f.get('recording_start'))
    rec_end = parse_dt(f.get('recording_end'))
    rec_duration = None
    if rec_start and rec_end:
        rec_duration = int((rec_end - rec_start).total_seconds())
    
    if rec_duration and (not lr.duration or lr.duration == 0):
        lr.duration = rec_duration
        lr.recording_start = rec_start
        lr.recording_end = rec_end
        lr.save(update_fields=['duration', 'recording_start', 'recording_end'])
        updated += 1
        print(f'Updated {lr.id}: duration={rec_duration}s ({int(rec_duration/60)}m)')

print(f'Done. Updated {updated} recordings')
