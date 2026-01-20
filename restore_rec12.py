from schedule.models import LessonRecording

# Восстанавливаю запись 12
r = LessonRecording.objects.get(id=12)
r.status = 'ready'
r.save()

print(f"RESTORED Recording {r.id}:")
print(f"  Title: {r.title}")
print(f"  Status: {r.status}")
print(f"  Play URL exists: {bool(r.play_url)}")
