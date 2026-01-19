#!/usr/bin/env python
"""Test raw API response for student"""
import os
import json
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from django.test import RequestFactory
from rest_framework.test import force_authenticate
from homework.views import HomeworkViewSet
from django.contrib.auth import get_user_model

User = get_user_model()

# Get student
student = User.objects.filter(role='student', is_active=True).first()
print(f"Student: {student.email if student else 'NOT FOUND'}")

if student:
    factory = RequestFactory()
    request = factory.get('/api/homework/')
    force_authenticate(request, user=student)
    
    view = HomeworkViewSet.as_view({'get': 'list'})
    response = view(request)
    response.render()
    
    data = json.loads(response.content)
    print(f"\nTotal homework: {data.get('count', len(data.get('results', [])))}")
    
    # Get first homework with questions
    for hw in data.get('results', []):
        hw_id = hw.get('id')
        title = hw.get('title', 'untitled')
        questions = hw.get('questions', [])
        
        print(f"\n=== HW{hw_id}: {title[:40]} ===")
        print(f"Questions count: {len(questions)}")
        
        for q in questions[:3]:
            config = q.get('config', {})
            img_url = config.get('imageUrl', 'NO IMAGE')
            if img_url != 'NO IMAGE':
                img_url = img_url[:60] + '...'
            print(f"  Q{q['id']}: imageUrl={img_url}")
