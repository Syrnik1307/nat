#!/usr/bin/env python
"""Check recordings for lesson 17 in DB and Zoom API"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, '/var/www/teaching_panel/teaching_panel')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from schedule.zoom_client import my_zoom_api_client
from schedule.models import Lesson, LessonRecording
import json

try:
    # Find lesson 17
    lesson = Lesson.objects.get(id=17)
    print(f'=== Lesson {lesson.id}: {lesson.title} ===')
    print(f'Zoom Meeting ID: {lesson.zoom_meeting_id}')
    print(f'Teacher: {lesson.teacher.email}')
    print(f'Teacher Zoom User ID: {getattr(lesson.teacher, "zoom_user_id", "NOT SET")}')
    print()
except Exception as e:
    print(f'Error loading lesson: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Check recordings in DB
recordings_in_db = LessonRecording.objects.filter(lesson=lesson)
print(f'=== Recordings in Django DB: {recordings_in_db.count()} ===')
for rec in recordings_in_db:
    print(f'  [{rec.id}] {rec.file_type} - {rec.status}')
    print(f'      Zoom ID: {rec.zoom_recording_id}')
    print(f'      Play URL: {rec.play_url}')
    print(f'      Download URL: {rec.download_url}')
print()

# Check what's in Zoom API
zoom_user_id = getattr(lesson.teacher, 'zoom_user_id', None)
if not zoom_user_id:
    print('=== Zoom User ID not set for teacher ===')
    print('Cannot call Zoom API without zoom_user_id')
    print('This is why recordings are not syncing!')
else:
    print('=== Checking Zoom API ===')
    try:
        zoom_recordings = my_zoom_api_client.list_user_recordings(zoom_user_id)
        print(f'Total recordings from Zoom API: {len(zoom_recordings)}')
        print()
        
        found_our_meeting = False
        for rec in zoom_recordings:
            meeting_id = str(rec.get('id', ''))
            topic = rec.get('topic', 'No topic')
            start_time = rec.get('start_time', 'Unknown')
            
            if meeting_id == str(lesson.zoom_meeting_id):
                found_our_meeting = True
                print(f'✓ FOUND OUR MEETING: {meeting_id}')
                print(json.dumps(rec, indent=2))
            else:
                print(f'  Other meeting: {meeting_id} - {topic} ({start_time})')
        
        if not found_our_meeting:
            print(f'\n✗ Meeting {lesson.zoom_meeting_id} NOT FOUND in Zoom API')
            print('  This means:')
            print('  1. Recording may still be processing in Zoom')
            print('  2. Recording may have failed')
            print('  3. Meeting may not have been recorded')
            
    except Exception as e:
        print(f'ERROR calling Zoom API: {e}')
        import traceback
        traceback.print_exc()
