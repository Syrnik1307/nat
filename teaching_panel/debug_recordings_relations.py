#!/usr/bin/env python
"""Debug recording relations"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from schedule.models import LessonRecording

for r in LessonRecording.objects.all().select_related('lesson__group__teacher', 'lesson__teacher'):
    lesson = r.lesson
    group = lesson.group if lesson else None
    teacher = group.teacher if group else (lesson.teacher if lesson else None)
    
    print(f"ID={r.id} | lesson={lesson.id if lesson else 'None'} | group={group.id if group else 'None'} | teacher={teacher.email if teacher else 'None'}")
    
    if teacher:
        has_zoom = bool(teacher.zoom_account_id and teacher.zoom_client_id)
        print(f"    has_zoom_creds={has_zoom}")
