#!/bin/bash
DB="/var/www/teaching_panel/teaching_panel/db.sqlite3"

echo "=== Step 1: WAL checkpoint ==="
sqlite3 "$DB" "PRAGMA wal_checkpoint(TRUNCATE);"

echo "=== Step 2: Delete any tenants.0003 ==="
sqlite3 "$DB" "DELETE FROM django_migrations WHERE app='tenants' AND name='0003_backfill_school_fk';"

echo "=== Step 3: Verify deletion ==="
sqlite3 "$DB" "SELECT id,app,name FROM django_migrations WHERE app='tenants';"

echo "=== Step 4: WAL checkpoint again ==="
sqlite3 "$DB" "PRAGMA wal_checkpoint(TRUNCATE);"

echo "=== Step 5: Count tenants ==="
sqlite3 "$DB" "SELECT COUNT(*) FROM django_migrations WHERE app='tenants';"

echo "=== Step 6: Try migrate with fake for tenants base ==="
cd /var/www/teaching_panel
sudo -u www-data venv/bin/python teaching_panel/manage.py migrate tenants 0002 --fake 2>&1 | tail -5

echo "=== Step 7: Check tenants status ==="
sqlite3 "$DB" "SELECT id,app,name FROM django_migrations WHERE app='tenants';"

echo "=== Step 8: Run all migrations ==="
sudo -u www-data venv/bin/python teaching_panel/manage.py migrate 2>&1 | tail -20

echo "=== Done ==="
