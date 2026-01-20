from schedule.models import LessonRecording
r = LessonRecording.objects.get(id=13)
r.duration = 559
r.save()
print(f"Updated: duration={r.duration}")
