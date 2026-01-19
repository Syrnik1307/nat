from schedule.models import LessonRecording, Lesson
from django.utils import timezone

# Найти записи с названием про прототип
print("=== Записи с '25 задание' или 'прототип' ===")
recs = LessonRecording.objects.filter(title__icontains='25 задание').order_by('-created_at')[:10]
if not recs:
    recs = LessonRecording.objects.filter(title__icontains='прототип').order_by('-created_at')[:10]

for r in recs:
    print(f"ID: {r.id}")
    print(f"  Title: {r.title}")
    print(f"  Duration: {r.duration} sec ({r.duration/60 if r.duration else 0:.1f} min)")
    print(f"  File size: {r.file_size} bytes ({r.file_size/(1024*1024) if r.file_size else 0:.1f} MB)")
    print(f"  Zoom ID: {r.zoom_recording_id}")
    print(f"  Status: {r.status}")
    print(f"  GDrive: {r.gdrive_file_id}")
    print(f"  Lesson ID: {r.lesson_id}")
    print(f"  Created: {r.created_at}")
    print("---")

# Проверим все записи для урока 17 (если это тот урок)
print("\n=== Все записи последних уроков ===")
lessons = Lesson.objects.filter(title__icontains='25 задание').order_by('-start_time')[:5]
for lesson in lessons:
    print(f"Lesson {lesson.id}: {lesson.title}")
    for rec in lesson.recordings.all():
        print(f"  -> Rec {rec.id}: zoom_id={rec.zoom_recording_id}, dur={rec.duration}s, size={rec.file_size}")
