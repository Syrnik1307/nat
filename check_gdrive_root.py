#!/usr/bin/env python
"""Check GDrive root folder and its contents."""
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "teaching_panel.settings")
import django
django.setup()

from schedule.gdrive_utils import GoogleDriveManager
from django.conf import settings

gdrive = GoogleDriveManager()
service = gdrive.service
if not service:
    print("ERROR: GDrive service not available")
    exit(1)

root_id = settings.GDRIVE_ROOT_FOLDER_ID
print(f"ROOT_FOLDER_ID: {root_id}")

# Check root folder exists
try:
    folder = service.files().get(fileId=root_id, fields="id, name, mimeType").execute()
    print(f"ROOT_FOLDER_NAME: {folder.get('name')}")
    print(f"ROOT_FOLDER_TYPE: {folder.get('mimeType')}")
except Exception as e:
    print(f"ERROR accessing root folder: {e}")
    exit(1)

# List contents of root folder
results = service.files().list(
    q=f"'{root_id}' in parents and trashed=false",
    fields="files(id, name, mimeType)",
    pageSize=50
).execute()

files = results.get("files", [])
print(f"\nFOLDERS IN ROOT ({len(files)} items):")
for f in files:
    ftype = "FOLDER" if "folder" in f.get("mimeType", "") else "FILE"
    print(f"  [{ftype}] {f.get('name')}")
