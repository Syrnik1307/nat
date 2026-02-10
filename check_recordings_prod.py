import sys
sys.path.insert(0, "/var/www/teaching_panel/teaching_panel")
import django, os
os.environ["DJANGO_SETTINGS_MODULE"] = "teaching_panel.settings"
django.setup()
from schedule.models import LessonRecording as R

# Check specific recording
try:
    r = R.objects.get(id=18)
    print(f"=== Recording ID=18 ===")
    print(f"title: {r.title}")
    print(f"storage_provider: {r.storage_provider}")
    print(f"gdrive_file_id: '{r.gdrive_file_id}'")
    print(f"play_url: '{r.play_url}'")
    print(f"download_url: '{r.download_url}'")
    print(f"local_file: {r.local_file.name if r.local_file else None}")
    print(f"file_size: {r.file_size}")
except R.DoesNotExist:
    print("Recording 18 not found")

# Check all recent
print("\n=== Last 5 recordings ===")
recs = R.objects.filter(is_deleted=False).order_by("-created_at")[:5]
for r in recs:
    print(f"ID={r.id} storage={r.storage_provider} gdrive='{r.gdrive_file_id}' play_url='{r.play_url[:60] if r.play_url else ''}'")

# Check file exists
import os
print("\n=== File check ===")
media_path = "/var/www/teaching_panel/teaching_panel/media/lesson_recordings/20260206_140955__19fb93_video1205579705.mp4"
print(f"File exists: {os.path.exists(media_path)}")
if os.path.exists(media_path):
    print(f"File size: {os.path.getsize(media_path)}")
