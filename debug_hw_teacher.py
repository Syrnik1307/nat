#!/usr/bin/env python
"""Debug script to check homework images on production - for TEACHER view."""
import os
import sys
import json

# Setup Django - правильный путь
sys.path.insert(0, '/var/www/teaching_panel/teaching_panel')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')

import django
django.setup()

from homework.models import Homework, Question, StudentSubmission
from homework.serializers import HomeworkSerializer

# Ищем ДЗ "Свойства Логарифма"
hw = Homework.objects.filter(title__iexact='Свойства Логарифма').first()
if not hw:
    hw = Homework.objects.filter(title__icontains='свойства').filter(title__icontains='логарифм').first()

if hw:
    print(f'HW ID: {hw.id}, Title: {hw.title}')
    print()
    
    # Сериализуем как для учителя (HomeworkSerializer)
    serialized = HomeworkSerializer(hw).data
    
    print('=== QUESTIONS FROM HomeworkSerializer ===')
    for q in serialized.get('questions', []):
        print(f"Q{q.get('order', '?')} ID={q.get('id')}")
        print(f"  prompt: {(q.get('prompt', '') or '')[:50]}")
        cfg = q.get('config', {})
        print(f"  config.imageUrl: {cfg.get('imageUrl', 'NONE')[:60] if cfg.get('imageUrl') else 'NONE'}")
        print(f"  config.imageFileId: {cfg.get('imageFileId', 'NONE')}")
        print()
    
    # Проверяем уникальность
    file_ids = [q.get('config', {}).get('imageFileId', 'NONE') for q in serialized.get('questions', [])]
    from collections import Counter
    counts = Counter(file_ids)
    print('=== DUPLICATE CHECK IN SERIALIZED DATA ===')
    has_dups = False
    for fid, cnt in counts.items():
        if cnt > 1:
            has_dups = True
            print(f'DUPLICATE: {fid} appears {cnt} times')
    if not has_dups:
        print('No duplicates found')
else:
    print('Homework not found')
