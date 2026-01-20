from schedule.views import resync_recording
from schedule.models import LessonRecording, Lesson
from schedule.zoom_client import ZoomAPIClient
from schedule.tasks import process_zoom_recording_bundle
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta
from django.utils import timezone

User = get_user_model()

recording = LessonRecording.objects.get(id=13)
lesson = recording.lesson
teacher = lesson.teacher

print(f"Recording: {recording.id} - {recording.title}")
print(f"Lesson: {lesson.id} - zoom_meeting_id: {lesson.zoom_meeting_id}")
print(f"Teacher: {teacher.email}")

# Создаём Zoom клиент
zoom_client = ZoomAPIClient(
    account_id=teacher.zoom_account_id,
    client_id=teacher.zoom_client_id,
    client_secret=teacher.zoom_client_secret
)

# Получаем записи
from_date = (lesson.start_time - timedelta(days=1)).date().isoformat()
to_date = (lesson.start_time + timedelta(days=1)).date().isoformat()

print(f"\nFetching recordings from {from_date} to {to_date}...")

try:
    recordings_response = zoom_client.list_user_recordings(
        user_id=teacher.zoom_user_id or 'me',
        from_date=from_date,
        to_date=to_date,
    )
    
    meetings = recordings_response.get('meetings', [])
    print(f"Found {len(meetings)} meetings")
    
    meeting_data = None
    for m in meetings:
        print(f"  Meeting ID: {m.get('id')} - Topic: {m.get('topic')}")
        if str(m.get('id')) == str(lesson.zoom_meeting_id):
            meeting_data = m
            print(f"    ^ MATCHED!")
            break
    
    if meeting_data:
        recording_files = meeting_data.get('recording_files', [])
        print(f"\nRecording files: {len(recording_files)}")
        
        mp4_files = []
        for rf in recording_files:
            ft = str(rf.get('file_type', '')).lower()
            print(f"  Type: {ft}, Size: {rf.get('file_size')}, Start: {rf.get('recording_start')}")
            if ft == 'mp4' and rf.get('download_url'):
                mp4_files.append(rf)
        
        print(f"\nMP4 files to merge: {len(mp4_files)}")
        
        if len(mp4_files) > 0:
            # Собираем части
            passcode = meeting_data.get('recording_play_passcode') or meeting_data.get('password')
            
            def apply_passcode(url, pwd):
                if not url or not pwd:
                    return url
                if 'pwd=' in url:
                    return url
                separator = '&' if '?' in url else '?'
                return f"{url}{separator}pwd={pwd}"
            
            mp4_files.sort(key=lambda f: f.get('recording_start') or '')
            
            parts = []
            total_size = 0
            for idx, f in enumerate(mp4_files):
                parts.append({
                    'id': f.get('id') or f"part_{idx}",
                    'download_url': apply_passcode(f.get('download_url', ''), passcode),
                    'recording_start': f.get('recording_start')
                })
                total_size += int(f.get('file_size', 0) or 0)
                print(f"  Part {idx+1}: {f.get('file_size')} bytes")
            
            print(f"\nTotal size: {total_size / (1024*1024):.1f} MB")
            print(f"Parts: {len(parts)}")
            
            # Обновляем запись и запускаем склейку
            recording.zoom_recording_id = f"bundle_{lesson.zoom_meeting_id}"
            recording.file_size = total_size
            recording.status = 'processing'
            recording.storage_provider = 'gdrive'
            recording.save()
            
            print(f"\nStarting bundle merge task...")
            process_zoom_recording_bundle.delay(recording.id, parts)
            print("Task queued!")
    else:
        print("Meeting not found!")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
