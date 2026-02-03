@echo off
ssh tp "sudo journalctl -u gunicorn --since '7 days ago' 2>/dev/null | grep -iE 'Admin payment notification|notify_admin_payment|payment.*sent' | tail -30"
