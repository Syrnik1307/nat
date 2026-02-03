#!/bin/bash
# ============================================================
# LECTIO PRE-LAUNCH FIXES
# ============================================================
# Скрипт для автоматического исправления критических проблем
# перед запуском в production.
#
# Запуск: bash fix_production.sh
# ============================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=============================================="
echo " LECTIO PRE-LAUNCH FIXES"
echo "==============================================${NC}"
echo ""

# ==================== 1. UFW FIREWALL ====================
echo -e "${YELLOW}[1/5] Настройка UFW Firewall...${NC}"

if ! command -v ufw &> /dev/null; then
    echo "Установка ufw..."
    sudo apt install -y ufw
fi

sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw allow 10050/tcp  # Zabbix agent (если используется)
echo "y" | sudo ufw enable

echo -e "${GREEN}✅ UFW настроен${NC}"
sudo ufw status
echo ""

# ==================== 2. FAIL2BAN ====================
echo -e "${YELLOW}[2/5] Установка и настройка Fail2Ban...${NC}"

if ! command -v fail2ban-client &> /dev/null; then
    sudo apt install -y fail2ban
fi

sudo tee /etc/fail2ban/jail.local > /dev/null << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log
maxretry = 5

[nginx-http-auth]
enabled = true
logpath = /var/log/nginx/error.log

[nginx-limit-req]
enabled = true
logpath = /var/log/nginx/error.log
maxretry = 10
findtime = 60
bantime = 600

[lectio-login]
enabled = true
port = http,https
filter = lectio-login
logpath = /var/log/teaching_panel/django_error.log
maxretry = 5
findtime = 300
bantime = 1800
EOF

# Создаём фильтр для Django логина
sudo tee /etc/fail2ban/filter.d/lectio-login.conf > /dev/null << 'EOF'
[Definition]
failregex = ^.*LOGIN_FAILED.*IP=<HOST>.*$
            ^.*Invalid credentials.*<HOST>.*$
ignoreregex =
EOF

sudo systemctl enable fail2ban
sudo systemctl restart fail2ban

echo -e "${GREEN}✅ Fail2Ban настроен${NC}"
sudo fail2ban-client status
echo ""

# ==================== 3. NGINX RATE LIMITING ====================
echo -e "${YELLOW}[3/5] Настройка Rate Limiting в Nginx...${NC}"

# Проверяем есть ли уже rate limiting в nginx.conf
if ! grep -q "limit_req_zone" /etc/nginx/nginx.conf; then
    # Добавляем в http {} блок
    sudo sed -i '/http {/a \
    # Rate Limiting для защиты от DDoS\
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;\
    limit_req_zone $binary_remote_addr zone=login_limit:10m rate=1r/s;\
    limit_conn_zone $binary_remote_addr zone=conn_limit:10m;' /etc/nginx/nginx.conf
    
    echo -e "${GREEN}✅ Rate limiting добавлен в nginx.conf${NC}"
else
    echo "Rate limiting уже настроен в nginx.conf"
fi

# Проверяем конфигурацию
sudo nginx -t && sudo systemctl reload nginx
echo ""

# ==================== 4. ALLOWED_HOSTS ====================
echo -e "${YELLOW}[4/5] Обновление ALLOWED_HOSTS...${NC}"

ENV_FILE="/var/www/teaching_panel/teaching_panel/.env"
if [ -f "$ENV_FILE" ]; then
    # Добавляем lectiospace.ru если его нет
    if ! grep -q "lectiospace.ru" "$ENV_FILE"; then
        sed -i 's/ALLOWED_HOSTS=\(.*\)/ALLOWED_HOSTS=\1,lectiospace.ru/' "$ENV_FILE"
        echo -e "${GREEN}✅ lectiospace.ru добавлен в ALLOWED_HOSTS${NC}"
    else
        echo "lectiospace.ru уже в ALLOWED_HOSTS"
    fi
fi
echo ""

# ==================== 5. БЭКАПЫ ====================
echo -e "${YELLOW}[5/5] Проверка и запуск бэкапов...${NC}"

# Создаём директорию для логов Django если нет
sudo mkdir -p /var/log/teaching_panel
sudo chown www-data:www-data /var/log/teaching_panel

# Проверяем cron
if ! crontab -l 2>/dev/null | grep -q "backup_db.sh"; then
    (crontab -l 2>/dev/null; echo "0 3 * * * /var/www/teaching_panel/teaching_panel/backup_db.sh >> /var/backups/teaching_panel/cron.log 2>&1") | crontab -
    echo "Cron для бэкапов добавлен"
fi

# Запускаем бэкап сейчас
echo "Запуск бэкапа..."
/var/www/teaching_panel/teaching_panel/backup_db.sh || true

echo -e "${GREEN}✅ Бэкапы настроены${NC}"
ls -la /var/backups/teaching_panel/ | tail -3
echo ""

# ==================== ИТОГ ====================
echo -e "${GREEN}=============================================="
echo " ГОТОВО!"
echo "==============================================${NC}"
echo ""
echo "Выполнено:"
echo "  ✅ UFW Firewall включен"
echo "  ✅ Fail2Ban установлен и настроен"
echo "  ✅ Rate Limiting добавлен в Nginx"
echo "  ✅ ALLOWED_HOSTS обновлён"
echo "  ✅ Бэкап запущен"
echo ""
echo -e "${YELLOW}⚠️  ОСТАЛОСЬ СДЕЛАТЬ ВРУЧНУЮ:${NC}"
echo ""
echo "1. Настроить Telegram бота для алертов:"
echo "   sudo nano /opt/lectio-monitor/config.env"
echo "   # Заменить TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID"
echo ""
echo "2. Добавить rate limiting в location блоки Nginx:"
echo "   sudo nano /etc/nginx/sites-available/lectio"
echo "   # В location /api/ добавить:"
echo "   # limit_req zone=api_limit burst=20 nodelay;"
echo "   # limit_conn conn_limit 10;"
echo ""
echo "3. Протестировать:"
echo "   /opt/lectio-monitor/health_check.sh"
echo ""
echo "4. Перезапустить сервисы:"
echo "   sudo systemctl restart teaching_panel nginx"
echo ""
