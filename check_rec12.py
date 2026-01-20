from schedule.models import LessonRecording, Lesson

# Запись 12
r = LessonRecording.objects.get(id=12)
print(f"Recording {r.id}:")
print(f"  Title: {r.title}")
print(f"  Status: {r.status}")
print(f"  GDrive File ID: '{r.gdrive_file_id}'")
print(f"  Archive Key: '{r.archive_key}'")
print(f"  Archive URL: '{r.archive_url}'")
print(f"  Play URL: '{r.play_url}'")
print(f"  Download URL: '{r.download_url}'")
print(f"  Storage Provider: {r.storage_provider}")
print(f"  Zoom Recording ID: '{r.zoom_recording_id}'")
print(f"  Lesson ID: {r.lesson_id}")

if r.lesson:
    lesson = r.lesson
    print(f"\nLesson {lesson.id}:")
    print(f"  Title: {lesson.title}")
    print(f"  Zoom Meeting ID: {lesson.zoom_meeting_id}")
    print(f"  Start: {lesson.start_time}")
