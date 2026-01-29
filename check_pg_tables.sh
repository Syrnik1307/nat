#!/bin/bash
cd /var/www/teaching_panel/teaching_panel
source ../venv/bin/activate
python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute(\"\"\"
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name LIKE 'homework%'
        ORDER BY table_name;
    \"\"\")
    for row in cursor.fetchall():
        print(row[0])
"
