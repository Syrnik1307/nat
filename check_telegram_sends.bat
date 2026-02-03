@echo off
ssh tp "grep -r 'sendMessage\|payment' /var/log/nginx/access.log 2>/dev/null | grep '02/Feb/2026:12:4' | head -20"
