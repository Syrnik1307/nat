#!/usr/bin/env python
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE","teaching_panel.settings")
import django; django.setup()

from django.utils import timezone
from django.contrib.auth import get_user_model
from accounts.models import Subscription
from accounts.gdrive_folder_service import create_teacher_folder_on_subscription
from schedule.gdrive_utils import GoogleDriveManager

TEACHER_EMAIL = "syrnik1307@gmail.com"  # change if needed

User = get_user_model()
try:
    user = User.objects.get(email=TEACHER_EMAIL)
except User.DoesNotExist:
    print(f"User not found: {TEACHER_EMAIL}")
    raise SystemExit(1)

sub = Subscription.objects.filter(user=user).order_by('-id').first()
if not sub:
    print("Subscription not found for user")
    raise SystemExit(1)

# Ensure subscription is active for the test
if not sub.status == 'active' or sub.expires_at is None or sub.expires_at < timezone.now():
    print("WARNING: Subscription is not active; proceeding to create folder anyway for test.")

if not sub.gdrive_folder_id:
    print("No folder linked yet; creating...")
    create_teacher_folder_on_subscription(sub)
    sub.refresh_from_db()
else:
    print(f"Folder already linked: {sub.gdrive_folder_id}")

folder_id = sub.gdrive_folder_id
print(f"Teacher folder id: {folder_id}")

# Upload a tiny test file into the teacher folder
gd = GoogleDriveManager()
svc = gd.service
from googleapiclient.http import MediaInMemoryUpload

content = b"Hello from Teaching Panel test upload at " + timezone.now().isoformat().encode('utf-8')
media = MediaInMemoryUpload(content, mimetype='text/plain', resumable=False)
file_metadata = {"name": "TP_test_upload.txt", "parents": [folder_id]}
res = svc.files().create(body=file_metadata, media_body=media, fields="id,name,webViewLink").execute()
print("Uploaded:", res)
