#!/usr/bin/env python
"""Check who can see HW with images"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from schedule.models import Group
from homework.models import Homework

# HW36 and HW37 have images
for hw_id in [36, 37]:
    hw = Homework.objects.get(id=hw_id)
    print(f"\n=== HW{hw_id}: {hw.title[:40]} ===")
    
    # Get assigned groups
    for g in hw.assigned_groups.all():
        print(f"Group: {g.name} (id={g.id})")
        students = list(g.students.values_list('email', 'first_name', 'last_name'))
        for s in students:
            print(f"  - {s[0]} ({s[1]} {s[2]})")
    
    # Get directly assigned students
    direct = list(hw.assigned_students.values_list('email', 'first_name', 'last_name'))
    if direct:
        print("Direct assignments:")
        for s in direct:
            print(f"  - {s[0]} ({s[1]} {s[2]})")
