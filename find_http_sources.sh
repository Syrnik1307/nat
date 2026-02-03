#!/bin/bash
# Проверяем HTTP ссылки на странице auth-new
echo "=== Проверяем HTML страницы ==="
curl -s https://lectiospace.ru/auth-new 2>&1 | grep -ioE 'http://[^"'"'"' ><]+' | grep -v 'w3.org' | sort -u

echo ""
echo "=== Проверяем JS бандлы ==="
for js in /var/www/teaching_panel/frontend/build/static/js/main.*.js; do
    if [ -f "$js" ]; then
        echo "Checking: $js"
        grep -oE 'http://[^"'"'"' ]+' "$js" 2>/dev/null | grep -v 'w3.org\|localhost\|127.0.0.1' | sort -u | head -10
    fi
done

echo ""
echo "=== Проверяем manifest.json ==="
cat /var/www/teaching_panel/frontend/build/manifest.json 2>/dev/null | grep -i 'http://'

echo ""
echo "=== Done ==="
