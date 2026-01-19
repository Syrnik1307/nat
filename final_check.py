#!/usr/bin/env python
"""Final check for broken image URLs"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from homework.models import Question

broken = 0
gdrive = 0
none_count = 0

for q in Question.objects.filter(homework__status='published'):
    cfg = q.config or {}
    img = cfg.get('imageUrl', '')
    
    if not img:
        none_count += 1
    elif img.startswith('https://drive.google.com'):
        gdrive += 1
    elif img.startswith('https://'):
        gdrive += 1  # other valid https
    else:
        print(f'BROKEN: HW{q.homework_id} Q{q.id}: {img}')
        broken += 1

print(f"\n=== SUMMARY ===")
print(f"With valid GDrive URL: {gdrive}")
print(f"Without image: {none_count}")
print(f"BROKEN URLs: {broken}")
