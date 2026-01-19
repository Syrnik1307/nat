#!/usr/bin/env python
"""Test student API access to homework with images"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

import json
from homework.models import Homework, Question
from homework.serializers import HomeworkStudentSerializer
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory
from rest_framework.request import Request

User = get_user_model()

# Find a student
student = User.objects.filter(role='student').first()
if not student:
    print("No student found!")
    exit(1)

print(f"Student: {student.email}")

# Get HW36 (has images)
hw = Homework.objects.filter(id=36).first()
if not hw:
    print("HW36 not found!")
    exit(1)

print(f"Homework: {hw.id} - {hw.title}")

# Serialize as student sees it
factory = APIRequestFactory()
request = factory.get('/api/homework/36/')
request.user = student

serializer = HomeworkStudentSerializer(hw, context={'request': Request(request)})
data = serializer.data

print("\n=== Serialized Data (questions config) ===")
for q in data.get('questions', []):
    config = q.get('config', {})
    image_url = config.get('imageUrl', 'NO_IMAGE')
    print(f"Q{q['id']}: imageUrl={image_url[:80] if image_url else 'NONE'}...")
