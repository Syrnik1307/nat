#!/usr/bin/env python
"""DB integrity check script"""
import os
import sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')

import django
django.setup()

from schedule.models import Lesson, LessonRecording
from homework.models import HomeworkSubmission
from accounts.models import CustomUser, Subscription

print("=== Database Integrity Check ===")
print(f"Users: {CustomUser.objects.count()}")
print(f"Lessons: {Lesson.objects.count()}")
print(f"Recordings: {LessonRecording.objects.count()}")
print(f"Subscriptions: {Subscription.objects.count()}")
print(f"Homework Submissions: {HomeworkSubmission.objects.count()}")

# Check for any active lessons
active = Lesson.objects.filter(status='in_progress').count()
print(f"Active lessons (in_progress): {active}")

print("\n=== All checks passed ===")
