from schedule.models import LessonRecording, Lesson
from schedule.zoom_client import ZoomAPIClient
from datetime import timedelta

# Запись 12
r = LessonRecording.objects.get(id=12)
lesson = r.lesson
teacher = lesson.teacher

print(f"Checking recording {r.id} for lesson {lesson.id}")
print(f"Meeting ID: {lesson.zoom_meeting_id}")

# Создаём Zoom клиент
zoom_client = ZoomAPIClient(
    account_id=teacher.zoom_account_id,
    client_id=teacher.zoom_client_id,
    client_secret=teacher.zoom_client_secret
)

# Ищем записи для этого митинга
from_date = (lesson.start_time - timedelta(days=3)).date().isoformat()
to_date = (lesson.start_time + timedelta(days=3)).date().isoformat()

print(f"Searching from {from_date} to {to_date}")

try:
    recordings_response = zoom_client.list_user_recordings(
        user_id=teacher.zoom_user_id or 'me',
        from_date=from_date,
        to_date=to_date,
    )
    
    meetings = recordings_response.get('meetings', [])
    print(f"Found {len(meetings)} meetings in Zoom")
    
    for m in meetings:
        mid = m.get('id')
        topic = m.get('topic')
        files = m.get('recording_files', [])
        print(f"  Meeting {mid}: {topic} - {len(files)} files")
        if str(mid) == str(lesson.zoom_meeting_id):
            print("    ^ THIS IS OUR MEETING!")
            for f in files:
                print(f"      File: {f.get('file_type')} - {f.get('file_size')} bytes")
                print(f"        Status: {f.get('status')}")
                print(f"        Download: {f.get('download_url', '')[:80]}...")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

# Попробуем получить записи напрямую для митинга
print("\n--- Trying direct meeting recordings ---")
try:
    # Zoom API: GET /meetings/{meetingId}/recordings
    import requests
    token = zoom_client._get_access_token()
    resp = requests.get(
        f"https://api.zoom.us/v2/meetings/{lesson.zoom_meeting_id}/recordings",
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Found: {len(data.get('recording_files', []))} files")
        for f in data.get('recording_files', []):
            print(f"  {f.get('file_type')}: {f.get('status')}")
    else:
        print(f"Error: {resp.text}")
except Exception as e:
    print(f"Direct API error: {e}")

# Проверим корзину
print("\n--- Checking trash ---")
try:
    resp = requests.get(
        f"https://api.zoom.us/v2/meetings/{lesson.zoom_meeting_id}/recordings?trash=true",
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"Trash status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"In trash: {len(data.get('recording_files', []))} files")
    else:
        print(f"Trash response: {resp.text[:200]}")
except Exception as e:
    print(f"Trash error: {e}")
