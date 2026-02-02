#!/bin/bash
# Emergency diagnostic script

echo "=== GUNICORN HEALTH CHECK ==="
curl -s -m 5 http://127.0.0.1:8000/api/health/ && echo "" || echo "TIMEOUT/ERROR"

echo ""
echo "=== STRACE GUNICORN (2 sec) ==="
PID=$(pgrep -f "gunicorn.*wsgi" | head -1)
if [ -n "$PID" ]; then
    timeout 2 strace -p $PID 2>&1 | head -20
else
    echo "Gunicorn PID not found"
fi

echo ""
echo "=== GUNICORN THREADS ==="
ps -eLf | grep gunicorn | grep -v grep | head -20

echo ""
echo "=== OPEN FILES BY GUNICORN ==="
lsof -c gunicorn 2>/dev/null | wc -l

echo ""
echo "=== NETWORK CONNECTIONS ==="
ss -tlnp | grep 8000

echo ""
echo "=== DMESG OOM CHECK ==="
dmesg | grep -i "oom\|kill" | tail -5
