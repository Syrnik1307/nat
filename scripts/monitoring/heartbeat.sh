#!/bin/bash
# ============================================================
# HEARTBEAT - Пинг внешнего uptime сервиса
# ============================================================
# Отправляет heartbeat на healthchecks.io или аналог.
# Если сервер не пингует > 5 минут, внешний сервис шлёт алерт.
# 
# Это защита от случая когда ВЕСЬ сервер лёг и локальные
# скрипты мониторинга не могут отправить алерт.
#
# Настройка:
# 1. Зарегистрироваться на healthchecks.io (бесплатно)
# 2. Создать check, получить URL типа https://hc-ping.com/xxx
# 3. Добавить в config.env: HEARTBEAT_URL="https://hc-ping.com/xxx"
# 4. Добавить в cron: * * * * * /opt/lectio-monitor/heartbeat.sh
#
# Расположение: /opt/lectio-monitor/heartbeat.sh
# ============================================================

CONFIG_FILE="/opt/lectio-monitor/config.env"
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
fi

HEARTBEAT_URL="${HEARTBEAT_URL:-}"

if [[ -z "$HEARTBEAT_URL" ]]; then
    # Нет URL - пропускаем
    exit 0
fi

# Проверяем что сайт жив перед отправкой heartbeat
# Это гарантирует что если сайт лежит, heartbeat НЕ уйдёт
# и внешний сервис отправит алерт

http_code=$(curl -s -o /dev/null -w "%{http_code}" \
    --max-time 10 \
    --connect-timeout 5 \
    "${SITE_URL:-https://lectio.tw1.ru}/api/health/" 2>/dev/null) || http_code="000"

if [[ "$http_code" == "200" ]]; then
    # Сайт жив - отправляем heartbeat
    curl -s -m 10 "$HEARTBEAT_URL" > /dev/null 2>&1
else
    # Сайт лежит - НЕ отправляем heartbeat
    # Внешний сервис заметит отсутствие пинга и пришлёт алерт
    echo "Site down (HTTP $http_code), skipping heartbeat"
    exit 1
fi
