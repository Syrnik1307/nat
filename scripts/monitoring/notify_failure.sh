#!/bin/bash
# ============================================================
# TELEGRAM NOTIFICATION SCRIPT for Service Failures
# ============================================================
# Расположение: /opt/lectio-monitor/notify_failure.sh
# ============================================================

set -euo pipefail

SERVICE_NAME="${1:-unknown}"

# Загружаем конфигурацию
CONFIG_FILE="/opt/lectio-monitor/config.env"
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
fi

# Используем отдельный бот для ошибок
# Fallback на старые переменные для обратной совместимости
ERRORS_BOT_TOKEN="${ERRORS_BOT_TOKEN:-${TELEGRAM_BOT_TOKEN:-}}"
ERRORS_CHAT_ID="${ERRORS_CHAT_ID:-${TELEGRAM_CHAT_ID:-}}"

if [[ -z "$ERRORS_BOT_TOKEN" ]] || [[ -z "$ERRORS_CHAT_ID" ]]; then
    echo "Telegram Errors Bot не настроен"
    exit 0
fi

# Собираем информацию о сервисе
SERVICE_STATUS=$(systemctl status "$SERVICE_NAME" 2>&1 | head -20 || echo "Unable to get status")
JOURNAL_LOGS=$(journalctl -u "$SERVICE_NAME" -n 10 --no-pager 2>&1 || echo "Unable to get logs")

# Форматируем сообщение
MESSAGE="🚨🚨🚨 СЕРВИС УПАЛ!

📛 Сервис: $SERVICE_NAME
🖥️ Сервер: $(hostname)
🕐 Время: $(date '+%Y-%m-%d %H:%M:%S')

📊 Статус:
$(echo "$SERVICE_STATUS" | head -10)

📝 Последние логи:
$(echo "$JOURNAL_LOGS" | tail -5)

⚡ Действие: Автоматический перезапуск..."

# Отправляем в Telegram (бот ошибок)
curl -s -X POST "https://api.telegram.org/bot${ERRORS_BOT_TOKEN}/sendMessage" \
    -d "chat_id=${ERRORS_CHAT_ID}" \
    -d "text=${MESSAGE}" \
    -d "parse_mode=HTML" \
    > /dev/null 2>&1

# Логируем
echo "$(date '+%Y-%m-%d %H:%M:%S') Service failure notification sent for: $SERVICE_NAME" \
    >> /var/log/lectio-monitor/notifications.log
