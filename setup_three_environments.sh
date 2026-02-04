#!/bin/bash
# Настройка ТРЁХ окружений на одном сервере
# Запускать на СЕРВЕРЕ от root

set -e

echo "🏗️ Setting up THREE environments"
echo "1. lectiospace.ru (PROD Russia)"
echo "2. stage.lectiospace.ru (STAGING Russia)"
echo "3. lectiospace.online (PROD Africa)"
echo "=================================================="

# ============================================
# 1. STAGING RUSSIA (stage.lectiospace.ru)
# ============================================
echo ""
echo "🧪 Setting up STAGING RUSSIA (stage.lectiospace.ru)..."

mkdir -p /var/www/teaching-panel-stage-ru
cd /var/www/teaching-panel-stage-ru

# Клонируем репозиторий
if [ ! -d ".git" ]; then
    git clone https://github.com/YOUR_USERNAME/teaching-panel.git .
else
    git pull origin staging-russia
fi

git checkout -b staging-russia || git checkout staging-russia

# Python venv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# .env для staging Russia
cat > .env << 'EOF'
# STAGING RUSSIA - точная копия настроек прода для тестирования
DJANGO_SETTINGS_MODULE=teaching_panel.settings_staging_russia
SECRET_KEY=staging-ru-secret-$(openssl rand -base64 32)
DEBUG=True
ALLOWED_HOSTS=stage.lectiospace.ru

# Feature Flags - ТОЛЬКО российские (как в проде)
FEATURE_AFRICA_MARKET=False
FEATURE_PWA_OFFLINE=False
FEATURE_MOBILE_MONEY=False
FEATURE_SMS_NOTIFICATIONS=False
FEATURE_MULTILINGUAL=False

# Российские фичи
FEATURE_YOOKASSA_PAYMENTS=True
FEATURE_TELEGRAM_SUPPORT=True

# Payments - ТЕСТОВЫЕ ключи YooKassa
YOOKASSA_ACCOUNT_ID=test_account_ru
YOOKASSA_SECRET_KEY=test_secret_ru

# Валюта и язык
DEFAULT_CURRENCY=RUB
DEFAULT_LANGUAGE=ru
PAYMENT_PROVIDER=yookassa

FRONTEND_URL=https://stage.lectiospace.ru
EOF

# Миграции и статика
python teaching_panel/manage.py migrate
python teaching_panel/manage.py collectstatic --noinput

# Логи
mkdir -p logs
chown -R www-data:www-data /var/www/teaching-panel-stage-ru

# Systemd service
cat > /etc/systemd/system/teaching-panel-stage-ru.service << 'EOF'
[Unit]
Description=Teaching Panel Staging Russia
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/teaching-panel-stage-ru/teaching_panel
Environment="PATH=/var/www/teaching-panel-stage-ru/venv/bin"
Environment="DJANGO_SETTINGS_MODULE=teaching_panel.settings_staging_russia"
ExecStart=/var/www/teaching-panel-stage-ru/venv/bin/gunicorn \
    --workers 2 \
    --bind 127.0.0.1:8001 \
    --access-logfile /var/www/teaching-panel-stage-ru/logs/access.log \
    --error-logfile /var/www/teaching-panel-stage-ru/logs/error.log \
    teaching_panel.wsgi:application

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Nginx config
cat > /etc/nginx/sites-available/stage.lectiospace.ru << 'EOF'
server {
    listen 80;
    server_name stage.lectiospace.ru;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name stage.lectiospace.ru;

    ssl_certificate /etc/letsencrypt/live/stage.lectiospace.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/stage.lectiospace.ru/privkey.pem;

    root /var/www/teaching-panel-stage-ru/frontend/build;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /admin/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
    }

    location /static/ {
        alias /var/www/teaching-panel-stage-ru/teaching_panel/staticfiles/;
    }

    location /media/ {
        alias /var/www/teaching-panel-stage-ru/teaching_panel/media/;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }

    # Индикатор staging
    add_header X-Environment "STAGING-RUSSIA" always;
}
EOF

ln -sf /etc/nginx/sites-available/stage.lectiospace.ru /etc/nginx/sites-enabled/

# ============================================
# 2. PRODUCTION AFRICA (lectiospace.online)
# ============================================
echo ""
echo "🌍 Setting up PRODUCTION AFRICA (lectiospace.online)..."

mkdir -p /var/www/teaching-panel-africa
cd /var/www/teaching-panel-africa

if [ ! -d ".git" ]; then
    git clone https://github.com/YOUR_USERNAME/teaching-panel.git .
else
    git pull origin main-africa
fi

git checkout -b main-africa || git checkout main-africa

# Python venv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# .env для Africa
cat > .env << 'EOF'
# PRODUCTION AFRICA - все новые фичи
DJANGO_SETTINGS_MODULE=teaching_panel.settings_production_africa
SECRET_KEY=africa-prod-secret-$(openssl rand -base64 32)
DEBUG=False
ALLOWED_HOSTS=lectiospace.online,www.lectiospace.online

# Feature Flags - ВСЕ африканские фичи
FEATURE_AFRICA_MARKET=True
FEATURE_PWA_OFFLINE=True
FEATURE_MOBILE_MONEY=True
FEATURE_SMS_NOTIFICATIONS=True
FEATURE_MULTILINGUAL=True
FEATURE_ADAPTIVE_VIDEO=True

# Российские фичи выключены
FEATURE_YOOKASSA_PAYMENTS=False
FEATURE_TELEGRAM_SUPPORT=False

# Payments - Flutterwave для Африки
FLUTTERWAVE_PUBLIC_KEY=your_flutterwave_public_key
FLUTTERWAVE_SECRET_KEY=your_flutterwave_secret_key

# Валюта и язык
DEFAULT_CURRENCY=USD
DEFAULT_LANGUAGE=en
PAYMENT_PROVIDER=flutterwave

FRONTEND_URL=https://lectiospace.online

# Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
CSRF_TRUSTED_ORIGINS=https://lectiospace.online
EOF

# Миграции и статика
python teaching_panel/manage.py migrate
python teaching_panel/manage.py collectstatic --noinput

mkdir -p logs
chown -R www-data:www-data /var/www/teaching-panel-africa

# Systemd service
cat > /etc/systemd/system/teaching-panel-africa.service << 'EOF'
[Unit]
Description=Teaching Panel Production Africa
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/teaching-panel-africa/teaching_panel
Environment="PATH=/var/www/teaching-panel-africa/venv/bin"
Environment="DJANGO_SETTINGS_MODULE=teaching_panel.settings_production_africa"
ExecStart=/var/www/teaching-panel-africa/venv/bin/gunicorn \
    --workers 3 \
    --bind 127.0.0.1:8002 \
    --access-logfile /var/www/teaching-panel-africa/logs/access.log \
    --error-logfile /var/www/teaching-panel-africa/logs/error.log \
    teaching_panel.wsgi:application

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Nginx config
cat > /etc/nginx/sites-available/lectiospace.online << 'EOF'
server {
    listen 80;
    server_name lectiospace.online www.lectiospace.online;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name lectiospace.online www.lectiospace.online;

    ssl_certificate /etc/letsencrypt/live/lectiospace.online/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/lectiospace.online/privkey.pem;

    root /var/www/teaching-panel-africa/frontend/build;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:8002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /admin/ {
        proxy_pass http://127.0.0.1:8002;
        proxy_set_header Host $host;
    }

    location /static/ {
        alias /var/www/teaching-panel-africa/teaching_panel/staticfiles/;
    }

    location /media/ {
        alias /var/www/teaching-panel-africa/teaching_panel/media/;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }

    add_header X-Environment "PRODUCTION-AFRICA" always;
}
EOF

ln -sf /etc/nginx/sites-available/lectiospace.online /etc/nginx/sites-enabled/

# ============================================
# 3. SSL сертификаты
# ============================================
echo ""
echo "🔒 Getting SSL certificates..."

certbot --nginx \
    -d stage.lectiospace.ru \
    -d lectiospace.online \
    -d www.lectiospace.online \
    --non-interactive --agree-tos --email your-email@example.com

# ============================================
# 4. Запуск всех сервисов
# ============================================
echo ""
echo "🚀 Starting all services..."

systemctl daemon-reload
systemctl enable teaching-panel-stage-ru teaching-panel-africa
systemctl start teaching-panel-stage-ru teaching-panel-africa
nginx -t && systemctl reload nginx

# ============================================
# 5. Проверка
# ============================================
echo ""
echo "✅ SETUP COMPLETED!"
echo "=================================================="
echo ""
echo "🇷🇺 RUSSIA PRODUCTION:"
echo "   URL: https://lectiospace.ru"
echo "   Port: 8000"
echo "   Status: systemctl status teaching-panel"
echo ""
echo "🧪 RUSSIA STAGING (для тестирования обновлений RU):"
echo "   URL: https://stage.lectiospace.ru"
echo "   Port: 8001"
echo "   Status: systemctl status teaching-panel-stage-ru"
echo ""
echo "🌍 AFRICA PRODUCTION (обкатка всех фич):"
echo "   URL: https://lectiospace.online"
echo "   Port: 8002"
echo "   Status: systemctl status teaching-panel-africa"
echo ""
echo "📝 Logs:"
echo "   Russia Prod: tail -f /var/www/teaching-panel/logs/error.log"
echo "   Russia Stage: tail -f /var/www/teaching-panel-stage-ru/logs/error.log"
echo "   Africa Prod: tail -f /var/www/teaching-panel-africa/logs/error.log"
