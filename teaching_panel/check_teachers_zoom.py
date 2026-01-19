import django
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "teaching_panel.settings")
django.setup()

from accounts.models import CustomUser
from django.utils import timezone

# Get all teachers
teachers = CustomUser.objects.filter(role='teacher')

print(f"Total teachers: {teachers.count()}")
print()

for t in teachers:
    has_zoom_creds = bool(t.zoom_account_id and t.zoom_client_id and t.zoom_client_secret)
    print(f"ID={t.id} email={t.email}")
    print(f"  zoom_account_id: {bool(t.zoom_account_id)}")
    print(f"  zoom_client_id: {bool(t.zoom_client_id)}")
    print(f"  zoom_client_secret: {bool(t.zoom_client_secret)}")
    print(f"  zoom_user_id: {t.zoom_user_id}")
    print(f"  HAS COMPLETE ZOOM CREDS: {has_zoom_creds}")
    print()
