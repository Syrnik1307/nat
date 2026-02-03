@echo off
ssh tp "ls -la /var/www/teaching_panel/logs/ 2>/dev/null; ls -la /var/log/gunicorn* 2>/dev/null; find /var/www/teaching_panel -name '*.log' -type f 2>/dev/null | head -10"
