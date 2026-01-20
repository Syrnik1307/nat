#!/bin/bash
cd /var/www/teaching_panel/teaching_panel
../venv/bin/python manage.py shell -c "
from homework.models import Answer, StudentSubmission

# Группируем ответы по submission
print('Answers by submission:')
from django.db.models import Count
for s in StudentSubmission.objects.annotate(cnt=Count('answers')).filter(cnt__gt=0).order_by('-id'):
    print(f'  Submission #{s.id}: status={s.status}, submitted_at={s.submitted_at}, answers={s.cnt}')
    for a in s.answers.all()[:3]:
        print(f'    Answer #{a.id}: q_type={a.question.question_type}, auto_score={a.auto_score}')
"
