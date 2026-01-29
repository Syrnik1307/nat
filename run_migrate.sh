#!/bin/bash
cd /var/www/teaching_panel/teaching_panel
source ../venv/bin/activate
python manage.py migrate homework 2>&1
echo "=== Checking tables after migration ==="
sqlite3 db.sqlite3 "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'homework%' ORDER BY name;"
