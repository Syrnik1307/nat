cd /var/www/teaching_panel/teaching_panel
../venv/bin/python manage.py shell -c "from schedule.models import LessonRecording; qs=LessonRecording.objects.filter(title__icontains='прототип'); print('count', qs.count()); [print(r.id, r.title, r.created_at, r.status, r.duration, r.file_size, r.gdrive_file_id, r.zoom_recording_id, r.archive_key, r.updated_at) for r in qs]"
