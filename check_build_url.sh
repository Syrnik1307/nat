#!/bin/bash
# Ищем URL gdrive-stats в билде
cd /var/www/teaching_panel/frontend/build/static/js
echo "=== Searching for gdrive-stats URL pattern ==="
grep -oh '"[^"]*gdrive-stats[^"]*"' *.js | head -5

echo ""
echo "=== Searching for schedule/api ==="
grep -oh '"/schedule/api/[^"]*"' *.js | head -5

echo ""
echo "=== File modification time ==="
ls -la 182*.js | head -1
