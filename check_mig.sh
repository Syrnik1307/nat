#!/bin/bash
DB="/var/www/teaching_panel/teaching_panel/db.sqlite3"

echo "=== All tenants records ==="
sqlite3 "$DB" "SELECT id,app,name FROM django_migrations WHERE app='tenants';"

echo "=== Count ==="
sqlite3 "$DB" "SELECT COUNT(*) as cnt FROM django_migrations WHERE app='tenants';"

echo "=== Check if 0003 exists literally ==="
sqlite3 "$DB" "SELECT id,app,name FROM django_migrations WHERE name LIKE '%backfill%';"

echo "=== Last 5 records total ==="
sqlite3 "$DB" "SELECT id,app,name FROM django_migrations ORDER BY id DESC LIMIT 5;"
