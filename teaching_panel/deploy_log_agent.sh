#!/bin/bash
# =============================================================================
# deploy_log_agent.sh — Деплой AI Log Agent на продакшен
# =============================================================================
# 
# Использование:
#   1. Заполните переменные ниже
#   2. Запустите: bash deploy_log_agent.sh
#
# Или с локальной машины:
#   scp teaching_panel/log_agent.py root@72.56.81.163:/var/www/teaching_panel/teaching_panel/
#   scp teaching_panel/log_agent.service root@72.56.81.163:/etc/systemd/system/
#   ssh root@72.56.81.163 "bash -s" < deploy_log_agent.sh
# =============================================================================

set -e

echo "============================================="
echo "🤖 Деплой AI Log Agent"
echo "============================================="

# --- Конфигурация (заполните!) ---
DEEPSEEK_API_KEY="${DEEPSEEK_API_KEY:-}"
LOG_AGENT_TG_TOKEN="${LOG_AGENT_TG_TOKEN:-}"
LOG_AGENT_TG_CHAT="${LOG_AGENT_TG_CHAT:-}"

PROJECT_DIR="/var/www/teaching_panel"
APP_DIR="${PROJECT_DIR}/teaching_panel"
VENV_DIR="${PROJECT_DIR}/venv"
LOG_DIR="/var/log/teaching_panel"

# --- Проверки ---
if [ -z "$DEEPSEEK_API_KEY" ]; then
    echo "❌ DEEPSEEK_API_KEY не задан!"
    echo "   Получите ключ на https://platform.deepseek.com/"
    echo "   export DEEPSEEK_API_KEY=sk-..."
    exit 1
fi

if [ -z "$LOG_AGENT_TG_TOKEN" ]; then
    echo "❌ LOG_AGENT_TG_TOKEN не задан!"
    echo "   Создайте бота через @BotFather в Telegram"
    exit 1
fi

if [ -z "$LOG_AGENT_TG_CHAT" ]; then
    echo "❌ LOG_AGENT_TG_CHAT не задан!"
    echo "   Отправьте /start боту, затем:"
    echo "   curl https://api.telegram.org/bot<TOKEN>/getUpdates | python3 -m json.tool"
    echo "   Найдите chat.id в ответе"
    exit 1
fi

# --- 1. Подготовка ---
echo ""
echo "📁 Подготовка директорий..."
mkdir -p "$LOG_DIR"
mkdir -p "${APP_DIR}/logs"

# --- 2. Установка зависимостей ---
echo "📦 Проверка зависимостей..."
${VENV_DIR}/bin/pip install requests 2>/dev/null || true

# --- 3. Файл окружения ---
echo "🔧 Создание /etc/log_agent.env..."
cat > /etc/log_agent.env << EOF
DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
LOG_AGENT_TG_TOKEN=${LOG_AGENT_TG_TOKEN}
LOG_AGENT_TG_CHAT=${LOG_AGENT_TG_CHAT}
LOG_AGENT_INTERVAL=60
LOG_AGENT_MODEL=deepseek-chat
EOF
chmod 600 /etc/log_agent.env

# --- 4. Копирование файлов (если ещё не на месте) ---
if [ ! -f "${APP_DIR}/log_agent.py" ]; then
    echo "📄 log_agent.py не найден в ${APP_DIR}, скопируйте вручную"
    exit 1
fi

# --- 5. systemd сервис ---
echo "⚙️  Настройка systemd сервиса..."
cat > /etc/systemd/system/log-agent.service << 'UNIT'
[Unit]
Description=AI Log Agent — мониторинг логов с AI-диагностикой
After=network.target teaching_panel.service
Wants=teaching_panel.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/var/www/teaching_panel/teaching_panel
ExecStart=/var/www/teaching_panel/venv/bin/python log_agent.py
Restart=always
RestartSec=10
EnvironmentFile=/etc/log_agent.env
StandardOutput=journal
StandardError=journal
SyslogIdentifier=log-agent

[Install]
WantedBy=multi-user.target
UNIT

# --- 6. Запуск ---
echo "🚀 Запуск сервиса..."
systemctl daemon-reload
systemctl enable log-agent
systemctl restart log-agent

# --- 7. Проверка ---
sleep 3
STATUS=$(systemctl is-active log-agent)
echo ""
echo "============================================="
if [ "$STATUS" = "active" ]; then
    echo "✅ Log Agent запущен и работает!"
    echo ""
    echo "Полезные команды:"
    echo "  systemctl status log-agent       # Статус"
    echo "  journalctl -u log-agent -f       # Логи в реальном времени"
    echo "  systemctl restart log-agent      # Перезапуск"
    echo "  systemctl stop log-agent         # Остановка"
    echo ""
    echo "  # Тест подключений:"
    echo "  cd ${APP_DIR} && ${VENV_DIR}/bin/python log_agent.py --test"
    echo ""
    echo "  # Анализ последних ошибок:"
    echo "  cd ${APP_DIR} && ${VENV_DIR}/bin/python log_agent.py --analyze-last"
else
    echo "❌ Сервис не запустился!"
    echo "Проверьте логи: journalctl -u log-agent -n 50"
    systemctl status log-agent || true
fi
echo "============================================="
