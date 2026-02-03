@echo off
ssh tp "cat /var/log/nginx/access.log 2>/dev/null | grep -E 'tbank.*webhook|yookassa.*webhook|webhook.*payment|payment.*webhook' | grep '02/Feb' | tail -20"
