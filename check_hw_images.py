#!/usr/bin/env python
"""Check published homework questions with images"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from homework.models import Question

for q in Question.objects.filter(homework__status='published').order_by('-homework_id')[:20]:
    img = (q.config or {}).get('imageUrl', 'NO_IMAGE')
    if img != 'NO_IMAGE':
        img = img[:70]
    print(f"HW{q.homework_id} Q{q.id}: {img}")
