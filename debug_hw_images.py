#!/usr/bin/env python
"""Debug script to check homework images on production."""
import os
import sys

# Setup Django - правильный путь
sys.path.insert(0, '/var/www/teaching_panel/teaching_panel')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')

import django
django.setup()

from homework.models import Homework, Question, StudentSubmission
from homework.serializers import QuestionStudentSerializer, HomeworkStudentSerializer

# Ищем ДЗ "Свойства Логарифма"
hw = Homework.objects.filter(title__iexact='Свойства Логарифма').first()
if not hw:
    hw = Homework.objects.filter(title__icontains='свойства').filter(title__icontains='логарифм').first()

if hw:
    print(f'HW ID: {hw.id}, Title: {hw.title}')
    print(f'Questions count: {hw.questions.count()}')
    print()
    print('=== RAW DB DATA (config) ===')
    for q in hw.questions.all().order_by('order'):
        cfg = q.config or {}
        print(f'Q{q.order} ID={q.id}: imageFileId={cfg.get("imageFileId", "NONE")}')
    
    print()
    print('=== SERIALIZED FOR STUDENT (QuestionStudentSerializer) ===')
    for q in hw.questions.all().order_by('order'):
        serialized = QuestionStudentSerializer(q).data
        config = serialized.get('config', {})
        img_url = config.get('imageUrl', 'NO IMAGE')[:60] if config.get('imageUrl') else 'NO IMAGE'
        img_file_id = config.get('imageFileId', 'NONE')
        print(f'Q{q.order} ID={q.id}: imageFileId={img_file_id}')
        print(f'    imageUrl={img_url}...')
    
    print()
    print('=== CHECK FOR DUPLICATES IN SERIALIZED DATA ===')
    file_ids = []
    for q in hw.questions.all().order_by('order'):
        serialized = QuestionStudentSerializer(q).data
        config = serialized.get('config', {})
        file_ids.append(config.get('imageFileId', 'NONE'))
    
    from collections import Counter
    counts = Counter(file_ids)
    has_dups = False
    for fid, cnt in counts.items():
        if cnt > 1:
            has_dups = True
            print(f'DUPLICATE: {fid} appears {cnt} times')
    
    if not has_dups:
        print('No duplicates found in serialized data')
else:
    print('Homework not found')
