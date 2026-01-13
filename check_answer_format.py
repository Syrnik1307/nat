#!/usr/bin/env python
"""Check answer format returned by serializer."""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
os.chdir(os.path.join(os.path.dirname(__file__), 'teaching_panel'))
sys.path.insert(0, os.getcwd())
django.setup()

from homework.models import StudentSubmission
from homework.serializers import StudentSubmissionSerializer

sub = StudentSubmission.objects.get(id=25)
s = StudentSubmissionSerializer(sub)
answers = s.data.get('answers', [])

print(f"ANSWERS_TYPE: {type(answers).__name__}")
print(f"ANSWERS_LEN: {len(answers) if isinstance(answers, list) else 'N/A'}")

if answers and isinstance(answers, list):
    for a in answers[:3]:
        print(f"ANSWER: question={a.get('question')}, text_answer='{a.get('text_answer')}', selected_choices={a.get('selected_choices')}")
