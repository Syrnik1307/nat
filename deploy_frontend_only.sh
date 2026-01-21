#!/bin/bash
# Deploy frontend build to production
cd /var/www/teaching_panel/frontend
rm -rf build_old
mv build build_old
mv build_new build
sudo systemctl restart teaching_panel
echo "=== Deploy done ==="
ls -la build/index.html
systemctl is-active teaching_panel
