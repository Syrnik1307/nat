import django
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "teaching_panel.settings")
django.setup()

from schedule.models import Lesson, LessonRecording
from accounts.models import CustomUser
from django.utils import timezone
from datetime import timedelta
from schedule.views import sync_missing_zoom_recordings_for_teacher

# Get lessons 64 and 65
for lid in [64, 65]:
    try:
        lesson = Lesson.objects.get(id=lid)
        print(f"Lesson {lid}:")
        print(f"  teacher_id: {lesson.teacher_id}")
        print(f"  teacher_email: {lesson.teacher.email}")
        print(f"  record_lesson: {lesson.record_lesson}")
        print(f"  zoom_meeting_id: {lesson.zoom_meeting_id}")
        print(f"  group: {lesson.group.name if lesson.group else 'N/A'}")
        print(f"  start_time: {lesson.start_time}")
        print(f"  end_time: {lesson.end_time}")
        
        # Check teacher's zoom credentials
        t = lesson.teacher
        has_creds = bool(t.zoom_account_id and t.zoom_client_id and t.zoom_client_secret)
        print(f"  teacher has_zoom_creds: {has_creds}")
        print()
    except Lesson.DoesNotExist:
        print(f"Lesson {lid} not found")
        print()

# Now try to sync for the teacher with credentials (ID=4)
print("=" * 50)
print("Attempting sync for teacher ID=4...")
try:
    teacher = CustomUser.objects.get(id=4)
    result = sync_missing_zoom_recordings_for_teacher(teacher)
    print(f"Synced {result} recordings")
except Exception as e:
    print(f"Error: {e}")

# Check recordings again
print()
print("=" * 50)
print("Recordings after sync:")
recs = LessonRecording.objects.order_by('-created_at')[:10]
for r in recs:
    print(f"  ID={r.id} lesson={r.lesson_id} status={r.status} storage={r.storage_provider}")
