from schedule.models import LessonRecording, Lesson
from django.utils import timezone

now = timezone.now()
cutoff = now - timezone.timedelta(hours=3)

print("=== RECORDINGS last 3h ===")
recs = LessonRecording.objects.filter(created_at__gte=cutoff).order_by('-created_at')
print(f"Found: {recs.count()}")
for r in recs:
    print(f"ID={r.id} lesson={r.lesson_id} status={r.status} storage={r.storage_provider} type={r.recording_type} created={r.created_at}")

print("\n=== LESSONS with record_lesson=True last 3h ===")
lessons = Lesson.objects.filter(start_time__gte=cutoff, record_lesson=True).order_by('-start_time')
print(f"Found: {lessons.count()}")
for l in lessons:
    print(f"ID={l.id} title='{l.title}' group={l.group.name if l.group else 'N/A'} zoom_id={l.zoom_meeting_id} start={l.start_time} end={l.end_time}")
    
print("\n=== ALL LESSONS last 3h ===")
all_lessons = Lesson.objects.filter(start_time__gte=cutoff).order_by('-start_time')
print(f"Found: {all_lessons.count()}")
for l in all_lessons:
    print(f"ID={l.id} title='{l.title}' record={l.record_lesson} zoom_id={l.zoom_meeting_id}")
