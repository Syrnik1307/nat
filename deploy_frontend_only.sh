#!/bin/bash
# Deploy frontend build to production
cd /var/www/teaching_panel/frontend
rm -rf build_old
mv build build_old
mv build_new build

# CRITICAL: Fix permissions to prevent 403 Forbidden errors
chown -R www-data:www-data build
chmod -R 755 build

sudo systemctl restart teaching_panel
echo "=== Deploy done ==="
ls -la build/index.html
systemctl is-active teaching_panel
