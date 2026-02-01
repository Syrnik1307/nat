#!/bin/bash
# ============================================================
# LECTIO UNIFIED MONITORING
# ============================================================
# Единый мониторинг с разумными порогами и агрегацией алертов
# Заменяет хаотичные проверки одним понятным потоком
# 
# Расположение: /opt/lectio-monitor/unified_monitor.sh
# Cron: */5 * * * * /opt/lectio-monitor/unified_monitor.sh
# ============================================================

set -u

# Загружаем конфигурацию
CONFIG_FILE="/opt/lectio-monitor/config.env"
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
fi

# ==================== КОНФИГУРАЦИЯ ====================
SITE_URL="${SITE_URL:-https://lectio.tw1.ru}"
API_URL="${API_URL:-https://lectio.tw1.ru/api/health/}"
BACKEND_SERVICE="${BACKEND_SERVICE:-teaching_panel}"
LOG_FILE="/var/log/lectio-monitor/unified.log"
STATE_DIR="/var/run/lectio-monitor"

# Telegram
ERRORS_BOT_TOKEN="${ERRORS_BOT_TOKEN:-${TELEGRAM_BOT_TOKEN:-}}"
ERRORS_CHAT_ID="${ERRORS_CHAT_ID:-${TELEGRAM_CHAT_ID:-}}"

# ==================== ПОРОГИ (РАЗУМНЫЕ!) ====================
# Память: алерт только при КРИТИЧНО низких значениях
# VPS с 2GB RAM нормально работает с 200-400MB свободной памяти
MEMORY_WARN_MB=150       # Предупреждение (не шлём в Telegram)
MEMORY_CRITICAL_MB=100   # Критично - шлём алерт
SWAP_CRITICAL_MB=1500    # Swap > 1.5GB = проблема

# Диск
DISK_WARN_PERCENT=85     # 85% занято = предупреждение
DISK_CRITICAL_PERCENT=95 # 95% = критично

# Latency
LATENCY_WARN_SEC=3       # Медленно
LATENCY_CRITICAL_SEC=10  # Очень медленно

# Anti-spam: один алерт на проблему раз в 2 часа
ALERT_COOLDOWN_SEC=7200

mkdir -p "$STATE_DIR" "$(dirname "$LOG_FILE")"

# ==================== ЛОГИРОВАНИЕ ====================
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# ==================== ANTI-SPAM ====================
should_alert() {
    local alert_type="$1"
    local state_file="$STATE_DIR/alert_${alert_type}"
    local now=$(date +%s)
    
    if [[ -f "$state_file" ]]; then
        local last_alert=$(cat "$state_file" 2>/dev/null || echo 0)
        local elapsed=$((now - last_alert))
        if [[ $elapsed -lt $ALERT_COOLDOWN_SEC ]]; then
            return 1  # Не алертить
        fi
    fi
    
    echo "$now" > "$state_file"
    return 0  # Алертить
}

# ==================== TELEGRAM ====================
send_telegram() {
    local message="$1"
    local priority="${2:-normal}"
    
    # Проверяем mute
    local mute_file="$STATE_DIR/mute_until"
    if [[ -f "$mute_file" ]]; then
        local until=$(cat "$mute_file" 2>/dev/null || echo 0)
        local now=$(date +%s)
        if [[ $now -lt $until ]]; then
            log "Алерты заглушены до $(date -d "@$until" '+%H:%M')"
            return 0
        fi
    fi
    
    if [[ -z "$ERRORS_BOT_TOKEN" ]] || [[ -z "$ERRORS_CHAT_ID" ]]; then
        return 0
    fi
    
    local emoji="INFO"
    case "$priority" in
        critical) emoji="CRITICAL" ;;
        warn)     emoji="WARNING" ;;
    esac
    
    local full_message="LECTIO $emoji

$message

$(date '+%Y-%m-%d %H:%M')"

    curl -s -X POST "https://api.telegram.org/bot${ERRORS_BOT_TOKEN}/sendMessage" \
        -d "chat_id=${ERRORS_CHAT_ID}" \
        -d "text=${full_message}" \
        > /dev/null 2>&1
}

# ==================== ПРОВЕРКИ ====================

# 1. Сайт доступен?
check_site_available() {
    local http_code
    local latency
    local result
    
    result=$(curl -s -o /dev/null -w "%{http_code}:%{time_total}" \
        --max-time 15 --connect-timeout 5 "$SITE_URL" 2>/dev/null) || result="000:0"
    
    http_code="${result%%:*}"
    latency="${result##*:}"
    
    if [[ "$http_code" != "200" ]]; then
        echo "CRITICAL:Сайт недоступен (HTTP $http_code)"
        return
    fi
    
    # Проверяем latency только если сайт доступен
    local latency_int=${latency%.*}
    if [[ $latency_int -ge $LATENCY_CRITICAL_SEC ]]; then
        echo "WARN:Сайт медленный (${latency}s)"
        return
    fi
    
    echo "OK"
}

# 2. Backend API работает?
check_api_health() {
    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" \
        --max-time 10 "$API_URL" 2>/dev/null) || http_code="000"
    
    if [[ "$http_code" != "200" ]]; then
        echo "CRITICAL:API недоступен (HTTP $http_code)"
        return
    fi
    
    echo "OK"
}

# 3. Сервисы запущены?
check_services() {
    local issues=()
    
    if ! systemctl is-active --quiet "$BACKEND_SERVICE"; then
        issues+=("Django остановлен")
    fi
    
    if ! systemctl is-active --quiet nginx; then
        issues+=("Nginx остановлен")
    fi
    
    if [[ ${#issues[@]} -gt 0 ]]; then
        echo "CRITICAL:$(IFS=', '; echo "${issues[*]}")"
        return
    fi
    
    echo "OK"
}

# 4. Память (только критичные случаи!)
check_memory() {
    local available=$(free -m | awk '/^Mem:/ {print $7}')
    local swap_used=$(free -m | awk '/^Swap:/ {print $3}')
    
    # Критично низкая память
    if [[ $available -lt $MEMORY_CRITICAL_MB ]]; then
        echo "CRITICAL:Критически мало памяти (${available}MB)"
        return
    fi
    
    # Критичный swap
    if [[ $swap_used -gt $SWAP_CRITICAL_MB ]]; then
        echo "CRITICAL:Большой swap (${swap_used}MB)"
        return
    fi
    
    # Просто мало памяти - логируем но не алертим
    if [[ $available -lt $MEMORY_WARN_MB ]]; then
        log "INFO: Мало памяти (${available}MB) - пока не критично"
    fi
    
    echo "OK"
}

# 5. Диск
check_disk() {
    local usage=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')
    
    if [[ $usage -ge $DISK_CRITICAL_PERCENT ]]; then
        echo "CRITICAL:Диск почти полон (${usage}%)"
        return
    fi
    
    if [[ $usage -ge $DISK_WARN_PERCENT ]]; then
        echo "WARN:Диск заполняется (${usage}%)"
        return
    fi
    
    echo "OK"
}

# 6. Gunicorn workers
check_workers() {
    local count=$(pgrep -c -f "gunicorn.*teaching_panel" 2>/dev/null || echo 0)
    
    if [[ $count -lt 2 ]]; then
        echo "CRITICAL:Мало gunicorn workers ($count)"
        return
    fi
    
    echo "OK"
}

# ==================== AUTO-RECOVERY ====================
# Попытка автоматического восстановления при известных проблемах
try_auto_recovery() {
    local issue="$1"
    local recovered=0
    
    log "AUTO-RECOVERY: Попытка исправить: $issue"
    
    # 403/Permission denied - исправляем права на frontend
    if [[ "$issue" == *"HTTP 403"* ]] || [[ "$issue" == *"permission"* ]]; then
        log "AUTO-RECOVERY: Исправляю права на frontend..."
        chown -R www-data:www-data /var/www/teaching_panel/frontend/build 2>/dev/null
        chmod -R 755 /var/www/teaching_panel/frontend/build 2>/dev/null
        recovered=1
    fi
    
    # Django остановлен - рестарт
    if [[ "$issue" == *"Django остановлен"* ]]; then
        log "AUTO-RECOVERY: Перезапускаю teaching_panel..."
        systemctl restart teaching_panel 2>/dev/null
        sleep 3
        if systemctl is-active --quiet teaching_panel; then
            recovered=1
        fi
    fi
    
    # Nginx остановлен - рестарт
    if [[ "$issue" == *"Nginx остановлен"* ]]; then
        log "AUTO-RECOVERY: Перезапускаю nginx..."
        systemctl restart nginx 2>/dev/null
        sleep 2
        if systemctl is-active --quiet nginx; then
            recovered=1
        fi
    fi
    
    # Мало gunicorn workers - рестарт Django
    if [[ "$issue" == *"gunicorn workers"* ]]; then
        log "AUTO-RECOVERY: Перезапускаю teaching_panel (мало workers)..."
        systemctl restart teaching_panel 2>/dev/null
        sleep 5
        local count=$(pgrep -c -f "gunicorn.*teaching_panel" 2>/dev/null || echo 0)
        if [[ $count -ge 2 ]]; then
            recovered=1
        fi
    fi
    
    # API недоступен (502/503/504) - рестарт Django
    if [[ "$issue" == *"API недоступен"* ]] && [[ "$issue" =~ HTTP\ (502|503|504) ]]; then
        log "AUTO-RECOVERY: Перезапускаю teaching_panel (API $BASH_REMATCH)..."
        systemctl restart teaching_panel 2>/dev/null
        sleep 5
        recovered=1
    fi
    
    if [[ $recovered -eq 1 ]]; then
        log "AUTO-RECOVERY: Действие выполнено, проверяю результат..."
        return 0
    fi
    
    return 1
}

# ==================== MAIN ====================
main() {
    log "=== Unified Monitor START ==="
    
    local critical_issues=()
    local warnings=()
    local recovery_attempted=0
    
    # Запускаем все проверки
    local result
    
    result=$(check_site_available)
    if [[ "$result" == CRITICAL:* ]]; then
        critical_issues+=("${result#CRITICAL:}")
    elif [[ "$result" == WARN:* ]]; then
        warnings+=("${result#WARN:}")
    fi
    
    result=$(check_api_health)
    if [[ "$result" == CRITICAL:* ]]; then
        critical_issues+=("${result#CRITICAL:}")
    fi
    
    result=$(check_services)
    if [[ "$result" == CRITICAL:* ]]; then
        critical_issues+=("${result#CRITICAL:}")
    fi
    
    result=$(check_memory)
    if [[ "$result" == CRITICAL:* ]]; then
        critical_issues+=("${result#CRITICAL:}")
    fi
    
    result=$(check_disk)
    if [[ "$result" == CRITICAL:* ]]; then
        critical_issues+=("${result#CRITICAL:}")
    elif [[ "$result" == WARN:* ]]; then
        warnings+=("${result#WARN:}")
    fi
    
    result=$(check_workers)
    if [[ "$result" == CRITICAL:* ]]; then
        critical_issues+=("${result#CRITICAL:}")
    fi
    
    # ==================== AUTO-RECOVERY ====================
    # Пытаемся автоматически исправить критические проблемы
    if [[ ${#critical_issues[@]} -gt 0 ]]; then
        local recovery_count=0
        for issue in "${critical_issues[@]}"; do
            if try_auto_recovery "$issue"; then
                ((recovery_count++))
            fi
        done
        
        # Если были попытки восстановления - перепроверяем
        if [[ $recovery_count -gt 0 ]]; then
            log "AUTO-RECOVERY: Выполнено $recovery_count действий, перепроверяю..."
            sleep 3
            
            # Перезапускаем проверки
            critical_issues=()
            warnings=()
            
            result=$(check_site_available)
            if [[ "$result" == CRITICAL:* ]]; then
                critical_issues+=("${result#CRITICAL:}")
            fi
            
            result=$(check_api_health)
            if [[ "$result" == CRITICAL:* ]]; then
                critical_issues+=("${result#CRITICAL:}")
            fi
            
            result=$(check_services)
            if [[ "$result" == CRITICAL:* ]]; then
                critical_issues+=("${result#CRITICAL:}")
            fi
            
            result=$(check_workers)
            if [[ "$result" == CRITICAL:* ]]; then
                critical_issues+=("${result#CRITICAL:}")
            fi
            
            if [[ ${#critical_issues[@]} -eq 0 ]]; then
                log "AUTO-RECOVERY: Успешно! Все проблемы устранены."
                send_telegram "AUTO-RECOVERY успешно восстановил сайт" "normal"
                log "=== Unified Monitor END ==="
                return 0
            else
                log "AUTO-RECOVERY: Не все проблемы устранены: ${critical_issues[*]}"
            fi
        fi
    fi
    
    # ==================== ОТПРАВКА АЛЕРТОВ ====================
    
    if [[ ${#critical_issues[@]} -gt 0 ]]; then
        log "CRITICAL: ${critical_issues[*]}"
        
        # Алерт с anti-spam
        if should_alert "critical"; then
            local msg=""
            for issue in "${critical_issues[@]}"; do
                msg+="• $issue
"
            done
            send_telegram "$msg" "critical"
        fi
    elif [[ ${#warnings[@]} -gt 0 ]]; then
        log "WARN: ${warnings[*]}"
        # Warnings НЕ отправляем в Telegram - только логируем
    else
        log "OK: Все проверки пройдены"
    fi
    
    log "=== Unified Monitor END ==="
}

main "$@"
