$pythonCode = @'
import django
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "teaching_panel.settings")
django.setup()

from schedule.models import LessonRecording, Lesson
from django.utils import timezone

now = timezone.now()
cutoff = now - timezone.timedelta(hours=3)

print("=== RECORDINGS (last 3h) ===")
recs = LessonRecording.objects.filter(created_at__gte=cutoff)
print(f"Count: {recs.count()}")
for r in recs:
    print(f"  ID={r.id} status={r.status} provider={r.storage_provider}")

print()
print("=== LESSONS with record_lesson=True (last 3h) ===")
lessons = Lesson.objects.filter(start_time__gte=cutoff, record_lesson=True)
print(f"Count: {lessons.count()}")
for l in lessons:
    grp = l.group.name if l.group else "N/A"
    print(f"  ID={l.id} group={grp} zoom_meeting_id={l.zoom_meeting_id}")

print()
print("=== ALL LESSONS (last 3h) ===")
all_lessons = Lesson.objects.filter(start_time__gte=cutoff)
print(f"Count: {all_lessons.count()}")
for l in all_lessons:
    grp = l.group.name if l.group else "N/A"
    print(f"  ID={l.id} group={grp} record={l.record_lesson} zoom_id={l.zoom_meeting_id}")
'@

$pythonCode | ssh tp 'cat > /tmp/check_recs.py && cd /var/www/teaching_panel/teaching_panel && source ../venv/bin/activate && python /tmp/check_recs.py'
