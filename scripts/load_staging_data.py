#!/usr/bin/env python
"""Load prod dump into staging DB with all signals disabled.

Run from the Django project directory (where manage.py lives):
  cd /var/www/teaching-panel-stage/teaching_panel
  source ../venv/bin/activate
  python /tmp/load_staging.py /tmp/prod_dump2.json
"""
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "teaching_panel.settings_staging")

# Ensure cwd is in Python path (needed for nohup/background execution)
cwd = os.getcwd()
if cwd not in sys.path:
    sys.path.insert(0, cwd)

import django
django.setup()

from django.db.models.signals import post_save, m2m_changed, pre_save

# Disconnect ALL signals to prevent auto-creates (NotificationSettings, Wallets, etc.)
for sig in [post_save, m2m_changed, pre_save]:
    sig.receivers = []

from django.core.management import call_command

dump_file = sys.argv[1] if len(sys.argv) > 1 else "/tmp/prod_dump2.json"
print(f"Loading {dump_file}...")

try:
    call_command("loaddata", dump_file, verbosity=1)
    print("LOAD_OK")
except Exception as e:
    print(f"LOAD_FAIL: {e}")
    sys.exit(1)
