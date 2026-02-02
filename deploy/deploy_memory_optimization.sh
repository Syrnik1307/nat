#!/bin/bash
# =============================================================================
# EMERGENCY MEMORY OPTIMIZATION DEPLOY
# =============================================================================
# Решает проблему OOM kills на 2GB сервере
# Применяет:
# - Оптимизированные systemd сервисы (меньше workers)
# - Обновлённый settings.py (DB connections, Celery intervals)
# - Обновлённый celery.py (gc.collect после задач)
# =============================================================================

set -e

echo "=== EMERGENCY MEMORY OPTIMIZATION DEPLOY ==="
echo "Date: $(date)"
echo ""

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

APP_DIR="/var/www/teaching_panel"
TEACHING_PANEL_DIR="$APP_DIR/teaching_panel"

# Проверяем что мы root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}ERROR: Запустите от root: sudo $0${NC}"
    exit 1
fi

echo -e "${YELLOW}Step 1: Остановка сервисов...${NC}"
systemctl stop teaching_panel celery celery-beat || true
sleep 2

echo -e "${YELLOW}Step 2: Синхронизация кода...${NC}"
cd $TEACHING_PANEL_DIR
sudo -u www-data git fetch origin
sudo -u www-data git reset --hard origin/main

echo -e "${YELLOW}Step 3: Обновление systemd сервисов...${NC}"

# Backup старых конфигов
cp /etc/systemd/system/teaching_panel.service /etc/systemd/system/teaching_panel.service.bak.$(date +%Y%m%d_%H%M%S) || true
cp /etc/systemd/system/celery.service /etc/systemd/system/celery.service.bak.$(date +%Y%m%d_%H%M%S) || true

# Обновляем teaching_panel.service - только workers и timeout
# Вместо полной замены делаем sed замены
sed -i 's/--workers 2/--workers 1/g' /etc/systemd/system/teaching_panel.service
sed -i 's/--timeout 120/--timeout 30/g' /etc/systemd/system/teaching_panel.service
sed -i 's/--timeout 300/--timeout 30/g' /etc/systemd/system/teaching_panel.service
sed -i 's/--graceful-timeout 30/--graceful-timeout 10/g' /etc/systemd/system/teaching_panel.service
sed -i 's/--max-requests 500/--max-requests 300/g' /etc/systemd/system/teaching_panel.service

# Обновляем celery.service - добавляем memory limits
cat > /etc/systemd/system/celery.service << 'EOF'
[Unit]
Description=Teaching Panel Celery Worker (Memory Optimized)
After=network.target redis.service postgresql.service
Wants=redis.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/teaching_panel/teaching_panel
Environment="PATH=/var/www/teaching_panel/venv/bin"

# MEMORY OPTIMIZATION 2026-02-02:
# - Single worker (-c 1) to reduce memory footprint
# - max-memory-per-child: Restart if exceeds 150MB
# - max-tasks-per-child: Restart after 50 tasks
ExecStart=/var/www/teaching_panel/venv/bin/celery -A teaching_panel worker \
    --loglevel=info \
    --concurrency=1 \
    --pool=prefork \
    --max-memory-per-child=150000 \
    --max-tasks-per-child=50 \
    --without-gossip \
    --without-mingle \
    --without-heartbeat

# Memory limits enforced by systemd
MemoryMax=300M
MemoryHigh=250M

Restart=always
RestartSec=10
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
EOF

echo -e "${YELLOW}Step 4: Перезагрузка systemd...${NC}"
systemctl daemon-reload

echo -e "${YELLOW}Step 5: Запуск сервисов...${NC}"
systemctl start celery-beat
sleep 2
systemctl start celery
sleep 3
systemctl start teaching_panel
sleep 3

echo -e "${YELLOW}Step 6: Проверка статуса...${NC}"
echo ""
echo "=== Статус сервисов ==="
systemctl is-active teaching_panel celery celery-beat
echo ""

echo "=== Использование памяти ==="
free -h
echo ""

echo "=== Top Python процессы ==="
ps aux --sort=-%mem | grep python | head -10
echo ""

# Тест login
echo -e "${YELLOW}Step 7: Smoke test - login...${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST https://lectio.tw1.ru/api/jwt/token/ \
    -H "Content-Type: application/json" \
    -H "X-Forwarded-Proto: https" \
    -d '{"email":"test@test.com","password":"Test1234"}' \
    --max-time 10)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | head -1)

if [ "$HTTP_CODE" == "200" ]; then
    echo -e "${GREEN}SUCCESS: Login работает (HTTP 200)${NC}"
elif [ "$HTTP_CODE" == "401" ]; then
    echo -e "${GREEN}SUCCESS: Сервер отвечает быстро (HTTP 401 - неверные credentials)${NC}"
else
    echo -e "${RED}WARNING: HTTP $HTTP_CODE - проверьте логи${NC}"
    echo "Response: $BODY"
fi

echo ""
echo -e "${GREEN}=== DEPLOY COMPLETED ===${NC}"
echo "Логи: journalctl -u teaching_panel -f"
