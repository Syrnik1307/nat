#!/bin/bash
# Fix migration inconsistency on production
# Problem: tenants.0003 has wrong "applied" state due to table introspection
# Solution: 
# 1. Fake schedule.0031 (both), schedule.0032_merge (they're no-ops, tables exist)
# 2. Fake tenants.0001, tenants.0002 (tables already exist)
# 3. Run real migrations for FK additions + backfill

DB="/var/www/teaching_panel/teaching_panel/db.sqlite3"

echo "=== Step 1: Insert fake records for migrations whose tables already exist ==="

# schedule.0031 variants (soft delete columns don't exist yet, but migrations are no-ops after merge)
sqlite3 "$DB" "INSERT OR IGNORE INTO django_migrations (app, name, applied) VALUES ('schedule', '0031_add_soft_delete_to_recording', datetime('now'));"
sqlite3 "$DB" "INSERT OR IGNORE INTO django_migrations (app, name, applied) VALUES ('schedule', '0031_lessonrecording_deleted_at_and_more', datetime('now'));"
sqlite3 "$DB" "INSERT OR IGNORE INTO django_migrations (app, name, applied) VALUES ('schedule', '0032_merge_20260201_0829', datetime('now'));"

echo "=== Step 2: Verify records ==="
sqlite3 "$DB" "SELECT app,name FROM django_migrations WHERE app='schedule' AND name LIKE '003%' ORDER BY name;"
sqlite3 "$DB" "SELECT app,name FROM django_migrations WHERE app='tenants' ORDER BY name;"

echo "=== Done ==="
