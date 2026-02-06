import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "teaching_panel.settings")
import django
django.setup()

from schedule.gdrive_utils import GDriveManager

print("Testing GDrive connection...")
try:
    gdrive = GDriveManager(teacher_id=76)
    files = gdrive.service.files().list(pageSize=3, fields="files(id, name)").execute()
    print(f"GDrive API works! Found {len(files.get('files', []))} files")
    for f in files.get('files', []):
        print(f"  - {f.get('name')}: {f.get('id')}")
except Exception as e:
    print(f"GDrive API error: {type(e).__name__}: {e}")
