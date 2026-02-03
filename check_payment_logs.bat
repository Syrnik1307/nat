@echo off
ssh tp "cd /var/www/teaching_panel && grep -i 'admin.*payment.*notification\|notify_admin_payment\|T-Bank notification\|WEBHOOK.*Payment' logs/gunicorn.log 2>/dev/null | tail -50"
