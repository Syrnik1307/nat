#!/bin/bash
cd /var/www/teaching_panel/teaching_panel
../venv/bin/python manage.py shell -c "
from homework.models import StudentSubmission
from django.utils import timezone

# Помечаем submission #39 как submitted/graded
s = StudentSubmission.objects.get(id=39)
print(f'Before: status={s.status}, submitted_at={s.submitted_at}')

s.status = 'graded'
s.submitted_at = timezone.now()
s.graded_at = timezone.now()
s.save()

print(f'After: status={s.status}, submitted_at={s.submitted_at}')

# Проверяем статистику
from homework.models import Answer
auto_graded = Answer.objects.filter(
    submission__submitted_at__isnull=False,
    auto_score__isnull=False,
).count()
print(f'\\nAuto-graded answers (submitted): {auto_graded}')
print(f'Time saved: {auto_graded * 2} minutes')
"
