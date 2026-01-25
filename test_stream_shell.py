import sys
import os
import logging
from schedule.models import LessonRecording
from schedule.gdrive_utils import get_gdrive_manager
from google.auth.transport.requests import AuthorizedSession

# Configure logging to console (stderr)
handler = logging.StreamHandler(sys.stderr)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(levelname)s %(message)s')
handler.setFormatter(formatter)
root_logger = logging.getLogger()
root_logger.addHandler(handler)
root_logger.setLevel(logging.INFO)

rec_id = 14
try:
    print("Fetching recording object...")
    rec = LessonRecording.objects.get(id=rec_id)
    print(f"Recording {rec_id} found. File ID: {rec.gdrive_file_id}")
    
    print("Initializing GDrive manager (this might hang)...")
    get_gdrive_manager.cache_clear() if hasattr(get_gdrive_manager, 'cache_clear') else None
    gdrive = get_gdrive_manager()
    print("GDrive manager initialized.")
    
    creds = getattr(getattr(gdrive.service, "_http", None), "credentials", None)
    if not creds:
        print("No creds found on service object.")
    else:
        print("Creating AuthorizedSession...")
        session = AuthorizedSession(creds)
        drive_url = f"https://www.googleapis.com/drive/v3/files/{rec.gdrive_file_id}?alt=media"
        
        print(f"Starting request to {drive_url}...")
        # Timeout 10s to fail fast if it hangs
        resp = session.get(drive_url, stream=True, timeout=10)
        print(f"Response status: {resp.status_code}")
        print(f"Headers: {resp.headers}")
        
        chunk = next(resp.iter_content(chunk_size=1024))
        print(f"First chunk read: {len(chunk)} bytes")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
