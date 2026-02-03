#!/bin/bash
# Добавляем заголовок upgrade-insecure-requests в nginx
# Это заставит браузер автоматически апгрейдить HTTP → HTTPS

NGINX_CONF="/etc/nginx/sites-enabled/lectiospace.ru"

echo "=== Текущие security headers ==="
grep -E 'add_header|upgrade-insecure' "$NGINX_CONF"

echo ""
echo "=== Проверяем наличие upgrade-insecure-requests ==="
if grep -q 'upgrade-insecure-requests' "$NGINX_CONF"; then
    echo "Заголовок уже есть"
else
    echo "Добавляем Content-Security-Policy: upgrade-insecure-requests"
    # Backup
    cp "$NGINX_CONF" "${NGINX_CONF}.bak.$(date +%s)"
    
    # Добавляем после Strict-Transport-Security
    sed -i '/Strict-Transport-Security/a\    add_header Content-Security-Policy "upgrade-insecure-requests" always;' "$NGINX_CONF"
    echo "Добавлено!"
fi

echo ""
echo "=== Проверяем синтаксис nginx ==="
nginx -t

echo ""
echo "=== Перезагружаем nginx ==="
systemctl reload nginx

echo ""
echo "=== Проверяем заголовки ==="
curl -sI https://lectiospace.ru/ 2>&1 | grep -iE 'security|policy'

echo ""
echo "=== Готово! Пожалуйста обновите страницу (Ctrl+F5) ==="
