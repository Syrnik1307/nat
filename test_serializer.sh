#!/bin/bash
cd /var/www/teaching_panel
source venv/bin/activate
python <<'EOF'
import os, sys, django
sys.path.insert(0, '/var/www/teaching_panel/teaching_panel')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from schedule.serializers import LessonRecordingSerializer
from schedule.models import LessonRecording

lr = LessonRecording.objects.filter(lesson_id=17).first()
if lr:
    ser = LessonRecordingSerializer(lr)
    print("duration_display:", ser.data.get('duration_display'))
    print("lesson_info:", ser.data.get('lesson_info'))
else:
    print("No recording")
EOF
