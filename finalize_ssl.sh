#!/bin/bash
# 🔐 Финализация SSL для lectiospace.ru
# Запусти после изменения DNS записей!

echo "🔍 Проверяю DNS..."
DNS_IP=$(dig +short lectiospace.ru)

if [ "$DNS_IP" = "72.56.81.163" ]; then
    echo "✅ DNS настроен правильно: $DNS_IP"
    
    echo "🔐 Получаю SSL сертификат..."
    systemctl stop nginx
    certbot certonly --standalone -d lectiospace.ru -d www.lectiospace.ru --non-interactive --agree-tos --email admin@lectiospace.ru
    
    if [ -f /etc/letsencrypt/live/lectiospace.ru/fullchain.pem ]; then
        echo "✅ SSL сертификат получен!"
        
        # Обновляю Nginx на HTTPS
        cat > /etc/nginx/sites-available/lectiospace.ru << 'NGINXEOF'
upstream django {
    server 127.0.0.1:8000;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name lectiospace.ru www.lectiospace.ru;
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name lectiospace.ru www.lectiospace.ru;

    ssl_certificate /etc/letsencrypt/live/lectiospace.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/lectiospace.ru/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;

    client_max_body_size 500M;

    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/json application/javascript;

    location /static/ {
        alias /var/www/teaching_panel/teaching_panel/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /var/www/teaching_panel/teaching_panel/media/;
        expires 7d;
    }

    location / {
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_read_timeout 300s;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
NGINXEOF
        
        nginx -t && systemctl start nginx
        echo ""
        echo "=========================================="
        echo "✅ МИГРАЦИЯ ЗАВЕРШЕНА!"
        echo "=========================================="
        echo "🌍 Сайт доступен: https://lectiospace.ru"
        echo ""
    else
        echo "❌ Ошибка получения SSL!"
        systemctl start nginx
    fi
else
    echo "❌ DNS ещё не обновился!"
    echo "   Текущий IP: $DNS_IP"
    echo "   Нужный IP: 72.56.81.163"
    echo ""
    echo "Подожди 5-30 минут и запусти скрипт снова."
fi
