"""Проверка уроков группы"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from schedule.models import Lesson, Group

g = Group.objects.get(id=1)
print(f"Group: {g.name}")
lessons = Lesson.objects.filter(group=g).order_by("start_time")
print(f"Lessons count: {lessons.count()}")
for l in lessons[:15]:
    dt = l.start_time.strftime("%Y-%m-%d %H:%M") if l.start_time else "N/A"
    title = l.title[:40] if l.title else "No title"
    print(f"  {l.id} | {dt} | {title}")
