#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from homework.models import Answer, Question, Choice

print("=== Testing evaluate() ===")

# Find an answer that has auto_score=0 but selected a correct choice
a = Answer.objects.filter(
    question__question_type='SINGLE_CHOICE',
    auto_score=0
).select_related('question').first()

if not a:
    print("No answer with auto_score=0 found")
    sys.exit(1)

q = a.question

print(f"Question: {q.id}, points: {q.points}")
print(f"Config: {q.config}")

correct = q.choices.filter(is_correct=True).first()
print(f"Correct choice: {correct.id if correct else 'None'}")
print(f"All choices: {[(c.id, c.is_correct) for c in q.choices.all()]}")

print(f"\nAnswer already found: {a.id}")
print(f"Selected: {list(a.selected_choices.values_list('id', flat=True))}")
print(f"Auto score before: {a.auto_score}")

# Check what the user selected
selected = list(a.selected_choices.all())
print(f"User selected: {[(c.id, c.is_correct) for c in selected]}")

# Evaluate
old_score = a.auto_score
a.evaluate()
print(f"Auto score after evaluate: {a.auto_score} (was {old_score})")

# Refresh from db
a.refresh_from_db()
print(f"Auto score after refresh: {a.auto_score}")
