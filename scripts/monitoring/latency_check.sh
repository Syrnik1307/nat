#!/bin/bash
# ============================================================
# LECTIO LATENCY CHECK - Мониторинг времени отклика
# ============================================================
# Проверяет response time критических endpoints.
# Алерт если время отклика > 3 сек.
#
# Запуск: каждые 5 минут вместе со smoke_check
# Расположение: /opt/lectio-monitor/latency_check.sh
# ============================================================

set -uo pipefail

CONFIG_FILE="/opt/lectio-monitor/config.env"
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
fi

SITE_URL="${SITE_URL:-https://lectiospace.ru}"
LOG_FILE="/var/log/lectio-monitor/latency.log"
STATE_FILE="/var/run/lectio-monitor/latency_state"

ERRORS_BOT_TOKEN="${ERRORS_BOT_TOKEN:-${TELEGRAM_BOT_TOKEN:-}}"
ERRORS_CHAT_ID="${ERRORS_CHAT_ID:-${TELEGRAM_CHAT_ID:-}}"

# Пороги (в секундах)
WARN_THRESHOLD=2.0
CRITICAL_THRESHOLD=5.0

# Антиспам: алерт раз в 15 минут
ALERT_COOLDOWN=900

mkdir -p "$(dirname "$LOG_FILE")" "$(dirname "$STATE_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
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
    
    # Антиспам
    if [[ -f "$STATE_FILE" ]]; then
        local last_alert=$(cat "$STATE_FILE" 2>/dev/null || echo 0)
        local now=$(date +%s)
        if [[ $((now - last_alert)) -lt $ALERT_COOLDOWN ]]; then
            return 0
        fi
    fi
    echo $(date +%s) > "$STATE_FILE"
    
    local emoji="⏱️"
    [[ "$priority" == "critical" ]] && emoji="🚨"
    [[ "$priority" == "high" ]] && emoji="⚠️"
    
    curl -s -X POST "https://api.telegram.org/bot${ERRORS_BOT_TOKEN}/sendMessage" \
        -d "chat_id=${ERRORS_CHAT_ID}" \
        -d "text=${emoji} LECTIO LATENCY ALERT

$message

🕐 $(date '+%Y-%m-%d %H:%M:%S')" \
        > /dev/null 2>&1 || true
}

# Измеряем latency endpoint
measure_latency() {
    local url="$1"
    local name="$2"
    
    local result
    result=$(curl -s -o /dev/null -w "%{http_code}|%{time_total}|%{time_connect}|%{time_starttransfer}" \
        --max-time 30 \
        --connect-timeout 10 \
        "$url" 2>/dev/null) || result="000|0|0|0"
    
    local http_code=$(echo "$result" | cut -d'|' -f1)
    local time_total=$(echo "$result" | cut -d'|' -f2)
    local time_connect=$(echo "$result" | cut -d'|' -f3)
    local time_ttfb=$(echo "$result" | cut -d'|' -f4)  # Time To First Byte
    
    echo "$name|$http_code|$time_total|$time_connect|$time_ttfb"
}

# ==================== MAIN ====================

main() {
    local slow_endpoints=()
    local critical_endpoints=()
    
    # Список endpoints для проверки
    declare -A endpoints=(
        ["Homepage"]="${SITE_URL}/"
        ["Health API"]="${SITE_URL}/api/health/"
        ["Static JS"]="${SITE_URL}/static/js/"
    )
    
    local all_metrics=""
    
    for name in "${!endpoints[@]}"; do
        local url="${endpoints[$name]}"
        local result=$(measure_latency "$url" "$name")
        
        local endpoint_name=$(echo "$result" | cut -d'|' -f1)
        local http_code=$(echo "$result" | cut -d'|' -f2)
        local time_total=$(echo "$result" | cut -d'|' -f3)
        local time_ttfb=$(echo "$result" | cut -d'|' -f5)
        
        all_metrics+="$endpoint_name: ${time_total}s (TTFB: ${time_ttfb}s) HTTP:$http_code\n"
        log "$endpoint_name: total=${time_total}s ttfb=${time_ttfb}s http=$http_code"
        
        # Проверяем пороги
        if [[ "$http_code" == "200" || "$http_code" == "301" || "$http_code" == "302" ]]; then
            # Сравниваем с порогами (используем bc для float)
            local is_critical=$(echo "$time_total > $CRITICAL_THRESHOLD" | bc -l 2>/dev/null || echo 0)
            local is_slow=$(echo "$time_total > $WARN_THRESHOLD" | bc -l 2>/dev/null || echo 0)
            
            if [[ "$is_critical" == "1" ]]; then
                critical_endpoints+=("$endpoint_name: ${time_total}s")
            elif [[ "$is_slow" == "1" ]]; then
                slow_endpoints+=("$endpoint_name: ${time_total}s")
            fi
        fi
    done
    
    # ==================== REPORT ====================
    
    if [[ ${#critical_endpoints[@]} -gt 0 ]]; then
        local crit_text=$(printf '• %s\n' "${critical_endpoints[@]}")
        send_telegram "КРИТИЧЕСКИ МЕДЛЕННЫЕ ОТВЕТЫ (>${CRITICAL_THRESHOLD}s):

$crit_text

Все метрики:
$(echo -e "$all_metrics")" "critical"
    elif [[ ${#slow_endpoints[@]} -gt 0 ]]; then
        local slow_text=$(printf '• %s\n' "${slow_endpoints[@]}")
        send_telegram "Медленные ответы (>${WARN_THRESHOLD}s):

$slow_text" "high"
    fi
}

main "$@"
