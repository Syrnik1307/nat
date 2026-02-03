@echo off
ssh tp "cat /var/log/nginx/access.log 2>/dev/null | grep -iE '/api/payments' | tail -30"
