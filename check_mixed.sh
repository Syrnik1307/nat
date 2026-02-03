#!/bin/bash
# Проверка mixed content на lectiospace.ru

echo "=== Проверка HTTP ссылок в React build ==="
grep -roh 'http://[^"'"'"' ]*' /var/www/react-app/static/ 2>/dev/null | grep -v 'www.w3.org' | sort -u

echo ""
echo "=== Проверка HTTP в index.html ==="
grep -i 'http://' /var/www/react-app/index.html 2>/dev/null

echo ""
echo "=== Проверка API ответов на HTTP ссылки ==="
curl -s https://lectiospace.ru/api/ 2>/dev/null | grep -o 'http://[^"]*' | head -5

echo ""
echo "=== Nginx proxy_pass ==="
grep -r 'proxy_pass' /etc/nginx/sites-enabled/ 2>/dev/null

echo ""
echo "=== Done ==="
