@echo off
ssh tp "cat /var/log/nginx/access.log 2>/dev/null | grep -E 'webhook|payment' | grep '02/Feb/2026:12:4' | head -30"
