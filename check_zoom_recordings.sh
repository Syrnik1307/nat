#!/bin/bash
cd /var/www/teaching_panel/teaching_panel
source ../venv/bin/activate
python manage.py shell << 'EOF'
from schedule.models import Lesson, LessonRecording
from schedule.zoom_client import ZoomAPIClient
from django.conf import settings

print("=== LESSON 64 CHECK ===")
lesson = Lesson.objects.get(id=64)
print(f"zoom_meeting_id: {lesson.zoom_meeting_id}")
print(f"record_lesson: {lesson.record_lesson}")
print(f"recordings count: {lesson.recordings.count()}")

# Получаем credentials
print("\n=== ZOOM CREDENTIALS ===")
print(f"ZOOM_ACCOUNT_ID: {bool(settings.ZOOM_ACCOUNT_ID)}")
print(f"ZOOM_CLIENT_ID: {bool(settings.ZOOM_CLIENT_ID)}")
print(f"ZOOM_CLIENT_SECRET: {bool(settings.ZOOM_CLIENT_SECRET)}")
print(f"ZOOM_WEBHOOK_SECRET_TOKEN: {bool(getattr(settings, 'ZOOM_WEBHOOK_SECRET_TOKEN', ''))}")

if settings.ZOOM_ACCOUNT_ID and settings.ZOOM_CLIENT_ID:
    print("\n=== ZOOM API TEST ===")
    try:
        api = ZoomAPIClient(
            settings.ZOOM_ACCOUNT_ID,
            settings.ZOOM_CLIENT_ID,
            settings.ZOOM_CLIENT_SECRET
        )
        print(f"ZoomAPIClient created")
        
        # Попробуем получить список записей пользователя
        from datetime import datetime, timedelta
        from_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        recs = api.list_user_recordings(from_date=from_date)
        print(f"Recordings response: {recs}")
    except Exception as e:
        print(f"API error: {type(e).__name__}: {e}")
EOF
