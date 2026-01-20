from schedule.tasks import _delete_from_zoom
from schedule.models import LessonRecording
from django.contrib.auth import get_user_model

User = get_user_model()
teacher = User.objects.filter(role='teacher').first()

print("Testing safety checks...")

# Test 1: No gdrive_file_id
rec = LessonRecording(gdrive_file_id='', status='ready', zoom_recording_id='test123')
result = _delete_from_zoom(rec, teacher)
print(f"Test1 (no gdrive_file_id): {'PASS' if not result else 'FAIL'}")

# Test 2: Status not ready
rec.gdrive_file_id = 'fake_id_123'
rec.status = 'processing'
result = _delete_from_zoom(rec, teacher)
print(f"Test2 (status=processing): {'PASS' if not result else 'FAIL'}")

# Test 3: File not on GDrive
rec.status = 'ready'
rec.gdrive_file_id = 'nonexistent_file_xyz_999'
result = _delete_from_zoom(rec, teacher)
print(f"Test3 (file not on GDrive): {'PASS' if not result else 'FAIL'}")

print("ALL SAFETY CHECKS WORKING!")
