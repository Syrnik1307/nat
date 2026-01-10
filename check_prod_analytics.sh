#!/bin/bash
echo "=== Checking NavBar.js for analytics link ==="
grep -n "analytics\|Аналитика" /var/www/teaching_panel/frontend/src/components/NavBar.js || echo "NOT_FOUND_IN_NAVBAR"

echo ""
echo "=== Checking App.js for analytics route ==="
grep -n "analytics\|AnalyticsPage" /var/www/teaching_panel/frontend/src/App.js || echo "NOT_FOUND_IN_APP"

echo ""
echo "=== Checking if AnalyticsPage.js exists ==="
ls -la /var/www/teaching_panel/frontend/src/components/AnalyticsPage.js 2>/dev/null || echo "FILE_NOT_EXISTS"

echo ""
echo "=== Checking GroupDetailModal for summary tab ==="
grep -n "analytics-summary\|Сводная" /var/www/teaching_panel/frontend/src/components/GroupDetailModal.js || echo "NOT_FOUND_IN_MODAL"

echo ""
echo "=== Git log last 3 commits ==="
cd /var/www/teaching_panel && git log --oneline -3
