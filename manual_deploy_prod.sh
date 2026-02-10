#!/bin/bash
# Manual Production Deploy: Homework Revision Feature

set -e

echo "=== PRODUCTION DEPLOY: Homework Revision ==="
cd /var/www/teaching_panel || exit 1

# 1. Backup
echo "[1/6] Backup DB..."
sudo cp teaching_panel/db.sqlite3 /tmp/manual_backup_$(date +%Y%m%d_%H%M%S).sqlite3
ls -lh /tmp/manual_backup_* | tail -1

# 2. Git pull
echo "[2/6] Git pull..."
sudo -u www-data git fetch origin
sudo -u www-data git reset --hard origin/main
echo "Current commit: $(git rev-parse --short HEAD)"

# 3. Check requirements (skip pip if unchanged)
echo "[3/6] Check requirements..."
sudo -u www-data ../venv/bin/pip list | grep -i django | head -3

# 4. Migrate
echo "[4/6] Migrate..."
cd teaching_panel
sudo -u www-data ../venv/bin/python manage.py migrate --noinput

# 5. Collectstatic
echo "[5/6] Collectstatic..."
sudo -u www-data ../venv/bin/python manage.py collectstatic --noinput 2>&1 | tail -3

# 6. Restart services
echo "[6/6] Restart..."
sudo systemctl restart teaching_panel nginx
sleep 3
systemctl is-active teaching_panel
systemctl is-active nginx

echo ""
echo "=== DEPLOY COMPLETE ==="
echo "Production commit: $(git rev-parse --short HEAD)"
echo "Service status: $(systemctl is-active teaching_panel)"
