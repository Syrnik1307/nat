#!/usr/bin/env python3
"""
Fix migration inconsistency: remove tenants.0003 from django_migrations.
Run as: sudo -u www-data /var/www/teaching_panel/venv/bin/python /tmp/fix_mig.py
"""
import sqlite3
import os

DB = '/var/www/teaching_panel/teaching_panel/db.sqlite3'

conn = sqlite3.connect(DB)
c = conn.cursor()

# Show all tenants records
c.execute("SELECT id, app, name FROM django_migrations WHERE app='tenants'")
rows = c.fetchall()
print(f"Found {len(rows)} tenants records:")
for r in rows:
    print(f"  id={r[0]}, app={r[1]}, name={r[2]}")

# Delete tenants.0003
c.execute("DELETE FROM django_migrations WHERE app='tenants' AND name='0003_backfill_school_fk'")
deleted = c.rowcount
print(f"\nDeleted {deleted} record(s) for tenants.0003_backfill_school_fk")

conn.commit()

# Verify
c.execute("SELECT COUNT(*) FROM django_migrations WHERE app='tenants'")
count = c.fetchone()[0]
print(f"Remaining tenants records: {count}")

# Also verify no other backfill records
c.execute("SELECT id, app, name FROM django_migrations WHERE name LIKE '%backfill%'")
rows = c.fetchall()
print(f"Records with 'backfill': {len(rows)}")
for r in rows:
    print(f"  id={r[0]}, app={r[1]}, name={r[2]}")

conn.close()
print("\nDone. Now run: sudo -u www-data venv/bin/python teaching_panel/manage.py migrate")
