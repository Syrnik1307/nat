@echo off
ssh tp "journalctl -u gunicorn --since '24 hours ago' 2>/dev/null | grep -i 'payment\|webhook\|notify' | tail -100"
