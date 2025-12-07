#!/usr/bin/env python
import os, sys, django
sys.path.insert(0, '/var/www/teaching_panel/teaching_panel')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from accounts.models import CustomUser

u = CustomUser.objects.get(email="syrnik131313@gmail.com")
print(f"Before: User {u.id} zoom_user_id = {u.zoom_user_id or 'NOT SET'}")

# Set zoom_user_id to teacher's email (this is typically the Zoom user ID)
u.zoom_user_id = "syrnik131313@gmail.com"
u.save()

print(f"After: User {u.id} zoom_user_id = {u.zoom_user_id}")
print("\n✓ Updated! Now sync_missing_zoom_recordings_for_teacher should work")
