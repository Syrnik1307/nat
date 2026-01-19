#!/bin/bash
cd /var/www/teaching_panel/teaching_panel
source ../venv/bin/activate
python << 'PYEOF'
from schedule.models import Lesson, Group

print("=== ACTIVE LESSONS ===")
active = Lesson.objects.filter(is_active=True)
print(f"Count: {active.count()}")
for l in active:
    gname = l.group.name if l.group else "NO_GROUP"
    print(f"  ID={l.id} group='{gname}' is_quick={l.is_quick_lesson} zoom={bool(l.zoom_join_url)}")
    if l.group:
        students = l.group.students.all()
        print(f"    Students in group: {[s.email for s in students]}")

print("\n=== GROUP INFO 1.1 ===")
g = Group.objects.filter(name__icontains="1.1").first()
if g:
    print(f"Group ID={g.id}, name={g.name}")
    print(f"Students: {[s.email for s in g.students.all()]}")
PYEOF
