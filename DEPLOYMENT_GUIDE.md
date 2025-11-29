# Teaching Panel - Production Deployment Guide

## 📋 Pre-Deployment Checklist

### 1. Server Requirements
- **OS**: Ubuntu 20.04+ / Debian 11+ (recommended)
- **RAM**: Minimum 2GB, recommended 4GB+
- **CPU**: 2+ cores recommended
- **Disk**: 20GB+ available space
- **Python**: 3.11+
- **Node.js**: 16+ (for frontend build)

### 2. Required Services
- PostgreSQL 13+ (or MySQL 8+)
- Redis 6+
- Nginx
- Supervisor or systemd
- SSL Certificate (Let's Encrypt recommended)

### 3. Domain & DNS
- Domain name registered
- DNS A record pointing to your server IP
- (Optional) CNAME for www subdomain

### 4. Third-Party Services
- **Zoom API**: Server-to-Server OAuth credentials
- **Google reCAPTCHA v3**: Site key and secret key
- **Email SMTP**: Gmail, Yandex, SendGrid, or Mailgun
- **SMS.ru** (optional): API ID for SMS notifications

---

## 🚀 Quick Deployment (Automated)

### Option 1: Automated Deployment Script

1. **Upload your code to the server:**
```bash
# On your local machine
cd "C:\Users\User\Desktop\WEB panel"
# Compress the project (excluding venv, node_modules, etc.)
tar -czf teaching_panel.tar.gz --exclude=venv --exclude=node_modules --exclude=__pycache__ --exclude=*.pyc .

# Upload to server
scp teaching_panel.tar.gz user@your-server:/tmp/
```

2. **Connect to your server:**
```bash
ssh user@your-server
```

3. **Extract and run deployment script:**
```bash
cd /tmp
tar -xzf teaching_panel.tar.gz -C /var/www/teaching_panel
cd /var/www/teaching_panel/teaching_panel/deployment
sudo chmod +x deploy.sh
sudo bash deploy.sh
```

The script will:
- Install all dependencies
- Set up Python virtual environment
- Configure Nginx and systemd services
- Set up SSL with Let's Encrypt
- Start all services

---

## 📝 Manual Deployment Steps

### Step 1: Prepare Server

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install dependencies
sudo apt-get install -y \
    python3.11 python3.11-venv python3-pip \
    nginx redis-server postgresql postgresql-contrib \
    libpq-dev build-essential git supervisor \
    certbot python3-certbot-nginx nodejs npm
```

### Step 2: Create PostgreSQL Database

```bash
sudo -u postgres psql
```

```sql
CREATE DATABASE teaching_panel;
CREATE USER teaching_panel_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE teaching_panel TO teaching_panel_user;
\q
```

### Step 3: Set Up Project

```bash
# Create directories
sudo mkdir -p /var/www/teaching_panel
sudo mkdir -p /var/log/teaching_panel
sudo mkdir -p /var/run/teaching_panel

# Clone or upload your project
cd /var/www/teaching_panel

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install Python dependencies
cd teaching_panel
pip install -r requirements-production.txt
```

### Step 4: Configure Environment

```bash
# Copy and edit .env file
cp .env.example .env
nano .env
```

**Critical settings to configure:**

```bash
# Django
SECRET_KEY=<generate with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())">
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database (PostgreSQL)
DATABASE_URL=postgresql://teaching_panel_user:your_password@localhost:5432/teaching_panel

# Email (Gmail example)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=Teaching Panel <your-email@gmail.com>

# Zoom API
ZOOM_ACCOUNT_ID=your-zoom-account-id
ZOOM_CLIENT_ID=your-zoom-client-id
ZOOM_CLIENT_SECRET=your-zoom-client-secret

# reCAPTCHA v3
RECAPTCHA_PUBLIC_KEY=your-public-key
RECAPTCHA_PRIVATE_KEY=your-private-key
RECAPTCHA_ENABLED=true

# Redis
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0

# Security (HTTPS)
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000

# Frontend
FRONTEND_URL=https://yourdomain.com
```

### Step 5: Database Setup

```bash
# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Create superuser
python manage.py createsuperuser
```

### Step 6: Build Frontend

```bash
cd /var/www/teaching_panel/frontend

# Create production .env
cat > .env << EOF
REACT_APP_RECAPTCHA_SITE_KEY=your-recaptcha-public-key
REACT_APP_API_URL=https://yourdomain.com
EOF

# Install dependencies and build
npm install
npm run build
```

### Step 7: Configure Systemd Services

```bash
# Copy service files
sudo cp deployment/teaching_panel.service /etc/systemd/system/
sudo cp deployment/celery.service /etc/systemd/system/
sudo cp deployment/celery-beat.service /etc/systemd/system/

# Update paths in service files if needed
sudo nano /etc/systemd/system/teaching_panel.service

# Reload systemd
sudo systemctl daemon-reload

# Enable services
sudo systemctl enable teaching_panel
sudo systemctl enable celery
sudo systemctl enable celery-beat
sudo systemctl enable redis-server
```

### Step 8: Configure Nginx

```bash
# Copy nginx config
sudo cp deployment/nginx.conf /etc/nginx/sites-available/teaching_panel

# Edit domain name
sudo nano /etc/nginx/sites-available/teaching_panel
# Replace 'yourdomain.com' with your actual domain

# Enable site
sudo ln -s /etc/nginx/sites-available/teaching_panel /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx
```

### Step 9: SSL Certificate (Let's Encrypt)

```bash
# Obtain certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Test auto-renewal
sudo certbot renew --dry-run
```

### Step 10: Set Permissions

```bash
sudo chown -R www-data:www-data /var/www/teaching_panel
sudo chown -R www-data:www-data /var/log/teaching_panel
sudo chown -R www-data:www-data /var/run/teaching_panel
sudo chmod -R 755 /var/www/teaching_panel
```

### Step 11: Start Services

```bash
# Start all services
sudo systemctl start redis-server
sudo systemctl start teaching_panel
sudo systemctl start celery
sudo systemctl start celery-beat

# Check status
sudo systemctl status teaching_panel
sudo systemctl status celery
sudo systemctl status celery-beat
```

---

## 🔒 Security Checklist

- [ ] `DEBUG=False` in production
- [ ] Strong `SECRET_KEY` generated
- [ ] PostgreSQL with strong password
- [ ] SSL certificate installed and auto-renewing
- [ ] Firewall configured (UFW/iptables)
- [ ] HTTPS redirect enabled
- [ ] Security headers configured in Nginx
- [ ] `ALLOWED_HOSTS` properly set
- [ ] reCAPTCHA enabled for public forms
- [ ] Regular backups configured
- [ ] Log monitoring set up

---

## 📊 Monitoring & Maintenance

### Updated Logging Strategy (stdout)
Приложение (Django + Gunicorn) теперь пишет логи напрямую в stdout/stderr, собираемые **systemd journald**. Это устраняет проблемы прав при создании файлов логов.

Основные изменения:
- Файловые хэндлеры Django удалены (только `StreamHandler`).
- Gunicorn конфиг (systemd unit) перенастроен на вывод access/error логов в `-` (stdout).
- Используйте `journalctl` для просмотра последних событий.

### View Logs

```bash
# Django / Gunicorn (combined stdout/stderr)
sudo journalctl -u teaching_panel -n 100 --no-pager
sudo journalctl -u teaching_panel -f

# Celery workers
sudo journalctl -u celery -n 100 --no-pager
sudo journalctl -u celery -f

# Celery beat
sudo journalctl -u celery-beat -n 100 --no-pager
sudo journalctl -u celery-beat -f

# Nginx logs (остаются файловыми)
sudo tail -f /var/log/nginx/teaching_panel_access.log
sudo tail -f /var/log/nginx/teaching_panel_error.log
```

### Service Management

```bash
# Restart services
sudo systemctl restart teaching_panel
sudo systemctl restart celery
sudo systemctl restart celery-beat
sudo systemctl restart nginx

# Stop services
sudo systemctl stop teaching_panel

# View status
sudo systemctl status teaching_panel
```

### Database Backup

```bash
# Manual backup
sudo -u postgres pg_dump teaching_panel > backup_$(date +%Y%m%d_%H%M%S).sql

# Automated backup (add to crontab)
0 2 * * * sudo -u postgres pg_dump teaching_panel > /backups/teaching_panel_$(date +\%Y\%m\%d).sql
```

### Update Deployment

```bash
# Pull latest code
cd /var/www/teaching_panel
git pull origin main

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
cd teaching_panel
pip install -r requirements-production.txt

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Rebuild frontend
cd ../frontend
npm install
npm run build

# Restart services
sudo systemctl restart teaching_panel
sudo systemctl restart celery
sudo systemctl restart celery-beat

# Быстрая проверка порта и логов
sudo ss -tlnp | grep ':8000'
sudo journalctl -u teaching_panel -n 50 --no-pager
```

---

## 🐛 Troubleshooting

### Service won't start

```bash
# Check logs
sudo journalctl -u teaching_panel -n 50

# Check if port is already in use
sudo netstat -tulpn | grep :8000

# Verify .env file exists and is readable
ls -la /var/www/teaching_panel/teaching_panel/.env
```

### Database connection errors

```bash
# Test PostgreSQL connection
psql -U teaching_panel_user -d teaching_panel -h localhost

# Check PostgreSQL is running
sudo systemctl status postgresql
```

### Static files not loading

```bash
# Verify static files collected
ls -la /var/www/teaching_panel/teaching_panel/staticfiles/

# Check Nginx configuration
sudo nginx -t

# Verify permissions
sudo chown -R www-data:www-data /var/www/teaching_panel
```

### Celery tasks not running

```bash
# Check Redis
redis-cli ping  # Should return PONG

# Check Celery worker
sudo systemctl status celery

# Check Celery beat
sudo systemctl status celery-beat

# Test Celery manually
cd /var/www/teaching_panel/teaching_panel
source ../venv/bin/activate
celery -A teaching_panel worker --loglevel=debug
```

---

## 📞 Support

For issues or questions:
1. Check logs in `/var/log/teaching_panel/`
2. Review Nginx error logs
3. Check systemd journal logs
4. Verify all environment variables are set correctly

---

## 🔄 Rollback Procedure

If deployment fails:

```bash
# Stop services
sudo systemctl stop teaching_panel celery celery-beat

# Restore database backup
sudo -u postgres psql teaching_panel < backup_YYYYMMDD.sql

# Restore previous code version
cd /var/www/teaching_panel
git reset --hard HEAD~1

# Restart services
sudo systemctl start teaching_panel celery celery-beat
```
