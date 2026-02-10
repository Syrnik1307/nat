#!/usr/bin/env python3
"""
Fix: delete tenants.0003 from django_migrations in POSTGRES on production.
"""
import os, sys
sys.path.insert(0, '/var/www/teaching_panel/teaching_panel')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')

import django
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    # Check current state
    cursor.execute("SELECT id, app, name FROM django_migrations WHERE app='tenants' ORDER BY id")
    rows = cursor.fetchall()
    print(f"Before: {len(rows)} tenants records:")
    for r in rows:
        print(f"  id={r[0]}, name={r[2]}")

    # Delete tenants.0003
    cursor.execute("DELETE FROM django_migrations WHERE app='tenants' AND name='0003_backfill_school_fk'")
    deleted = cursor.rowcount
    print(f"\nDeleted {deleted} record(s)")

    # Verify
    cursor.execute("SELECT id, app, name FROM django_migrations WHERE app='tenants' ORDER BY id")
    rows = cursor.fetchall()
    print(f"\nAfter: {len(rows)} tenants records:")
    for r in rows:
        print(f"  id={r[0]}, name={r[2]}")

print("\nDone! Now run: sudo -u www-data venv/bin/python teaching_panel/manage.py migrate")
