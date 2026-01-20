#!/bin/bash
cd /var/www/teaching_panel/teaching_panel
../venv/bin/python manage.py shell -c "
from homework.models import StudentSubmission

print('All submissions:')
for s in StudentSubmission.objects.order_by('-id')[:10]:
    print(f'  #{s.id}: status={s.status}, submitted_at={s.submitted_at}, answers_count={s.answers.count()}')
"
