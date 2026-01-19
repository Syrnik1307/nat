#!/bin/bash
cd /var/www/teaching_panel/teaching_panel
source ../venv/bin/activate
python manage.py shell < /tmp/check_active_lessons.py
