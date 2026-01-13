#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from homework.models import Answer, Question, StudentSubmission

print("=== Testing sanitize_question_config ===")

from homework.serializers import HomeworkStudentSerializer, QuestionStudentSerializer, sanitize_question_config

# Get homework that contains question 67
hw = Question.objects.get(id=67).homework
print(f"Homework: {hw.id} - {hw.title}")

# Check raw config before sanitization
q = Question.objects.get(id=67)
print(f"\nRaw config for Q#67: {q.config}")

# Check sanitized config
sanitized = sanitize_question_config(q)
print(f"Sanitized config: {sanitized}")

# Serialize it for student
serializer = HomeworkStudentSerializer(hw)
data = serializer.data

print(f"\nSerialized data for SINGLE/MULTI_CHOICE questions:")
for q_data in data.get('questions', []):
    if q_data['question_type'] in ('SINGLE_CHOICE', 'MULTIPLE_CHOICE'):
        print(f"  Q#{q_data['id']} ({q_data['question_type']})")
        print(f"    choices: {q_data.get('choices', [])}")
        print(f"    config.options: {q_data.get('config', {}).get('options', 'NOT PRESENT (GOOD!)')}")
