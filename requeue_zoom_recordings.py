from schedule.models import LessonRecording
from schedule.tasks import process_zoom_recording
from django.utils import timezone

now = timezone.now()
cutoff = now - timezone.timedelta(hours=24)
qs = LessonRecording.objects.filter(created_at__gte=cutoff, storage_provider='zoom')
print(f"Found {qs.count()} zoom recordings since {cutoff}")
for rec in qs:
    print(f"Queue recording id={rec.id}, lesson={rec.lesson_id}, status={rec.status}, type={rec.recording_type}")
    rec.status = 'processing'
    rec.storage_provider = 'gdrive'
    rec.save(update_fields=['status','storage_provider'])
    process_zoom_recording.delay(rec.id)
print('DONE')
