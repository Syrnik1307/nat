@echo off
ssh tp "cd /var/www/teaching_panel/teaching_panel && . ../venv/bin/activate && python -c \"
import django
django.setup()
from django.db.migrations.recorder import MigrationRecorder
migs = MigrationRecorder.Migration.objects.filter(app='accounts').order_by('-applied')[:10]
for m in migs:
    print(f'{m.name:40} | {m.applied}')
\""
