$script = @'
from schedule.models import Lesson, Group
from django.utils import timezone
now = timezone.now()

print('=== GROUPS INFO 1.1 ===')
groups = Group.objects.filter(name__icontains='1.1')
for g in groups:
    print(f'ID={g.id}, name={g.name}')

print()
print('=== RECENT LESSONS (1 hour) ===')
recent = Lesson.objects.filter(start_time__gte=now - timezone.timedelta(hours=1)).order_by('-start_time')
for l in recent:
    print(f'ID={l.id}, group={l.group.name if l.group else None}, active={l.is_active}, zoom={bool(l.zoom_join_url)}')

print()
print('=== ALL ACTIVE LESSONS ===')
active = Lesson.objects.filter(is_active=True)
for l in active:
    print(f'ID={l.id}, group={l.group.name if l.group else None}, start={l.start_time}, zoom={bool(l.zoom_join_url)}')
'@

$script | Out-File -FilePath "check_lessons_temp.py" -Encoding utf8

# Copy to server and run
scp check_lessons_temp.py tp:/tmp/check_lessons.py
ssh tp "cd /var/www/teaching_panel/teaching_panel && source ../venv/bin/activate && python manage.py shell < /tmp/check_lessons.py"

Remove-Item check_lessons_temp.py
