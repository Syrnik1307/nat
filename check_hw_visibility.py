#!/usr/bin/env python
"""Check student groups and homework visibility"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from homework.models import Homework
from schedule.models import Group
from django.contrib.auth import get_user_model

User = get_user_model()

print("=== ALL STUDENTS ===")
for s in User.objects.filter(role='student', is_active=True):
    # Get groups where student is a member
    student_groups = Group.objects.filter(students=s)
    print(f"{s.email} (id={s.id}) - groups: {list(student_groups.values_list('id', 'name'))}")

print("\n=== PUBLISHED HOMEWORK ASSIGNMENTS ===")
for hw in Homework.objects.filter(status='published').order_by('-id')[:10]:
    assigned_groups = list(hw.assigned_groups.values_list('id', 'name'))
    assigned_students = list(hw.assigned_students.values_list('id', 'email'))
    print(f"HW{hw.id}: {hw.title[:30]} | groups={assigned_groups} | students={assigned_students}")

print("\n=== MATCHING CHECK ===")
for s in User.objects.filter(role='student', is_active=True)[:3]:
    student_groups = Group.objects.filter(students=s)
    student_group_ids = set(student_groups.values_list('id', flat=True))
    
    visible_hw = []
    for hw in Homework.objects.filter(status='published'):
        hw_group_ids = set(hw.assigned_groups.values_list('id', flat=True))
        hw_student_ids = set(hw.assigned_students.values_list('id', flat=True))
        
        if student_group_ids & hw_group_ids:
            visible_hw.append(f"HW{hw.id}(group)")
        if s.id in hw_student_ids:
            visible_hw.append(f"HW{hw.id}(direct)")
    
    print(f"{s.email}: can see {visible_hw}")
