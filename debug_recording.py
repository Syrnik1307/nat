#!/usr/bin/env python
"""Debug recording API response"""
import os, sys
os.environ["DJANGO_SETTINGS_MODULE"] = "teaching_panel.settings"
sys.path.insert(0, "/var/www/teaching_panel/teaching_panel")
import django
django.setup()

from schedule.models import LessonRecording

print("=== All recordings (newest first) ===")
recs = LessonRecording.objects.filter(is_deleted=False).order_by("-created_at")[:15]
for r in recs:
    gdrive_ok = bool(r.gdrive_file_id)
    file_exists = False
    if r.storage_provider == 'local' and r.play_url:
        # Check if file exists
        local_path = r.play_url.replace('/media/', '/var/www/teaching_panel/teaching_panel/media/')
        file_exists = os.path.exists(local_path)
    print(f"ID={r.id:3} | {r.created_at.strftime('%Y-%m-%d %H:%M')} | storage={r.storage_provider:6} | gdrive={gdrive_ok} | file_exists={file_exists} | play_url={r.play_url[:60] if r.play_url else 'EMPTY'}")

# Check specific new recordings
print("\n=== New recordings details ===")
new_recs = LessonRecording.objects.filter(storage_provider='local', is_deleted=False).order_by("-created_at")[:5]
for r in new_recs:
    local_path = r.play_url.replace('/media/', '/var/www/teaching_panel/teaching_panel/media/') if r.play_url else None
    print(f"ID={r.id}")
    print(f"  play_url: {r.play_url}")
    print(f"  local_path: {local_path}")
    print(f"  exists: {os.path.exists(local_path) if local_path else False}")
    if local_path and os.path.exists(local_path):
        print(f"  size: {os.path.getsize(local_path)}")
    print()
