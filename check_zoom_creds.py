from schedule.models import LessonRecording, Lesson
from django.contrib.auth import get_user_model

User = get_user_model()

# Проверим учителя урока 65
lesson = Lesson.objects.get(id=65)
teacher = lesson.teacher

print(f"Teacher: {teacher.email}")
print(f"Zoom Account ID: {teacher.zoom_account_id or 'NOT SET'}")
print(f"Zoom Client ID: {teacher.zoom_client_id or 'NOT SET'}")
print(f"Zoom Client Secret: {'SET' if teacher.zoom_client_secret else 'NOT SET'}")
print(f"Zoom User ID: {teacher.zoom_user_id or 'NOT SET'}")

# Проверим глобальные настройки Zoom
from django.conf import settings
print(f"\nGlobal Zoom Account ID: {getattr(settings, 'ZOOM_ACCOUNT_ID', 'NOT SET')}")
print(f"Global Zoom Client ID: {getattr(settings, 'ZOOM_CLIENT_ID', 'NOT SET')}")
print(f"Global Zoom Client Secret: {'SET' if getattr(settings, 'ZOOM_CLIENT_SECRET', None) else 'NOT SET'}")
