#!/usr/bin/env python
import os, sys, django
sys.path.insert(0, '/var/www/teaching_panel/teaching_panel')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from schedule.models import LessonRecording

PASS = 'DH6J-H_Ug0fxfa-sowAAIAAAAH8SnNMGZRTGPn2JAUwRqiiCtUHR3yLDzblEQQg6aiWA3WAu2hfzfuTTmSsuQnai0zAwMDAwNA'

def apply_pwd(url):
    if not url or not PASS:
        return url
    if 'pwd=' in url:
        return url
    sep = '&' if '?' in url else '?'
    return f"{url}{sep}pwd={PASS}"

updated = 0
for lr in LessonRecording.objects.filter(lesson_id=17):
    new_play = apply_pwd(lr.play_url)
    new_dl = apply_pwd(lr.download_url)
    if new_play != lr.play_url or new_dl != lr.download_url:
        lr.play_url = new_play
        lr.download_url = new_dl
        lr.save(update_fields=['play_url', 'download_url'])
        updated += 1
        print(f'Updated {lr.id}')

print('Done. Updated', updated)
