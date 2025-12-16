#!/usr/bin/env python
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE","teaching_panel.settings")
import django; django.setup()
from schedule.gdrive_utils import GoogleDriveManager

gd = GoogleDriveManager()
svc = gd.service
root_id = 'root'
print(f"MY DRIVE ROOT: {root_id}")
res = svc.files().list(q="'root' in parents and trashed=false", fields="files(id,name,mimeType)", pageSize=100).execute()
for f in res.get('files',[]):
    kind = 'FOLDER' if 'folder' in f.get('mimeType','') else 'FILE'
    print(f"[{kind}] {f['name']}")
