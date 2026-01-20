cd /var/www/teaching_panel/teaching_panel
../venv/bin/python manage.py shell -c "
from homework.models import StudentSubmission
for s in StudentSubmission.objects.all():
    print(s.id, s.status, getattr(s, 'homework_id', None), getattr(s, 'student_id', None))
"
