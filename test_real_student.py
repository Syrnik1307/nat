#!/usr/bin/env python
"""Test API for real student who has homework with images"""
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

# Get real student from HW37
student = User.objects.filter(email='guriev.dmitriy.y@gmail.com').first()
if not student:
    student = User.objects.filter(email='yugay.slava.2023@inbox.ru').first()

print(f"Testing with student: {student.email if student else 'NOT FOUND'}")

if student:
    factory = RequestFactory()
    request = factory.get('/api/homework/')
    force_authenticate(request, user=student)
    
    view = HomeworkViewSet.as_view({'get': 'list'})
    response = view(request)
    response.render()
    
    data = json.loads(response.content)
    results = data.get('results', [])
    print(f"\nHomework visible to student: {len(results)}")
    
    for hw in results:
        hw_id = hw.get('id')
        title = hw.get('title', 'untitled')[:40]
        questions = hw.get('questions', [])
        
        print(f"\n=== HW{hw_id}: {title} ===")
        print(f"Questions: {len(questions)}")
        
        for q in questions:
            config = q.get('config', {})
            img_url = config.get('imageUrl')
            if img_url:
                print(f"  Q{q['id']}: imageUrl={img_url[:70]}...")
            else:
                print(f"  Q{q['id']}: NO IMAGE")
