#!/bin/bash
echo "=== API Health Check ==="
for ep in health courses course-modules course-lessons homework submissions groups; do
    code=$(curl -s -m5 -H 'X-Forwarded-Proto: https' -o /dev/null -w '%{http_code}' "http://127.0.0.1:8000/api/$ep/")
    echo "$ep: HTTP $code"
done
echo "=== Last errors ==="
tail -5 /var/log/teaching_panel/error.log | grep -iE 'error|exception|fail|kill' || echo 'No errors'
echo "=== Memory ==="
free -m | head -2
