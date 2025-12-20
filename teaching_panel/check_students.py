#!/usr/bin/env python
"""Check students in the system"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from accounts.models import CustomUser

students = CustomUser.objects.filter(role='student')
print(f"Всего студентов: {students.count()}")
for s in students[:10]:
    chat_id = s.telegram_chat_id or "НЕТ"
    print(f"  {s.email} - chat_id: {chat_id}")
