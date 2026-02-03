#!/bin/bash
# Исправление mixed content для lectiospace.ru

set -e

echo "=== Текущая конфигурация nginx ==="
NGINX_CONF="/etc/nginx/sites-available/lectiospace.ru"
if [ ! -f "$NGINX_CONF" ]; then
    # Поиск правильного конфига
    NGINX_CONF=$(ls /etc/nginx/sites-available/ | grep -i lectio | head -1)
    if [ -n "$NGINX_CONF" ]; then
        NGINX_CONF="/etc/nginx/sites-available/$NGINX_CONF"
    else
        echo "Конфиг lectiospace не найден!"
        ls -la /etc/nginx/sites-available/
        exit 1
    fi
fi
echo "Используем: $NGINX_CONF"

echo ""
echo "=== Проверяем X-Forwarded-Proto ==="
if grep -q 'X-Forwarded-Proto' "$NGINX_CONF"; then
    echo "X-Forwarded-Proto уже есть в конфиге"
    grep 'X-Forwarded-Proto' "$NGINX_CONF"
else
    echo "ВНИМАНИЕ: X-Forwarded-Proto отсутствует! Добавляем..."
    # Backup
    cp "$NGINX_CONF" "${NGINX_CONF}.bak.$(date +%s)"
    # Добавляем заголовок после proxy_set_header Host
    sed -i '/proxy_set_header Host/a\        proxy_set_header X-Forwarded-Proto $scheme;' "$NGINX_CONF"
    echo "Добавлено!"
fi

echo ""
echo "=== Проверяем все location с proxy_pass ==="
grep -A5 'proxy_pass' "$NGINX_CONF" | head -30

echo ""
echo "=== Тестируем nginx конфигурацию ==="
nginx -t

echo ""
echo "=== Перезагружаем nginx ==="
systemctl reload nginx

echo ""
echo "=== Проверяем что сервис работает ==="
systemctl status nginx --no-pager | head -10

echo ""
echo "=== Проверяем SSL и заголовки ==="
curl -sI https://lectiospace.ru/api/ 2>&1 | head -15

echo ""
echo "=== Готово! ==="
