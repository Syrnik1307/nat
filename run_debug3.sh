#!/bin/bash
cd /var/www/teaching_panel/teaching_panel
source ../venv/bin/activate
python manage.py shell < /tmp/debug_prod2.py > /tmp/debug_result2.txt 2>&1
echo "DONE" >> /tmp/debug_result2.txt
