#!/bin/bash
# ============================================================
# LECTIO INTEGRATION CHECK - GDrive, Zoom, External APIs
# ============================================================
# Проверяет работоспособность внешних интеграций:
# - Google Drive API (токен, доступ к папке)
# - Zoom API (OAuth токен)
# - T-Bank/YooKassa API availability
#
# Запуск: каждые 6 часов (0 */6 * * *)
# Расположение: /opt/lectio-monitor/integration_check.sh
# ============================================================

set -uo pipefail

CONFIG_FILE="/opt/lectio-monitor/config.env"
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
fi

PROJECT_ROOT="${PROJECT_ROOT:-/var/www/teaching_panel}"
LOG_FILE="/var/log/lectio-monitor/integration_check.log"
PYTHON="${PROJECT_ROOT}/venv/bin/python"
MANAGE="${PROJECT_ROOT}/teaching_panel/manage.py"

ERRORS_BOT_TOKEN="${ERRORS_BOT_TOKEN:-${TELEGRAM_BOT_TOKEN:-}}"
ERRORS_CHAT_ID="${ERRORS_CHAT_ID:-${TELEGRAM_CHAT_ID:-}}"

mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$1] $2" | tee -a "$LOG_FILE"
}

send_telegram() {
    local message="$1"
    local priority="${2:-normal}"

    if [[ "${ALERTS_MUTED:-0}" == "1" ]]; then
        return 0
    fi

    local mute_file="${ALERTS_MUTE_FILE:-/var/run/lectio-monitor/mute_until}"
    if [[ -f "$mute_file" ]]; then
        local until
        until=$(cat "$mute_file" 2>/dev/null || echo "")
        local now
        now=$(date +%s)
        if [[ "$until" =~ ^[0-9]+$ ]] && [[ "$now" -lt "$until" ]]; then
            return 0
        fi
    fi
    
    if [[ -z "$ERRORS_BOT_TOKEN" ]] || [[ -z "$ERRORS_CHAT_ID" ]]; then
        return 0
    fi
    
    local emoji="ℹ️"
    [[ "$priority" == "critical" ]] && emoji="🚨"
    [[ "$priority" == "high" ]] && emoji="⚠️"
    
    curl -s -X POST "https://api.telegram.org/bot${ERRORS_BOT_TOKEN}/sendMessage" \
        -d "chat_id=${ERRORS_CHAT_ID}" \
        -d "text=${emoji} LECTIO INTEGRATION CHECK

$message

🕐 $(date '+%Y-%m-%d %H:%M:%S')" \
        > /dev/null 2>&1 || true
}

# ==================== ПРОВЕРКИ ====================

# 1. Google Drive API
check_gdrive() {
    log "INFO" "Checking Google Drive..."
    
    cd "${PROJECT_ROOT}/teaching_panel"
    
    local result
    result=$($PYTHON -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
import django
django.setup()

try:
    from schedule.gdrive_utils import get_gdrive_manager
    manager = get_gdrive_manager()
    
    # Попытка получить список файлов в root папке
    files = manager.service.files().list(
        q=\"'\" + manager.root_folder_id + \"' in parents\",
        pageSize=1,
        fields='files(id, name)'
    ).execute()
    
    print('OK:GDrive connected, root folder accessible')
except Exception as e:
    print(f'FAIL:GDrive error: {str(e)[:100]}')
" 2>&1 | tail -1)
    
    echo "$result"
    log "INFO" "GDrive: $result"
}

# 2. Zoom API (OAuth token refresh)
check_zoom() {
    log "INFO" "Checking Zoom API..."
    
    cd "${PROJECT_ROOT}/teaching_panel"
    
    local result
    result=$($PYTHON -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
import django
django.setup()

try:
    from schedule.zoom_utils import get_zoom_access_token
    token = get_zoom_access_token()
    
    if token and len(token) > 20:
        print('OK:Zoom OAuth token obtained')
    else:
        print('FAIL:Zoom token is empty or invalid')
except Exception as e:
    print(f'FAIL:Zoom error: {str(e)[:100]}')
" 2>&1 | tail -1)
    
    echo "$result"
    log "INFO" "Zoom: $result"
}

# 3. T-Bank API availability
check_tbank() {
    log "INFO" "Checking T-Bank API..."
    
    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" \
        --max-time 10 \
        "https://securepay.tinkoff.ru/v2/Init" 2>/dev/null) || http_code="000"
    
    # T-Bank возвращает 405 на GET (ожидает POST), но это значит что API доступен
    if [[ "$http_code" == "405" || "$http_code" == "200" || "$http_code" == "400" ]]; then
        echo "OK:T-Bank API reachable (HTTP $http_code)"
    else
        echo "FAIL:T-Bank API unreachable (HTTP $http_code)"
    fi
}

# 4. YooKassa API availability  
check_yookassa() {
    log "INFO" "Checking YooKassa API..."
    
    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" \
        --max-time 10 \
        "https://api.yookassa.ru/v3/payments" 2>/dev/null) || http_code="000"
    
    # YooKassa возвращает 401 без auth, но это значит что API доступен
    if [[ "$http_code" == "401" || "$http_code" == "200" ]]; then
        echo "OK:YooKassa API reachable (HTTP $http_code)"
    else
        echo "FAIL:YooKassa API unreachable (HTTP $http_code)"
    fi
}

# 5. Telegram Bot API (проверка что бот работает)
check_telegram_bot() {
    log "INFO" "Checking Telegram Bot..."
    
    if [[ -z "$ERRORS_BOT_TOKEN" ]]; then
        echo "SKIP:Telegram bot not configured"
        return 0
    fi
    
    local response
    response=$(curl -s --max-time 10 \
        "https://api.telegram.org/bot${ERRORS_BOT_TOKEN}/getMe" 2>/dev/null)
    
    if echo "$response" | grep -q '"ok":true'; then
        local bot_name=$(echo "$response" | grep -o '"username":"[^"]*"' | cut -d'"' -f4)
        echo "OK:Telegram bot @$bot_name working"
    else
        echo "FAIL:Telegram bot not responding"
    fi
}

# ==================== MAIN ====================

main() {
    local issues=()
    local warnings=()
    
    log "INFO" "=== Integration Check START ==="
    
    # GDrive
    local res=$(check_gdrive)
    [[ "$res" == FAIL:* ]] && issues+=("GDrive: ${res#FAIL:}")
    
    # Zoom
    res=$(check_zoom)
    [[ "$res" == FAIL:* ]] && issues+=("Zoom: ${res#FAIL:}")
    
    # T-Bank
    res=$(check_tbank)
    log "INFO" "T-Bank: $res"
    [[ "$res" == FAIL:* ]] && warnings+=("T-Bank: ${res#FAIL:}")
    
    # YooKassa
    res=$(check_yookassa)
    log "INFO" "YooKassa: $res"
    [[ "$res" == FAIL:* ]] && warnings+=("YooKassa: ${res#FAIL:}")
    
    # Telegram
    res=$(check_telegram_bot)
    log "INFO" "Telegram: $res"
    [[ "$res" == FAIL:* ]] && issues+=("Telegram: ${res#FAIL:}")
    
    # ==================== REPORT ====================
    
    if [[ ${#issues[@]} -gt 0 ]]; then
        local issue_text=$(printf '• %s\n' "${issues[@]}")
        log "ERROR" "Integration issues found!"
        send_telegram "ПРОБЛЕМЫ С ИНТЕГРАЦИЯМИ:

$issue_text" "critical"
    elif [[ ${#warnings[@]} -gt 0 ]]; then
        local warn_text=$(printf '• %s\n' "${warnings[@]}")
        log "WARN" "Integration warnings"
        send_telegram "Предупреждения интеграций:

$warn_text" "high"
    else
        log "SUCCESS" "All integrations OK"
    fi
}

main "$@"
