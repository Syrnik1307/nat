from schedule.models import Lesson, LessonRecording
from django.utils import timezone

now = timezone.now()

# Последние уроки с record_lesson=True
print("=== RECENT LESSONS WITH RECORDING ENABLED ===")
lessons = Lesson.objects.filter(record_lesson=True).order_by('-start_time')[:10]
for l in lessons:
    recs = l.recordings.all()
    print(f"ID={l.id} group={l.group.name if l.group else 'NO'} start={l.start_time} zoom_id={l.zoom_meeting_id} recs={recs.count()}")
    for r in recs:
        print(f"    Rec ID={r.id} status={r.status} url={r.video_url[:50] if r.video_url else 'None'}...")

print("\n=== LESSON 64 (quick lesson) ===")
try:
    l64 = Lesson.objects.get(id=64)
    print(f"record_lesson={l64.record_lesson}")
    print(f"zoom_meeting_id={l64.zoom_meeting_id}")
    print(f"recordings count={l64.recordings.count()}")
except:
    print("Not found")

print("\n=== LAST 5 RECORDINGS ===")
for r in LessonRecording.objects.order_by('-created_at')[:5]:
    print(f"ID={r.id} lesson={r.lesson_id} status={r.status} provider={r.storage_provider} created={r.created_at}")
