#!/bin/bash
cd /var/www/teaching_panel/teaching_panel
../venv/bin/python manage.py shell -c "
from schedule.models import Group
qs = Group.objects.all()
print('Groups count:', qs.count())
for g in qs[:10]:
    print(g.id, repr(g.name), 'students:', g.students.count())
"
