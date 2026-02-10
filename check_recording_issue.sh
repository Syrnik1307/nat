#!/bin/bash
echo "=== PROCESSES ==="
ps aux | grep -E 'gunicorn|celery|redis-server|python' | grep -v grep
echo ""
echo "=== SYSTEMD SERVICES ==="
sudo systemctl list-units --type=service --state=running | grep -iE 'celery|teaching|panel|gunicorn|redis'
echo ""
echo "=== RECORDING STATS ==="
cd /var/www/teaching_panel
sudo -u www-data /var/www/venv/bin/python manage.py shell -c "
from schedule.models import LessonRecording
recs = LessonRecording.objects.all()
print('Total recordings:', recs.count())
print('Ready:', recs.filter(status='ready').count())
print('Processing:', recs.filter(status='processing').count())
ready = recs.filter(status='ready')
no_gdrive = ready.filter(gdrive_file_id='')
print('Ready without gdrive_file_id:', no_gdrive.count())
print('Ready with gdrive_file_id:', ready.exclude(gdrive_file_id='').count())
# Show last 5 recordings
for r in recs.order_by('-created_at')[:5]:
    print(f'  ID={r.id} status={r.status} gdrive={bool(r.gdrive_file_id)} play_url={bool(r.play_url)} storage={r.storage_provider} title={r.title[:40]}')
"
echo ""
echo "=== DONE ==="
