#!/bin/bash
# ============================================================
# Установка OPS Bot на production
# ============================================================
# Запуск:
#   scp scripts/monitoring/ops_bot.py tp:/opt/lectio-monitor/
#   scp scripts/monitoring/lectio-ops-bot.service tp:/tmp/
#   scp scripts/monitoring/install_ops_bot.sh tp:/tmp/
#   ssh tp 'sudo bash /tmp/install_ops_bot.sh'
#
# Или одной командой из VS Code task: "ops-bot: install"
# ============================================================

set -euo pipefail

echo "============================================"
echo "  INSTALLING LECTIO OPS BOT"
echo "============================================"
echo ""

MONITOR_DIR="/opt/lectio-monitor"
LOG_DIR="/var/log/lectio-monitor"
VENV="/var/www/teaching_panel/venv"

# 1. Проверяем файлы
echo "[1/5] Проверка файлов..."
if [[ ! -f "$MONITOR_DIR/ops_bot.py" ]]; then
    echo "  FAIL: ops_bot.py не найден в $MONITOR_DIR"
    echo "  Сначала: scp scripts/monitoring/ops_bot.py tp:$MONITOR_DIR/"
    exit 1
fi
echo "  OK: ops_bot.py"

# 2. Установка python-telegram-bot
echo "[2/5] Установка python-telegram-bot..."
if "$VENV/bin/pip" show python-telegram-bot >/dev/null 2>&1; then
    echo "  OK: уже установлен"
else
    "$VENV/bin/pip" install "python-telegram-bot==20.7" -q
    echo "  OK: установлен"
fi

# 3. Конфигурация
echo "[3/5] Проверка конфигурации..."
OPS_CONFIG="$MONITOR_DIR/ops_bot.env"
if [[ ! -f "$OPS_CONFIG" ]]; then
    echo ""
    echo "  Создаю шаблон конфига: $OPS_CONFIG"
    echo "  ВАЖНО: заполни его перед запуском!"
    echo ""
    cat > "$OPS_CONFIG" << 'ENVEOF'
# Lectio OPS Bot Configuration
# Создай ОТДЕЛЬНОГО бота через @BotFather (НЕ основной бот!)
# Токен основного бота НЕ подойдёт — они будут конфликтовать

OPS_BOT_TOKEN=""

# Твой Telegram chat_id (узнай у @userinfobot или @getidsbot)
# Можно несколько через запятую: 123456789,987654321
ADMIN_CHAT_IDS=""
ENVEOF
    chmod 600 "$OPS_CONFIG"
    echo "  WARN: Заполни $OPS_CONFIG!"
    echo ""
    echo "  Как получить chat_id:"
    echo "    1. Напиши @userinfobot в Telegram"
    echo "    2. Он ответит твой Id: 123456789"
    echo "    3. Впиши в ADMIN_CHAT_IDS"
    echo ""
    echo "  Как создать бота:"
    echo "    1. @BotFather → /newbot"
    echo "    2. Имя: LectioOps или любое"
    echo "    3. Токен → в OPS_BOT_TOKEN"
    echo ""
else
    # Проверяем что заполнен
    source "$OPS_CONFIG"
    if [[ -z "${OPS_BOT_TOKEN:-}" ]]; then
        echo "  WARN: OPS_BOT_TOKEN пуст в $OPS_CONFIG"
    else
        echo "  OK: OPS_BOT_TOKEN задан"
    fi
    if [[ -z "${ADMIN_CHAT_IDS:-}" ]]; then
        echo "  WARN: ADMIN_CHAT_IDS пуст в $OPS_CONFIG"
    else
        echo "  OK: ADMIN_CHAT_IDS=$ADMIN_CHAT_IDS"
    fi
fi

# 4. Systemd service
echo "[4/5] Установка systemd service..."
if [[ -f "/tmp/lectio-ops-bot.service" ]]; then
    cp /tmp/lectio-ops-bot.service /etc/systemd/system/lectio-ops-bot.service
elif [[ -f "$MONITOR_DIR/lectio-ops-bot.service" ]]; then
    cp "$MONITOR_DIR/lectio-ops-bot.service" /etc/systemd/system/
fi

systemctl daemon-reload

# Проверяем что конфиг заполнен перед стартом
source "$OPS_CONFIG" 2>/dev/null || true
if [[ -n "${OPS_BOT_TOKEN:-}" && -n "${ADMIN_CHAT_IDS:-}" ]]; then
    systemctl enable lectio-ops-bot
    systemctl restart lectio-ops-bot
    sleep 2
    
    if systemctl is-active --quiet lectio-ops-bot; then
        echo "  OK: lectio-ops-bot запущен и работает"
    else
        echo "  FAIL: lectio-ops-bot не запустился"
        echo "  Проверь: journalctl -u lectio-ops-bot -n 20"
    fi
else
    echo "  SKIP: не запускаю — заполни $OPS_CONFIG сначала"
    echo "  После заполнения:"
    echo "    sudo systemctl enable lectio-ops-bot"
    echo "    sudo systemctl start lectio-ops-bot"
fi

# 5. Создаём директорию логов
echo "[5/5] Подготовка..."
mkdir -p "$LOG_DIR"
echo "  OK"

echo ""
echo "============================================"
echo "  OPS BOT УСТАНОВЛЕН"
echo "============================================"
echo ""
echo "Что он умеет (через Telegram):"
echo ""
echo "  Мониторинг:"
echo "    /status    — Полный статус сайта"
echo "    /health    — Health check"
echo "    /logs      — Логи gunicorn"
echo "    /disk      — Использование диска"
echo ""
echo "  Управление:"
echo "    /restart     — Restart gunicorn+celery"
echo "    /restart_all — Restart всего"
echo "    /guardian    — Запустить guardian"
echo "    /pause       — Пауза guardian"
echo "    /resume      — Снять паузу"
echo ""
echo "  Аварийные:"
echo "    /rollback    — Git rollback"
echo "    /rollback_db — Rollback + DB restore"
echo ""
echo "Логи: journalctl -u lectio-ops-bot -f"
echo ""
