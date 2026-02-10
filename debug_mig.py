#!/usr/bin/env python3
"""
Debug: check what MigrationRecorder.applied_migrations() returns for tenants.
"""
import os, sys
sys.path.insert(0, '/var/www/teaching_panel/teaching_panel')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')

import django
django.setup()

from django.db import connection
from django.db.migrations.recorder import MigrationRecorder

recorder = MigrationRecorder(connection)
applied = recorder.applied_migrations()

tenant_applied = {k: v for k, v in applied.items() if k[0] == 'tenants'}
print(f"Tenants applied migrations: {len(tenant_applied)}")
for k in sorted(tenant_applied.keys()):
    print(f"  {k}")

# Also check raw SQL
with connection.cursor() as cursor:
    cursor.execute("SELECT app, name FROM django_migrations WHERE app='tenants'")
    rows = cursor.fetchall()
    print(f"\nRaw SQL tenants records: {len(rows)}")
    for r in rows:
        print(f"  {r}")
