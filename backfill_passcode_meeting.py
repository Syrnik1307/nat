#!/usr/bin/env python
"""Append passcode to play/download URLs for a given meeting."""
import os
import sys
import django
from datetime import datetime
import requests

MEETING_ID = '83743093059'

sys.path.insert(0, '/var/www/teaching_panel/teaching_panel')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from schedule.zoom_client import my_zoom_api_client
from schedule.models import LessonRecording


def apply_pwd(url: str, pwd: str):
    if not url or not pwd:
        return url
    if 'pwd=' in url:
        return url
    sep = '&' if '?' in url else '?'
    return f"{url}{sep}pwd={pwd}"


def main():
    access_token = my_zoom_api_client._get_access_token()
    url = f'https://api.zoom.us/v2/meetings/{MEETING_ID}/recordings'
    r = requests.get(url, headers={'Authorization': f'Bearer {access_token}'}, timeout=20)
    r.raise_for_status()
    data = r.json()

    pwd = data.get('recording_play_passcode') or data.get('password')
    if not pwd:
        print('No passcode returned from Zoom')
        return

    updated = 0
    for f in data.get('recording_files', []):
        rec_id = f.get('id')
        try:
            lr = LessonRecording.objects.get(zoom_recording_id=rec_id)
        except LessonRecording.DoesNotExist:
            continue
        new_play = apply_pwd(lr.play_url, pwd)
        new_download = apply_pwd(lr.download_url, pwd)
        if new_play != lr.play_url or new_download != lr.download_url:
            lr.play_url = new_play
            lr.download_url = new_download
            lr.save(update_fields=['play_url', 'download_url'])
            updated += 1
            print(f"Updated {lr.id} with passcode")

    print(f"Done. Updated {updated} recordings")


if __name__ == '__main__':
    main()
