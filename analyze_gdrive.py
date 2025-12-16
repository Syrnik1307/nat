#!/usr/bin/env python
"""Analyze all GDrive folders."""
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "teaching_panel.settings")
import django
django.setup()

from schedule.gdrive_utils import GoogleDriveManager
from django.conf import settings
from accounts.models import Subscription
from collections import Counter

gdrive = GoogleDriveManager()
service = gdrive.service

root_id = settings.GDRIVE_ROOT_FOLDER_ID
print(f"ROOT_ID: {root_id}")

# Get ALL folders in root
all_folders = []
page_token = None
while True:
    results = service.files().list(
        q=f"'{root_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="nextPageToken, files(id, name)",
        pageSize=100,
        pageToken=page_token
    ).execute()
    all_folders.extend(results.get("files", []))
    page_token = results.get("nextPageToken")
    if not page_token:
        break

print(f"Total folders in TeachingPanel: {len(all_folders)}")

# Group by name
names = [f['name'] for f in all_folders]
counts = Counter(names)
print("\nFolder counts (top 20):")
for name, count in counts.most_common(20):
    print(f"  {name}: {count}")

# Check which are linked to subscriptions  
subs_with_folders = Subscription.objects.exclude(gdrive_folder_id='').exclude(gdrive_folder_id__isnull=True)
linked_ids = set(s.gdrive_folder_id for s in subs_with_folders)
print(f"\nFolders linked to subscriptions: {len(linked_ids)}")

# Orphan folders
orphan_count = 0
for f in all_folders:
    if f['id'] not in linked_ids:
        orphan_count += 1
print(f"Orphan folders (can be cleaned): {orphan_count}")
