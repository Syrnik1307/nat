from schedule.models import LessonRecording

# Помечаем запись как удалённую
r = LessonRecording.objects.get(id=12)
r.status = 'deleted'
r.save()

print(f"Recording {r.id} marked as deleted - file no longer exists on Zoom")
