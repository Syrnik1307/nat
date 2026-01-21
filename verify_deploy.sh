#!/bin/bash
echo "=== DEPLOY VERIFICATION ==="
echo "Frontend build:"
ls -la /var/www/teaching_panel/frontend/build/index.html
echo ""
echo "Service status:"
systemctl is-active teaching_panel
echo ""
echo "Latest commit:"
git -C /var/www/teaching_panel log --oneline -1
echo ""
echo "=== DONE ==="
