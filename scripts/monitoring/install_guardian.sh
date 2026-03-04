#!/bin/bash
# ============================================================
# Установка Guardian на production сервер
# ============================================================
# Запуск: scp scripts/monitoring/install_guardian.sh tp:/tmp/ && ssh tp 'sudo bash /tmp/install_guardian.sh'
# ============================================================

set -euo pipefail

echo "============================================"
echo "  INSTALLING LECTIO GUARDIAN"
echo "============================================"
echo ""

MONITOR_DIR="/opt/lectio-monitor"
LOG_DIR="/var/log/lectio-monitor"
STATE_DIR="/var/run/lectio-monitor"

# 1. Создание директорий
echo "[1/5] Создание директорий..."
mkdir -p "$MONITOR_DIR" "$LOG_DIR" "$STATE_DIR"
echo "  OK"

# 2. Копирование скрипта (предполагаем что guardian.sh уже в /opt/lectio-monitor/)
echo "[2/5] Проверка guardian.sh..."
if [[ ! -f "$MONITOR_DIR/guardian.sh" ]]; then
    echo "  FAIL: guardian.sh не найден в $MONITOR_DIR"
    echo "  Сначала скопируйте: scp scripts/monitoring/guardian.sh tp:$MONITOR_DIR/"
    exit 1
fi
chmod +x "$MONITOR_DIR/guardian.sh"
echo "  OK: guardian.sh установлен"

# 3. Проверка config.env
echo "[3/5] Проверка config.env..."
if [[ ! -f "$MONITOR_DIR/config.env" ]]; then
    echo "  WARN: config.env не найден, создаю шаблон..."
    cat > "$MONITOR_DIR/config.env" << 'ENVEOF'
# Lectio Monitor Configuration
SITE_URL="https://lectiospace.ru"
INTERNAL_BACKEND_URL="http://127.0.0.1:8000"
PUBLIC_HOST="lectiospace.ru"
PROJECT_ROOT="/var/www/teaching_panel"
FRONTEND_BUILD="/var/www/teaching_panel/frontend/build"

# Telegram (бот ошибок)
ERRORS_BOT_TOKEN=""
ERRORS_CHAT_ID=""

# Smoke test users
SMOKE_TEACHER_EMAIL="smoke_teacher@test.local"
SMOKE_TEACHER_PASSWORD="SmokeTest123!"
SMOKE_STUDENT_EMAIL="smoke_student@test.local"
SMOKE_STUDENT_PASSWORD="SmokeTest123!"
ENVEOF
    echo "  WARN: Заполните $MONITOR_DIR/config.env"
else
    echo "  OK: config.env существует"
fi

# 4. Добавляем в cron (каждые 2 минуты)
echo "[4/5] Настройка cron..."
GUARDIAN_CRON="*/2 * * * * /opt/lectio-monitor/guardian.sh >> /var/log/lectio-monitor/guardian_cron.log 2>&1"

# Проверяем нет ли уже
if crontab -l 2>/dev/null | grep -q "guardian.sh"; then
    echo "  OK: guardian уже в cron"
else
    (crontab -l 2>/dev/null || true; echo "$GUARDIAN_CRON") | crontab -
    echo "  OK: guardian добавлен в cron (*/2 * * * *)"
fi

# 5. Сохраняем текущий коммит как known good
echo "[5/5] Инициализация known good state..."
if [[ -d "/var/www/teaching_panel/.git" ]]; then
    COMMIT=$(cd /var/www/teaching_panel && git rev-parse --short HEAD)
    echo "$COMMIT $(date '+%Y-%m-%d %H:%M:%S')" > "$STATE_DIR/last_known_good"
    echo "  OK: $COMMIT сохранён как last_known_good"
else
    echo "  WARN: git не найден, known good не инициализирован"
fi

echo ""
echo "============================================"
echo "  GUARDIAN УСТАНОВЛЕН"
echo "============================================"
echo ""
echo "Что он делает:"
echo "  - Каждые 2 минуты проверяет:"
echo "    * Services (teaching_panel, nginx, celery)"
echo "    * HTTP (главная, /api/health/)"
echo "    * Frontend build (index.html -> JS файл)"
echo "    * Auth (JWT login + API endpoints)"
echo "    * Resources (диск, память)"
echo ""
echo "  - При поломке автоматически пробует:"
echo "    L1: Перезапуск сервисов"
echo "    L2: Fix permissions + nginx"
echo "    L3: Git rollback на last_known_good"
echo ""
echo "  - Алерт в Telegram ТОЛЬКО если не может починить сам"
echo ""
echo "Управление:"
echo "  Пауза (деплой):  touch $STATE_DIR/maintenance_mode"
echo "  Проверить логи:   tail -f $LOG_DIR/guardian.log"
echo "  Ручной запуск:    $MONITOR_DIR/guardian.sh"
echo "  Текущий known_good: cat $STATE_DIR/last_known_good"
echo ""
