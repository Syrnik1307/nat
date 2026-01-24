#!/bin/bash
cd /var/www/teaching_panel/teaching_panel
export PYTHONPATH=/var/www/teaching_panel/teaching_panel
export DJANGO_SETTINGS_MODULE=teaching_panel.settings

/var/www/teaching_panel/venv/bin/python << 'EOF'
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')

import django
django.setup()

from schedule.gdrive_utils import get_gdrive_manager
from schedule.models import LessonRecording

print("=== Testing Google Drive access ===")

r = LessonRecording.objects.get(id=14)
print(f"Recording: {r.title}")
print(f"GDrive ID: {r.gdrive_file_id}")

gdrive = get_gdrive_manager()
print(f"GDrive manager initialized: {gdrive is not None}")

# Try to get file metadata
try:
    from google.auth.transport.requests import AuthorizedSession
    creds = getattr(getattr(gdrive.service, '_http', None), 'credentials', None)
    
    if creds:
        print("Credentials found")
        session = AuthorizedSession(creds)
        
        # Get file metadata first
        metadata_url = f"https://www.googleapis.com/drive/v3/files/{r.gdrive_file_id}?fields=id,name,size,mimeType"
        resp = session.get(metadata_url, timeout=30)
        print(f"Metadata response: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"  File: {data.get('name')}")
            print(f"  Size: {data.get('size')}")
            print(f"  Type: {data.get('mimeType')}")
        else:
            print(f"  Error: {resp.text[:200]}")
            
        # Try to stream first bytes
        stream_url = f"https://www.googleapis.com/drive/v3/files/{r.gdrive_file_id}?alt=media"
        resp2 = session.get(stream_url, headers={'Range': 'bytes=0-1023'}, stream=True, timeout=30)
        print(f"Stream response: {resp2.status_code}")
        print(f"Content-Type: {resp2.headers.get('Content-Type')}")
        print(f"Content-Length: {resp2.headers.get('Content-Length')}")
        if resp2.status_code in (200, 206):
            chunk = next(resp2.iter_content(1024))
            print(f"Got {len(chunk)} bytes")
        else:
            print(f"  Error: {resp2.text[:200]}")
    else:
        print("ERROR: No credentials found!")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Done ===")
EOF
