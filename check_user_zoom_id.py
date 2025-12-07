#!/usr/bin/env python
import os, sys, django
sys.path.insert(0, '/var/www/teaching_panel/teaching_panel')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from accounts.models import CustomUser

u = CustomUser.objects.get(email="syrnik131313@gmail.com")
print(f"User ID: {u.id}")
print(f"Role: {u.role}")
print(f"Zoom User ID: {u.zoom_user_id or 'NOT SET'}")
