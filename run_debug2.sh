#!/bin/bash
cd /var/www/teaching_panel/teaching_panel
source ../venv/bin/activate
python manage.py shell < /tmp/debug_prod.py > /tmp/debug_result.txt 2>&1
echo "SCRIPT DONE" >> /tmp/debug_result.txt
