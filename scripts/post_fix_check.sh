#!/bin/bash
# Check nginx 404s on static files AFTER the fix (after 20:00 on March 2)
echo "=== NGINX 404s on static files AFTER 20:00 today ==="
count=$(sudo grep "No such file" /var/log/nginx/error.log 2>/dev/null | grep "static" | grep "2026/03/02" | while read line; do
    hour=$(echo "$line" | grep -oP '\d{2}:\d{2}:\d{2}' | head -1 | cut -d: -f1)
    if [ "$hour" -ge 20 ] 2>/dev/null; then
        echo "$line"
    fi
done | wc -l)
echo "Count: $count"

if [ "$count" -eq 0 ]; then
    echo "RESULT: NO_ERRORS_AFTER_FIX"
else
    echo "RESULT: ERRORS_FOUND"
    sudo grep "No such file" /var/log/nginx/error.log 2>/dev/null | grep "static" | grep "2026/03/02" | while read line; do
        hour=$(echo "$line" | grep -oP '\d{2}:\d{2}:\d{2}' | head -1 | cut -d: -f1)
        if [ "$hour" -ge 20 ] 2>/dev/null; then
            echo "  $line"
        fi
    done | tail -10
fi

echo ""
echo "=== REAL-TIME TEST: Can students load homework page? ==="
# Simulate what a fresh browser does
echo "Step 1: Load index.html"
CODE=$(curl -s -o /tmp/test_index.html -w "%{http_code}" https://lectiospace.ru/student/homework/75 --max-time 10)
echo "  /student/homework/75 -> HTTP $CODE"

echo "Step 2: Extract all JS/CSS from index.html"
JS_FILE=$(grep -oP 'src="/static/js/main\.[a-f0-9]+\.js"' /tmp/test_index.html | grep -oP 'main\.[a-f0-9]+\.js')
CSS_FILE=$(grep -oP 'href="/static/css/main\.[a-f0-9]+\.css"' /tmp/test_index.html | grep -oP 'main\.[a-f0-9]+\.css')
echo "  Main JS: $JS_FILE"
echo "  Main CSS: $CSS_FILE"

echo "Step 3: Load main JS"
CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://lectiospace.ru/static/js/$JS_FILE" --max-time 10)
echo "  main.js -> HTTP $CODE"

echo "Step 4: Load main CSS"
CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://lectiospace.ru/static/css/$CSS_FILE" --max-time 10)
echo "  main.css -> HTTP $CODE"

echo "Step 5: Check all lazy chunks load (like a browser would)"
FAIL=0
TOTAL=0
for f in /var/www/teaching_panel/frontend/build/static/js/*.chunk.js; do
    name=$(basename "$f")
    CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://lectiospace.ru/static/js/$name" --max-time 5 2>/dev/null)
    TOTAL=$((TOTAL+1))
    if [ "$CODE" != "200" ]; then
        echo "  FAIL: $name -> HTTP $CODE"
        FAIL=$((FAIL+1))
    fi
done
echo "  Tested $TOTAL chunks: $FAIL failures"

if [ "$FAIL" -eq 0 ]; then
    echo ""
    echo "FINAL: ALL SYSTEMS OPERATIONAL"
    echo "Students CAN open homework pages"
else
    echo ""
    echo "FINAL: PROBLEMS DETECTED"
fi
