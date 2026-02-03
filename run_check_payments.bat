@echo off
scp C:\Users\User\Desktop\nat\check_payments_remote.py tp:/tmp/check_payments.py
ssh tp "cd /var/www/teaching_panel/teaching_panel && . ../venv/bin/activate && python /tmp/check_payments.py"
