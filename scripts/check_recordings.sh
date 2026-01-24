#!/bin/bash
cd /var/www/teaching_panel/teaching_panel
export PYTHONPATH=/var/www/teaching_panel/teaching_panel
export DJANGO_SETTINGS_MODULE=teaching_panel.settings

/var/www/teaching_panel/venv/bin/python << 'EOF'
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')

import django
django.setup()

from schedule.models import LessonRecording

print("=== Last 3 ready recordings ===")
for r in LessonRecording.objects.filter(status='ready').order_by('-id')[:3]:
    print(f"\nID: {r.id}")
    print(f"  Title: {r.title}")
    print(f"  gdrive_file_id: {r.gdrive_file_id}")
    print(f"  play_url: {r.play_url}")
    print(f"  storage_provider: {r.storage_provider}")
    print(f"  file_size: {r.file_size}")
EOF
