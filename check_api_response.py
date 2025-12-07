#!/usr/bin/env python
import os, sys, django
sys.path.insert(0, '/var/www/teaching_panel/teaching_panel')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from schedule.serializers import LessonRecordingSerializer
from schedule.models import LessonRecording

lr = LessonRecording.objects.filter(lesson_id=17).first()
if lr:
    serializer = LessonRecordingSerializer(lr)
    print("API Response data:")
    import json
    data = serializer.data
    print(json.dumps(data, indent=2, default=str))
else:
    print("No recording found")
