from schedule.models import LessonRecording

# Обновляем запись 13 - ставим реальные данные
recording = LessonRecording.objects.get(id=13)

# Файл на GDrive только 9 минут, обновляем duration чтобы соответствовало реальности
# 9:19 = 559 секунд
recording.duration = 559
recording.save()

print(f"Updated recording {recording.id}")
print(f"  Duration: {recording.duration} sec ({recording.duration/60:.1f} min)")
print(f"  Note: Original recording had multiple parts but only first part was uploaded to GDrive")
