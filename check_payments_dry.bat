@echo off
ssh tp "cd /var/www/teaching_panel/teaching_panel && . ../venv/bin/activate && python manage.py mark_old_payments_notified --dry-run"
