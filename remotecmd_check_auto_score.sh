#!/bin/bash
cd /var/www/teaching_panel/teaching_panel
../venv/bin/python manage.py shell -c "
from homework.models import Answer, StudentSubmission
from django.utils import timezone

# Все ответы
total_answers = Answer.objects.count()
print(f'Total answers: {total_answers}')

# Ответы с auto_score
answers_with_auto = Answer.objects.filter(auto_score__isnull=False).count()
print(f'Answers with auto_score: {answers_with_auto}')

# Ответы с submitted_at (важно для статистики)
submitted_submissions = StudentSubmission.objects.filter(submitted_at__isnull=False).count()
print(f'Submitted submissions: {submitted_submissions}')

# Последние 5 ответов
print('\\nLatest 5 answers:')
for a in Answer.objects.order_by('-id')[:5]:
    print(f'  Answer #{a.id}: q_type={a.question.question_type}, auto_score={a.auto_score}, submission_status={a.submission.status}')
"
