import os, sys
os.environ["DJANGO_SETTINGS_MODULE"] = "teaching_panel.settings"
sys.path.insert(0, "/var/www/teaching_panel")

import django
django.setup()

from schedule.models import LessonRecording

recs = LessonRecording.objects.all()
print(f"TOTAL: {recs.count()}")
print(f"READY: {recs.filter(status='ready').count()}")
print(f"PROCESSING: {recs.filter(status='processing').count()}")

ready = recs.filter(status='ready')
no_gdrive = ready.filter(gdrive_file_id='')
print(f"READY_NO_GDRIVE: {no_gdrive.count()}")
print(f"READY_WITH_GDRIVE: {ready.exclude(gdrive_file_id='').count()}")

print("\nLAST 5 RECORDINGS:")
for r in recs.order_by('-created_at')[:5]:
    gd = r.gdrive_file_id or 'NONE'
    pu = (r.play_url[:60] if r.play_url else 'NONE')
    print(f"  ID={r.id} STATUS={r.status} GDRIVE={gd} PLAY={pu} STORAGE={r.storage_provider} TITLE={r.title[:40]}")

# Check the specific recording (ПП) with 115.37 MB
pp_recs = recs.filter(title__startswith='ПП')
if pp_recs.exists():
    print("\nПП RECORDING:")
    for r in pp_recs:
        print(f"  ID={r.id} STATUS={r.status} GDRIVE={r.gdrive_file_id or 'NONE'} PLAY={r.play_url or 'NONE'} DOWNLOAD={r.download_url or 'NONE'} STORAGE={r.storage_provider}")
