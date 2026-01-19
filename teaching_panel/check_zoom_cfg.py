import django
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "teaching_panel.settings")
django.setup()

from django.conf import settings

print("ZOOM_ACCOUNT_ID:", bool(getattr(settings, 'ZOOM_ACCOUNT_ID', '')))
print("ZOOM_CLIENT_ID:", bool(getattr(settings, 'ZOOM_CLIENT_ID', '')))
print("ZOOM_CLIENT_SECRET:", bool(getattr(settings, 'ZOOM_CLIENT_SECRET', '')))
print("ZOOM_WEBHOOK_SECRET:", bool(getattr(settings, 'ZOOM_WEBHOOK_SECRET', '')))
