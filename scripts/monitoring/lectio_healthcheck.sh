#!/bin/bash
export TZ=Europe/Moscow
# ============================================================
# Lectio Space — Health Check v2 (2026-02-24)
# ============================================================
#
# Лёгкий скрипт проверки здоровья сайта.
# НЕ перезапускает сервисы, НЕ трогает файлы — только проверяет
# и шлёт алерт в Telegram если что-то не так.
#
# Проверки:
#   1. nginx работает
#   2. gunicorn (teaching_panel) работает
#   3. Backend API отвечает 200
#   4. Frontend index.html существует
#   5. Все JS/CSS из index.html реально лежат на диске
#
# Установка:
#   scp lectio_healthcheck.sh tp:/opt/lectio-monitor/
#   ssh tp "chmod +x /opt/lectio-monitor/lectio_healthcheck.sh"
#   Добавить в cron (каждые 3 мин):
#     */3 * * * * /opt/lectio-monitor/lectio_healthcheck.sh >> /var/log/lectio-monitor/healthcheck.log 2>&1
#
# ============================================================

set -euo pipefail

# --- Конфиг ---
CONFIG="/opt/lectio-monitor/config.env"
[[ -f "$CONFIG" ]] && source "$CONFIG"

SITE_URL="${SITE_URL:-https://lectiospace.ru}"
FRONTEND_BUILD="${FRONTEND_BUILD:-/var/www/teaching_panel/frontend/build}"
BACKEND_SERVICE="${BACKEND_SERVICE:-teaching_panel}"
NGINX_SERVICE="${NGINX_SERVICE:-nginx}"
LOG_DIR="${LOG_DIR:-/var/log/lectio-monitor}"
BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
CHAT_ID="${TELEGRAM_CHAT_ID:-}"

# Флаг чтобы не спамить (кулдаун 10 минут)
ALERT_COOLDOWN_FILE="/tmp/lectio_healthcheck_alert_sent"
ALERT_COOLDOWN_SEC=180

mkdir -p "$LOG_DIR"

# --- Функции ---

send_telegram() {
    local msg="$1"
    if [[ -z "$BOT_TOKEN" || -z "$CHAT_ID" ]]; then
        echo "[WARN] Telegram не настроен, алерт только в лог"
        return
    fi
    curl -s --max-time 10 \
        "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -d "chat_id=${CHAT_ID}" \
        -d "text=${msg}" \
        -d "parse_mode=HTML" \
        -d "disable_web_page_preview=true" > /dev/null 2>&1 || true
}

should_alert() {
    if [[ -f "$ALERT_COOLDOWN_FILE" ]]; then
        local last_alert
        last_alert=$(stat -c %Y "$ALERT_COOLDOWN_FILE" 2>/dev/null || echo 0)
        local now
        now=$(date +%s)
        if (( now - last_alert < ALERT_COOLDOWN_SEC )); then
            return 1  # ещё рано
        fi
    fi
    return 0
}

mark_alert_sent() {
    touch "$ALERT_COOLDOWN_FILE"
}

clear_alert() {
    rm -f "$ALERT_COOLDOWN_FILE"
}

timestamp() {
    date '+%Y-%m-%d %H:%M:%S'
}

# --- Проверки ---

ERRORS=()

# 1. nginx
if ! systemctl is-active --quiet "$NGINX_SERVICE" 2>/dev/null; then
    ERRORS+=("nginx не запущен")
fi

# 2. gunicorn
if ! systemctl is-active --quiet "$BACKEND_SERVICE" 2>/dev/null; then
    ERRORS+=("backend ($BACKEND_SERVICE) не запущен")
fi

# 3. Backend API
API_CODE=$(curl -s -o /dev/null -w '%{http_code}' \
    --max-time 10 --connect-timeout 5 \
    "http://127.0.0.1:8000/api/health/" 2>/dev/null) || API_CODE="000"

if [[ "$API_CODE" != "200" ]]; then
    ERRORS+=("Backend API: HTTP $API_CODE (ожидался 200)")
fi

# 4. index.html существует
INDEX_FILE="${FRONTEND_BUILD}/index.html"
if [[ ! -f "$INDEX_FILE" ]]; then
    ERRORS+=("index.html не найден: $INDEX_FILE")
else
    # 5. Все ресурсы из index.html существуют на диске
    # Ищем src="/static/js/..." и href="/static/css/..."
    MISSING_ASSETS=()
    FOUND_ASSETS=0

    # Parse assets: support both absolute (/static/...) and relative (./static/...)
    while IFS= read -r asset; do
        clean_asset="${asset#./}"
        clean_asset="${clean_asset#/}"
        local_path="${FRONTEND_BUILD}/${clean_asset}"
        FOUND_ASSETS=$((FOUND_ASSETS + 1))
        if [[ ! -f "$local_path" ]]; then
            MISSING_ASSETS+=("$asset")
        fi
    done < <(grep -oP '(?:src|href)="\.?/?static/[^"]+' "$INDEX_FILE" | grep -oP '\.?/?static/[^"]+')

    if [[ $FOUND_ASSETS -eq 0 ]]; then
        ERRORS+=("index.html не содержит ссылок на JS/CSS - сломанный билд")
    fi

    if [[ ${#MISSING_ASSETS[@]} -gt 0 ]]; then
        ERRORS+=("Отсутствуют файлы фронтенда: ${MISSING_ASSETS[*]}")
    fi

    # Check: index.html must NOT use relative paths (./static)
    if grep -qP '(?:src|href)="\./static' "$INDEX_FILE" 2>/dev/null; then
        ERRORS+=("DANGER: index.html имеет relative paths (./static/) - lazy chunks сломаются! Нужно homepage:/ в package.json + rebuild")
    fi

    # Check publicPath in main.js - must be absolute
    MAIN_JS=$(find "${FRONTEND_BUILD}/static/js" -name "main.*.js" -not -name "*.map" -not -name "*.LICENSE*" 2>/dev/null | head -1)
    if [[ -n "$MAIN_JS" ]]; then
        if grep -qP '\.p="\.\/?"\s' "$MAIN_JS" 2>/dev/null; then
            ERRORS+=("DANGER: publicPath в main.js relative (./) - chunks сломаются на nested URLs!")
        fi
    fi
fi

# 7. Redis
if ! redis-cli ping > /dev/null 2>&1; then
    ERRORS+=("Redis не отвечает")
fi

# 8. Celery worker
if ! systemctl is-active --quiet celery 2>/dev/null; then
    ERRORS+=("Celery worker не запущен")
fi

# 9. Celery beat
if ! systemctl is-active --quiet celery-beat 2>/dev/null; then
    ERRORS+=("Celery beat не запущен")
fi

# 10. Redis queue size
REDIS_QUEUE_LEN=$(redis-cli llen celery 2>/dev/null || echo "0")
if [[ "$REDIS_QUEUE_LEN" -gt 100 ]] 2>/dev/null; then
    ERRORS+=("Очередь Celery: $REDIS_QUEUE_LEN задач")
fi

# 6. Внешний доступ к сайту (с retry — внешний curl может блипнуть на DNS/TLS)
SITE_CODE="000"
for _retry in 1 2 3; do
    SITE_CODE=$(curl -s -o /dev/null -w '%{http_code}' \
        --max-time 15 --connect-timeout 5 \
        "$SITE_URL" 2>/dev/null) || SITE_CODE="000"
    [[ "$SITE_CODE" == "200" ]] && break
    (( _retry < 3 )) && sleep 2
done

if [[ "$SITE_CODE" != "200" ]]; then
    # Проверяем внутренний backend прежде чем алертить
    INTERNAL_CODE=$(curl -s -o /dev/null -w '%{http_code}' \
        --max-time 10 --connect-timeout 5 \
        "http://127.0.0.1:8000/api/health/" 2>/dev/null) || INTERNAL_CODE="000"
    if [[ "$INTERNAL_CODE" == "200" ]]; then
        ERRORS+=("Внешний URL $SITE_URL: HTTP $SITE_CODE (после 3 попыток, backend OK — сетевой блип)")
    else
        ERRORS+=("Сайт $SITE_URL: HTTP $SITE_CODE, backend: HTTP $INTERNAL_CODE")
    fi
fi

# --- Результат ---

if [[ ${#ERRORS[@]} -eq 0 ]]; then
    echo "[$(timestamp)] OK — все проверки пройдены"
    # Если ранее был алерт, шлём recovery
    if [[ -f "$ALERT_COOLDOWN_FILE" ]]; then
        send_telegram "<b>Lectio Space — ВОССТАНОВЛЕН</b>

Все проверки пройдены.
$(timestamp)"
        clear_alert
    fi
    exit 0
fi

# Есть ошибки
ERROR_TEXT=""
for err in "${ERRORS[@]}"; do
    ERROR_TEXT+="  - ${err}
"
    echo "[$(timestamp)] FAIL: $err"
done

if should_alert; then
    send_telegram "<b>Lectio Space — ПРОБЛЕМА</b>

${ERROR_TEXT}
<i>$(timestamp)</i>
<i>Повторяю каждые 3 мин пока не починят</i>"
    mark_alert_sent
else
    echo "[$(timestamp)] Повтор через 3 мин"
fi

exit 1
