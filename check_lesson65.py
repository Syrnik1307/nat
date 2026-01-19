from schedule.models import LessonRecording, Lesson

# Все записи для урока 65
print("=== Все записи для урока 65 ===")
recs = LessonRecording.objects.filter(lesson_id=65).order_by('created_at')
for r in recs:
    print(f"ID: {r.id}")
    print(f"  Title: {r.title}")  
    print(f"  Duration: {r.duration} sec")
    print(f"  File size: {r.file_size}")
    print(f"  Zoom ID: {r.zoom_recording_id}")
    print(f"  Status: {r.status}")
    print(f"  GDrive: {r.gdrive_file_id}")
    print(f"  recording_start: {r.recording_start}")
    print(f"  recording_end: {r.recording_end}")
    print("---")

# Проверим урок
lesson = Lesson.objects.get(id=65)
print(f"\nУрок 65: {lesson.title}")
print(f"  Группа: {lesson.group.name if lesson.group else 'N/A'}")
print(f"  Время: {lesson.start_time} - {lesson.end_time}")
print(f"  Zoom Meeting ID: {lesson.zoom_meeting_id}")
print(f"  Записей всего: {lesson.recordings.count()}")
