#!/bin/bash
cd /var/www/teaching_panel/teaching_panel
source ../venv/bin/activate
python manage.py shell < /tmp/debug_student_window.py > /tmp/student_window_out.txt 2>&1
