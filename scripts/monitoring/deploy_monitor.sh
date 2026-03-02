#!/bin/bash
# ============================================================
# Lectio Space — Deploy & Change Monitor (2026-03-02)
# ============================================================
#
# Отслеживает изменения в production-окружении и шлет алерт
# в Telegram при обнаружении:
#   1. Перезаписи frontend build (JS/CSS файлы изменились)
#   2. Перезапуска backend-сервиса
#   3. Изменения в ключевых конфигах (nginx, settings.py, urls.py)
#   4. Изменения файлов backend-кода (.py)
#   5. Новых миграций Django
#   6. Изменения в базе данных (размер резко изменился)
#
# НЕ модифицирует файлы, НЕ перезапускает сервисы — ТОЛЬКО мониторит.
#
# Кулдаун: 30 минут между алертами одного типа.
# Maintenance mode: если существует файл maintenance_mode,
#   все алерты подавляются (макс. 2 часа).
# Global rate limit: макс. 4 алерта в час.
#
# Установка:
#   scp deploy_monitor.sh tp:/opt/lectio-monitor/
#   chmod +x /opt/lectio-monitor/deploy_monitor.sh
#   Добавить в cron (каждые 5 мин):
#     */5 * * * * /opt/lectio-monitor/deploy_monitor.sh >> /var/log/lectio-monitor/deploy_monitor.log 2>&1
#
# Управление:
#   Включить maintenance mode (1 час):
#     touch /var/run/lectio-monitor/maintenance_mode
#   Выключить вручную:
#     rm -f /var/run/lectio-monitor/maintenance_mode
#
# ============================================================

set -uo pipefail

# --- Конфиг ---
CONFIG="/opt/lectio-monitor/config.env"
[[ -f "$CONFIG" ]] && source "$CONFIG"

BOT_TOKEN="${ERRORS_BOT_TOKEN:-${TELEGRAM_BOT_TOKEN:-}}"
CHAT_ID="${ERRORS_CHAT_ID:-${TELEGRAM_CHAT_ID:-}}"
PROJECT_ROOT="${PROJECT_ROOT:-/var/www/teaching_panel}"
FRONTEND_BUILD="${FRONTEND_BUILD:-/var/www/teaching_panel/frontend/build}"
LOG_DIR="${LOG_DIR:-/var/log/lectio-monitor}"
STATE_DIR="/var/run/lectio-monitor"
DB_PATH="${PROJECT_ROOT}/teaching_panel/db.sqlite3"

ALERT_COOLDOWN_SEC=1800  # 30 минут
MAINTENANCE_MAX_SEC=7200 # 2 часа — maintenance mode автоистечение
GLOBAL_MAX_ALERTS_PER_HOUR=4

mkdir -p "$LOG_DIR" "$STATE_DIR"

# --- Функции ---

timestamp() {
    date '+%Y-%m-%d %H:%M:%S'
}

log() {
    echo "[$(timestamp)] $1"
}

send_telegram() {
    local msg="$1"
    if [[ -z "$BOT_TOKEN" || -z "$CHAT_ID" ]]; then
        log "[WARN] Telegram не настроен"
        return
    fi
    curl -s --max-time 10 \
        "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -d "chat_id=${CHAT_ID}" \
        -d "text=${msg}" \
        -d "parse_mode=HTML" \
        -d "disable_web_page_preview=true" > /dev/null 2>&1 || true
}

# ============================================================
# MAINTENANCE MODE — подавляет все алерты во время деплоя
# ============================================================
MAINTENANCE_FILE="${STATE_DIR}/maintenance_mode"

is_maintenance_mode() {
    if [[ ! -f "$MAINTENANCE_FILE" ]]; then
        return 1
    fi
    local created
    created=$(stat -c %Y "$MAINTENANCE_FILE" 2>/dev/null || echo 0)
    local now
    now=$(date +%s)
    local age=$(( now - created ))
    if (( age > MAINTENANCE_MAX_SEC )); then
        # Автоистечение — удаляем файл
        rm -f "$MAINTENANCE_FILE"
        log "Maintenance mode expired (${age}s > ${MAINTENANCE_MAX_SEC}s), auto-removed"
        return 1
    fi
    return 0
}

# ============================================================
# GLOBAL RATE LIMIT — max N алертов в час
# ============================================================
GLOBAL_RATE_FILE="${STATE_DIR}/deploy_alerts_hourly"

check_global_rate() {
    local now
    now=$(date +%s)
    local hour_ago=$(( now - 3600 ))

    # Читаем timestamps отправленных алертов, отфильтровываем старые
    local count=0
    local new_entries=""
    if [[ -f "$GLOBAL_RATE_FILE" ]]; then
        while IFS= read -r ts; do
            if [[ -n "$ts" ]] && (( ts > hour_ago )); then
                new_entries+="${ts}\n"
                (( count++ ))
            fi
        done < "$GLOBAL_RATE_FILE"
    fi

    if (( count >= GLOBAL_MAX_ALERTS_PER_HOUR )); then
        return 1  # rate limit exceeded
    fi

    # Добавляем текущий timestamp
    new_entries+="${now}\n"
    echo -e "$new_entries" > "$GLOBAL_RATE_FILE"
    return 0
}

# Проверка кулдауна по типу алерта
should_alert() {
    local alert_type="$1"
    local cooldown_file="${STATE_DIR}/deploy_alert_${alert_type}"
    if [[ -f "$cooldown_file" ]]; then
        local last_alert
        last_alert=$(stat -c %Y "$cooldown_file" 2>/dev/null || echo 0)
        local now
        now=$(date +%s)
        if (( now - last_alert < ALERT_COOLDOWN_SEC )); then
            return 1
        fi
    fi
    return 0
}

mark_alert_sent() {
    local alert_type="$1"
    touch "${STATE_DIR}/deploy_alert_${alert_type}"
}

# --- Проверки ---

CHANGES=()

# ============================================================
# 1. Frontend build — отслеживание перезаписи JS/CSS бандлов
# ============================================================
FRONTEND_STATE="${STATE_DIR}/frontend_build_hash"
INDEX_FILE="${FRONTEND_BUILD}/index.html"

if [[ -f "$INDEX_FILE" ]]; then
    CURRENT_HASH=$(find "${FRONTEND_BUILD}/static" -type f \( -name "*.js" -o -name "*.css" \) -exec md5sum {} \; 2>/dev/null | sort | md5sum | cut -d' ' -f1)
    CURRENT_MAIN_JS=$(grep -oP 'src="/static/js/main\.[^"]+\.js"' "$INDEX_FILE" 2>/dev/null | head -1 || echo "unknown")

    if [[ -f "$FRONTEND_STATE" ]]; then
        PREV_HASH=$(cat "$FRONTEND_STATE" 2>/dev/null || echo "")
        if [[ "$CURRENT_HASH" != "$PREV_HASH" && -n "$PREV_HASH" ]]; then
            BUILD_SIZE=$(du -sh "${FRONTEND_BUILD}" 2>/dev/null | cut -f1)
            JS_COUNT=$(find "${FRONTEND_BUILD}/static/js" -name "*.js" 2>/dev/null | wc -l)
            CHANGES+=("FRONTEND_REBUILD|Frontend build перезаписан!\nMain JS: ${CURRENT_MAIN_JS}\nФайлов JS: ${JS_COUNT}\nРазмер build: ${BUILD_SIZE}")
        fi
    fi
    echo "$CURRENT_HASH" > "$FRONTEND_STATE"
fi

# ============================================================
# 2. Backend service — отслеживание перезапусков
# ============================================================
SERVICE_STATE="${STATE_DIR}/backend_service_start"
BACKEND_SERVICE="${BACKEND_SERVICE:-teaching_panel}"

CURRENT_START=$(systemctl show "$BACKEND_SERVICE" --property=ActiveEnterTimestamp 2>/dev/null | cut -d= -f2 || echo "")
if [[ -n "$CURRENT_START" ]]; then
    if [[ -f "$SERVICE_STATE" ]]; then
        PREV_START=$(cat "$SERVICE_STATE" 2>/dev/null || echo "")
        if [[ "$CURRENT_START" != "$PREV_START" && -n "$PREV_START" ]]; then
            CHANGES+=("SERVICE_RESTART|Backend ($BACKEND_SERVICE) перезапущен!\nНовое время старта: ${CURRENT_START}")
        fi
    fi
    echo "$CURRENT_START" > "$SERVICE_STATE"
fi

# ============================================================
# 3. Nginx config — отслеживание изменений
# ============================================================
NGINX_STATE="${STATE_DIR}/nginx_config_hash"
CURRENT_NGINX_HASH=$(find /etc/nginx/sites-enabled/ -type f -exec md5sum {} \; 2>/dev/null | sort | md5sum | cut -d' ' -f1)

if [[ -f "$NGINX_STATE" ]]; then
    PREV_NGINX_HASH=$(cat "$NGINX_STATE" 2>/dev/null || echo "")
    if [[ "$CURRENT_NGINX_HASH" != "$PREV_NGINX_HASH" && -n "$PREV_NGINX_HASH" ]]; then
        CHANGED_FILES=$(find /etc/nginx/sites-enabled/ -type f -newer "$NGINX_STATE" -printf "%f\n" 2>/dev/null | head -5 | tr '\n' ', ')
        CHANGES+=("NGINX_CONFIG|Nginx конфиг изменен!\nИзменены: ${CHANGED_FILES:-unknown}")
    fi
fi
echo "$CURRENT_NGINX_HASH" > "$NGINX_STATE"

# ============================================================
# 4. Backend Python код — отслеживание изменений
# ============================================================
BACKEND_CODE_STATE="${STATE_DIR}/backend_code_hash"
BACKEND_DIR="${PROJECT_ROOT}/teaching_panel"

CURRENT_CODE_HASH=$(find "$BACKEND_DIR" -maxdepth 3 -type f \( -name "views.py" -o -name "models.py" -o -name "serializers.py" -o -name "urls.py" -o -name "settings.py" \) -exec md5sum {} \; 2>/dev/null | sort | md5sum | cut -d' ' -f1)

if [[ -f "$BACKEND_CODE_STATE" ]]; then
    PREV_CODE_HASH=$(cat "$BACKEND_CODE_STATE" 2>/dev/null || echo "")
    if [[ "$CURRENT_CODE_HASH" != "$PREV_CODE_HASH" && -n "$PREV_CODE_HASH" ]]; then
        CHANGED_PY=$(find "$BACKEND_DIR" -maxdepth 3 -type f \( -name "views.py" -o -name "models.py" -o -name "serializers.py" -o -name "urls.py" -o -name "settings.py" \) -newer "$BACKEND_CODE_STATE" -printf "%P\n" 2>/dev/null | head -10 | tr '\n' ', ')
        CHANGES+=("BACKEND_CODE|Backend код изменен!\nФайлы: ${CHANGED_PY:-unknown}")
    fi
fi
echo "$CURRENT_CODE_HASH" > "$BACKEND_CODE_STATE"

# ============================================================
# 5. Django миграции — новые файлы миграций
# ============================================================
MIGRATIONS_STATE="${STATE_DIR}/migrations_count"
CURRENT_MIGRATIONS=$(find "$BACKEND_DIR" -path "*/migrations/*.py" -not -name "__init__.py" 2>/dev/null | wc -l)

if [[ -f "$MIGRATIONS_STATE" ]]; then
    PREV_MIGRATIONS=$(cat "$MIGRATIONS_STATE" 2>/dev/null || echo "0")
    if [[ "$CURRENT_MIGRATIONS" -gt "$PREV_MIGRATIONS" && "$PREV_MIGRATIONS" -gt 0 ]]; then
        NEW_COUNT=$((CURRENT_MIGRATIONS - PREV_MIGRATIONS))
        LATEST=$(find "$BACKEND_DIR" -path "*/migrations/*.py" -not -name "__init__.py" -printf "%T@ %P\n" 2>/dev/null | sort -rn | head -3 | awk '{print $2}' | tr '\n' ', ')
        CHANGES+=("NEW_MIGRATIONS|Новые миграции Django (+${NEW_COUNT})!\nПоследние: ${LATEST:-unknown}")
    fi
fi
echo "$CURRENT_MIGRATIONS" > "$MIGRATIONS_STATE"

# ============================================================
# 6. База данных — резкое изменение размера
# ============================================================
DB_SIZE_STATE="${STATE_DIR}/db_size"
if [[ -f "$DB_PATH" ]]; then
    CURRENT_DB_SIZE=$(stat -c %s "$DB_PATH" 2>/dev/null || echo "0")
    CURRENT_DB_SIZE_MB=$((CURRENT_DB_SIZE / 1024 / 1024))

    if [[ -f "$DB_SIZE_STATE" ]]; then
        PREV_DB_SIZE=$(cat "$DB_SIZE_STATE" 2>/dev/null || echo "0")
        if [[ "$PREV_DB_SIZE" -gt 0 ]]; then
            DIFF=$((CURRENT_DB_SIZE - PREV_DB_SIZE))
            if [[ "$DIFF" -lt 0 ]]; then DIFF=$((-DIFF)); fi
            THRESHOLD=$((PREV_DB_SIZE / 10))  # 10%
            if [[ "$DIFF" -gt "$THRESHOLD" && "$THRESHOLD" -gt 0 ]]; then
                PREV_MB=$((PREV_DB_SIZE / 1024 / 1024))
                DIRECTION="увеличился"
                [[ "$CURRENT_DB_SIZE" -lt "$PREV_DB_SIZE" ]] && DIRECTION="УМЕНЬШИЛСЯ"
                CHANGES+=("DB_SIZE|Размер БД ${DIRECTION}!\nБыло: ${PREV_MB} MB -> Стало: ${CURRENT_DB_SIZE_MB} MB")
            fi
        fi
    fi
    echo "$CURRENT_DB_SIZE" > "$DB_SIZE_STATE"
fi

# ============================================================
# 7. SSL сертификат — скорое истечение
# ============================================================
SSL_STATE="${STATE_DIR}/ssl_check_daily"
SSL_TODAY=$(date +%Y%m%d)
SSL_LAST_CHECK=$(cat "$SSL_STATE" 2>/dev/null || echo "")

if [[ "$SSL_TODAY" != "$SSL_LAST_CHECK" ]]; then
    CERT_FILE="/etc/letsencrypt/live/lectiospace.ru-0001/fullchain.pem"
    if [[ -f "$CERT_FILE" ]]; then
        EXPIRY_DATE=$(openssl x509 -enddate -noout -in "$CERT_FILE" 2>/dev/null | cut -d= -f2)
        EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s 2>/dev/null || echo "0")
        NOW_EPOCH=$(date +%s)
        DAYS_LEFT=$(( (EXPIRY_EPOCH - NOW_EPOCH) / 86400 ))

        if [[ "$DAYS_LEFT" -lt 14 ]]; then
            CHANGES+=("SSL_EXPIRY|SSL сертификат истекает через ${DAYS_LEFT} дней!\nДата: ${EXPIRY_DATE}")
        fi
    fi
    echo "$SSL_TODAY" > "$SSL_STATE"
fi

# ============================================================
# 8. Disk space — критический уровень
# ============================================================
DISK_USAGE=$(df / --output=pcent 2>/dev/null | tail -1 | tr -d ' %')
if [[ "$DISK_USAGE" -gt 85 ]]; then
    DISK_AVAIL=$(df -h / --output=avail 2>/dev/null | tail -1 | tr -d ' ')
    CHANGES+=("DISK_SPACE|Диск заполнен на ${DISK_USAGE}%!\nСвободно: ${DISK_AVAIL}")
fi

# ============================================================
# 9. Memory — критический уровень
# ============================================================
MEM_USED_PCT=$(free | awk '/Mem:/ {printf "%.0f", $3/$2*100}')
if [[ "$MEM_USED_PCT" -gt 90 ]]; then
    MEM_AVAIL=$(free -m | awk '/Mem:/ {print $7}')
    CHANGES+=("MEMORY|Память: ${MEM_USED_PCT}% используется!\nДоступно: ${MEM_AVAIL} MB")
fi

# ============================================================
# 10. Git branch check — verify new-prod is checked out
# ============================================================
GIT_DIR="/var/www/teaching_panel_git"
if [[ -d "$GIT_DIR/.git" ]]; then
    CURRENT_BRANCH=$(cd "$GIT_DIR" && git rev-parse --abbrev-ref HEAD 2>/dev/null)
    EXPECTED_BRANCH="new-prod"
    if [[ "$CURRENT_BRANCH" != "$EXPECTED_BRANCH" ]]; then
        CHANGES+=("BRANCH_SWITCH|CRITICAL: Git branch is '$CURRENT_BRANCH' instead of '$EXPECTED_BRANCH'!\nRepo: $GIT_DIR")
    fi
fi

# ============================================================
# 11. Immutable protection check — verify critical files locked
# ============================================================
IMMUTABLE_FILES=(
    "/var/www/teaching_panel/frontend/build/index.html"
    "/var/www/teaching_panel/frontend/build/favicon.svg"
    "/var/www/teaching_panel/frontend/src/App.js"
    "/var/www/teaching_panel/teaching_panel/teaching_panel/settings.py"
)

UNLOCKED_FILES=()
for f in "${IMMUTABLE_FILES[@]}"; do
    if [[ -f "$f" ]]; then
        attrs=$(lsattr "$f" 2>/dev/null | cut -d' ' -f1)
        if [[ "$attrs" != *i* ]]; then
            UNLOCKED_FILES+=("$(basename $f)")
        fi
    fi
done

if [[ ${#UNLOCKED_FILES[@]} -gt 0 ]]; then
    CHANGES+=("IMMUTABLE_REMOVED|CRITICAL: Immutable protection removed!\nFiles: ${UNLOCKED_FILES[*]}\nSomeone ran chattr -i or prod_unlock.sh")
fi

# --- Результат ---

if [[ ${#CHANGES[@]} -eq 0 ]]; then
    log "OK — изменений не обнаружено"
    exit 0
fi

# --- Maintenance mode: подавляем ВСЕ алерты ---
if is_maintenance_mode; then
    for change in "${CHANGES[@]}"; do
        ALERT_TYPE="${change%%|*}"
        ALERT_MSG="${change#*|}"
        log "CHANGE DETECTED: ${ALERT_TYPE}: ${ALERT_MSG}"
        log "Alert suppressed (MAINTENANCE MODE) for ${ALERT_TYPE}"
        # Обновляем state-файлы чтобы не ретриггерить после выхода из maintenance
        mark_alert_sent "$ALERT_TYPE"
    done
    exit 0
fi

# Отправляем алерты по каждому типу (с кулдауном + global rate limit)
for change in "${CHANGES[@]}"; do
    ALERT_TYPE="${change%%|*}"
    ALERT_MSG="${change#*|}"

    log "CHANGE DETECTED: ${ALERT_TYPE}: ${ALERT_MSG}"

    if should_alert "$ALERT_TYPE"; then
        if check_global_rate; then
            send_telegram "<b>Lectio Deploy Monitor</b>

<b>${ALERT_TYPE}</b>
$(echo -e "$ALERT_MSG")

<i>$(timestamp)</i>
<i>Server: $(hostname)</i>"
            mark_alert_sent "$ALERT_TYPE"
            log "Alert sent for ${ALERT_TYPE}"
        else
            log "Alert suppressed (GLOBAL RATE LIMIT: ${GLOBAL_MAX_ALERTS_PER_HOUR}/hour) for ${ALERT_TYPE}"
        fi
    else
        log "Alert suppressed (cooldown) for ${ALERT_TYPE}"
    fi
done

exit 0
