#!/bin/bash
echo "=== Schedule migrations ==="
sqlite3 /var/www/teaching_panel/teaching_panel/db.sqlite3 "SELECT name FROM django_migrations WHERE app='schedule' ORDER BY id;"

echo ""
echo "=== Tenants migrations ==="
sqlite3 /var/www/teaching_panel/teaching_panel/db.sqlite3 "SELECT name FROM django_migrations WHERE app='tenants' ORDER BY id;"

echo ""
echo "=== LessonRecording has deleted_at? ==="
sqlite3 /var/www/teaching_panel/teaching_panel/db.sqlite3 "PRAGMA table_info(schedule_lessonrecording);" | grep -i "deleted"

echo ""
echo "=== Group has school_id? ==="
sqlite3 /var/www/teaching_panel/teaching_panel/db.sqlite3 "PRAGMA table_info(schedule_group);" | grep -i "school"

echo ""
echo "=== Schedule migration files on disk ==="
ls /var/www/teaching_panel/teaching_panel/schedule/migrations/003*.py 2>/dev/null

echo ""
echo "=== Tenants migration files on disk ==="
ls /var/www/teaching_panel/teaching_panel/tenants/migrations/0*.py 2>/dev/null

echo ""
echo "=== Current git commit ==="
cd /var/www/teaching_panel && git log --oneline -1

echo ""
echo "=== Service status ==="
systemctl is-active teaching_panel
