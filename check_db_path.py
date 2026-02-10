#!/usr/bin/env python3
"""Check actual DB path Django uses."""
import os, sys
sys.path.insert(0, '/var/www/teaching_panel/teaching_panel')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')

import django
django.setup()

from django.conf import settings
db_config = settings.DATABASES['default']
print(f"DB ENGINE: {db_config['ENGINE']}")
print(f"DB NAME: {db_config.get('NAME', 'N/A')}")

# Check actual file
db_path = db_config.get('NAME', '')
if db_path and os.path.exists(db_path):
    print(f"DB file exists: {db_path}")
    print(f"DB file size: {os.path.getsize(db_path)} bytes")
else:
    print(f"DB file NOT FOUND at: {db_path}")
