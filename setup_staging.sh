#!/bin/bash
# Настройка staging окружения на lectiospace.online
# Запускать на СЕРВЕРЕ от root

set -e  # Остановка при ошибке

echo "🧪 Setting up STAGING environment on lectiospace.online"
echo "=================================================="

# 1. Создаем директорию для staging
echo "📁 Creating staging directory..."
mkdir -p /var/www/teaching-panel-staging
cd /var/www/teaching-panel-staging

# 2. Клонируем репозиторий (ветка staging)
echo "📥 Cloning repository (staging branch)..."
if [ ! -d ".git" ]; then
    git clone -b staging https://github.com/YOUR_USERNAME/teaching-panel.git .
else
    echo "Repository already exists, pulling latest..."
    git pull origin staging
fi

# 3. Создаем Python virtual environment
echo "🐍 Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# 4. Устанавливаем зависимости
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# 5. Создаем .env файл для staging
echo "⚙️ Creating .env file..."
cat > .env << 'EOF'
# Staging Environment
DJANGO_SETTINGS_MODULE=teaching_panel.settings_staging
SECRET_KEY=staging-secret-key-change-me-$(openssl rand -base64 32)
DEBUG=True
ALLOWED_HOSTS=lectiospace.online,www.lectiospace.online

# Database (отдельная от прода!)
DATABASE_URL=sqlite:////var/www/teaching-panel-staging/db_staging.sqlite3

# Feature Flags - ВСЕ включены для тестирования
FEATURE_AFRICA_MARKET=True
FEATURE_PWA_OFFLINE=True
FEATURE_MOBILE_MONEY=True
FEATURE_SMS_NOTIFICATIONS=True
FEATURE_MULTILINGUAL=True

# Payments - ТЕСТОВЫЕ ключи
YOOKASSA_ACCOUNT_ID=test_account
YOOKASSA_SECRET_KEY=test_secret

# Frontend URL
FRONTEND_URL=https://lectiospace.online

# Email (console для staging)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EOF

# 6. Миграции
echo "🗄️ Running migrations..."
python teaching_panel/manage.py migrate

# 7. Создаем суперюзера для staging
echo "👤 Creating staging admin user..."
python teaching_panel/manage.py shell << 'PYTHON'
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email='admin@staging.test').exists():
    User.objects.create_superuser(
        email='admin@staging.test',
        password='staging123',
        first_name='Staging',
        last_name='Admin',
        role='admin'
    )
    print("✅ Staging admin created: admin@staging.test / staging123")
else:
    print("⚠️ Admin already exists")
PYTHON

# 8. Собираем статику
echo "📦 Collecting static files..."
python teaching_panel/manage.py collectstatic --noinput

# 9. Настраиваем права
echo "🔐 Setting permissions..."
chown -R www-data:www-data /var/www/teaching-panel-staging
chmod -R 755 /var/www/teaching-panel-staging

# 10. Создаем systemd service для staging
echo "⚙️ Creating systemd service..."
cat > /etc/systemd/system/teaching-panel-staging.service << 'EOF'
[Unit]
Description=Teaching Panel Staging (lectiospace.online)
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/teaching-panel-staging/teaching_panel
Environment="PATH=/var/www/teaching-panel-staging/venv/bin"
Environment="DJANGO_SETTINGS_MODULE=teaching_panel.settings_staging"
ExecStart=/var/www/teaching-panel-staging/venv/bin/gunicorn \
    --workers 2 \
    --bind 127.0.0.1:8001 \
    --access-logfile /var/www/teaching-panel-staging/logs/access.log \
    --error-logfile /var/www/teaching-panel-staging/logs/error.log \
    --log-level info \
    teaching_panel.wsgi:application

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 11. Создаем директорию для логов
mkdir -p /var/www/teaching-panel-staging/logs
chown -R www-data:www-data /var/www/teaching-panel-staging/logs

# 12. Настраиваем Nginx для staging
echo "🌐 Configuring Nginx for staging..."
cat > /etc/nginx/sites-available/lectiospace.online << 'EOF'
server {
    listen 80;
    server_name lectiospace.online www.lectiospace.online;

    # Redirect to HTTPS
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name lectiospace.online www.lectiospace.online;

    # SSL certificates (будут получены через certbot)
    ssl_certificate /etc/letsencrypt/live/lectiospace.online/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/lectiospace.online/privkey.pem;

    # Frontend (React build)
    root /var/www/teaching-panel-staging/frontend/build;
    index index.html;

    # Backend API (Django на порту 8001)
    location /api/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Admin panel
    location /admin/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Static files (Django)
    location /static/ {
        alias /var/www/teaching-panel-staging/teaching_panel/staticfiles/;
    }

    # Media files
    location /media/ {
        alias /var/www/teaching-panel-staging/teaching_panel/media/;
    }

    # React Router - все остальное на index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Staging banner (чтобы не путать с продом)
    add_header X-Environment "STAGING" always;
}
EOF

# Включаем сайт
ln -sf /etc/nginx/sites-available/lectiospace.online /etc/nginx/sites-enabled/

# 13. Получаем SSL сертификат
echo "🔒 Getting SSL certificate..."
certbot --nginx -d lectiospace.online -d www.lectiospace.online --non-interactive --agree-tos --email your-email@example.com

# 14. Тестируем Nginx конфиг
echo "✅ Testing Nginx configuration..."
nginx -t

# 15. Перезапускаем сервисы
echo "🔄 Restarting services..."
systemctl daemon-reload
systemctl enable teaching-panel-staging
systemctl start teaching-panel-staging
systemctl reload nginx

# 16. Проверка статуса
echo ""
echo "✅ STAGING SETUP COMPLETED!"
echo "=================================================="
echo "🌐 Staging URL: https://lectiospace.online"
echo "👤 Admin login: admin@staging.test / staging123"
echo "📊 Check status: systemctl status teaching-panel-staging"
echo "📝 View logs: tail -f /var/www/teaching-panel-staging/logs/error.log"
echo ""
echo "🔍 Testing backend: curl https://lectiospace.online/api/health/"
curl -s https://lectiospace.online/api/health/ || echo "⚠️ Backend not responding yet"

echo ""
echo "📋 Next steps:"
echo "1. Deploy frontend: cd frontend && npm run build && copy to server"
echo "2. Test on https://lectiospace.online"
echo "3. When ready, deploy to prod: deploy.ps1 -Environment production-russia"
