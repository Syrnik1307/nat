from schedule.models import Lesson

# Check active lessons
active = Lesson.objects.filter(is_active=True)
print(f"Active lessons count: {active.count()}")
for l in active:
    gname = l.group.name if l.group else 'NO GROUP'
    print(f"ID={l.id}, group={gname}, is_quick={l.is_quick_lesson}, zoom={bool(l.zoom_join_url)}")
