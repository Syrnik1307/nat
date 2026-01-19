#!/bin/bash
cd /var/www/teaching_panel/teaching_panel
source ../venv/bin/activate
python manage.py shell < /tmp/requeue_zoom_recordings.py > /tmp/requeue_out.txt 2>&1
