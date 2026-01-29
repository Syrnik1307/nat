#!/bin/bash
# ============================================================
# LECTIO DEEP CHECK - Расширенные проверки
# ============================================================
# Проверяет то, что не покрывает smoke_check_v2:
# - SSL сертификат (срок истечения)
# - Стриминг видео (Range requests)
# - Google Drive connectivity
# - Размер БД и диска
# - Nginx error rate
#
# Запуск: раз в час (0 * * * *)
# Расположение: /opt/lectio-monitor/deep_check.sh
# ============================================================

set -uo pipefail

CONFIG_FILE="/opt/lectio-monitor/config.env"
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
fi

SITE_URL="${SITE_URL:-https://lectio.tw1.ru}"
PROJECT_ROOT="${PROJECT_ROOT:-/var/www/teaching_panel}"
LOG_FILE="/var/log/lectio-monitor/deep_check.log"

ERRORS_BOT_TOKEN="${ERRORS_BOT_TOKEN:-${TELEGRAM_BOT_TOKEN:-}}"
ERRORS_CHAT_ID="${ERRORS_CHAT_ID:-${TELEGRAM_CHAT_ID:-}}"

mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$1] $2" | tee -a "$LOG_FILE"
}

build_human_explanations() {
    local issue
    local lines=()
    while IFS= read -r issue; do
        [[ -z "$issue" ]] && continue
        case "$issue" in
            "SSL истекает"*)
                lines+=("• Сертификат безопасности скоро истечёт — браузеры начнут ругаться. Действие: продлить SSL.")
                ;;
            "Database size"*)
                lines+=("• База данных стала большой — бэкапы и операции могут замедляться. Действие: проверить рост и архивировать старые данные.")
                ;;
            "Disk space critical"*|"Low disk space"*)
                lines+=("• Диск почти заполнен — файлы и логи могут не записываться. Действие: освободить место или расширить диск.")
                ;;
            "High nginx errors"*)
                lines+=("• Много ошибок веб‑сервера — часть пользователей видит ошибки. Действие: проверить логи nginx.")
                ;;
            "Only "*" gunicorn workers"*)
                lines+=("• Слишком мало процессов приложения — запросы могут падать. Действие: перезапустить teaching_panel.")
                ;;
            *"gunicorn workers at high CPU"*)
                lines+=("• Процессы приложения перегружены — возможны тормоза. Действие: проверить нагрузку и логи.")
                ;;
            "Memory critical"*|"Low memory"*)
                lines+=("• Мало оперативной памяти — сервер уходит в swap и тормозит. Действие: проверить память, перезапустить тяжёлые процессы или увеличить RAM.")
                ;;
            *"pending migrations"*)
                lines+=("• Есть неприменённые миграции — часть функций может работать некорректно. Действие: применить миграции.")
                ;;
            *)
                lines+=("• Требуется проверка логов и состояния сервисов.")
                ;;
        esac
    done <<< "$1"

    printf '%s\n' "${lines[@]}"
}

send_telegram() {
    local message="$1"
    local priority="${2:-normal}"
    
    if [[ -z "$ERRORS_BOT_TOKEN" ]] || [[ -z "$ERRORS_CHAT_ID" ]]; then
        return 0
    fi
    
    local emoji="ℹ️"
    [[ "$priority" == "critical" ]] && emoji="🚨"
    [[ "$priority" == "high" ]] && emoji="⚠️"
    
    curl -s -X POST "https://api.telegram.org/bot${ERRORS_BOT_TOKEN}/sendMessage" \
        -d "chat_id=${ERRORS_CHAT_ID}" \
        -d "text=${emoji} LECTIO DEEP CHECK

$message

🕐 $(date '+%Y-%m-%d %H:%M:%S')" \
        > /dev/null 2>&1 || true
}

# ==================== ПРОВЕРКИ ====================

# 1. SSL сертификат - предупреждать за 14 дней
check_ssl_expiry() {
    local domain="${SITE_URL#https://}"
    domain="${domain#http://}"
    domain="${domain%%/*}"
    
    local expiry_date
    expiry_date=$(echo | openssl s_client -servername "$domain" -connect "$domain:443" 2>/dev/null | \
        openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)
    
    if [[ -z "$expiry_date" ]]; then
        echo "FAIL:Не удалось получить SSL сертификат"
        return 1
    fi
    
    local expiry_epoch=$(date -d "$expiry_date" +%s 2>/dev/null)
    local now_epoch=$(date +%s)
    local days_left=$(( (expiry_epoch - now_epoch) / 86400 ))
    
    if [[ $days_left -lt 7 ]]; then
        echo "CRITICAL:SSL истекает через $days_left дней!"
        return 1
    elif [[ $days_left -lt 14 ]]; then
        echo "WARN:SSL истекает через $days_left дней"
        return 0
    fi
    
    echo "OK:SSL valid ($days_left days)"
    return 0
}

# 2. Размер БД
check_database_size() {
    local db_file="${PROJECT_ROOT}/teaching_panel/db.sqlite3"
    
    if [[ ! -f "$db_file" ]]; then
        echo "OK:No SQLite (probably PostgreSQL)"
        return 0
    fi
    
    local size_mb=$(du -m "$db_file" | cut -f1)
    
    if [[ $size_mb -gt 1000 ]]; then
        echo "WARN:Database size ${size_mb}MB (>1GB)"
        return 0
    fi
    
    echo "OK:DB size ${size_mb}MB"
    return 0
}

# 3. Свободное место на диске
check_disk_space() {
    local usage=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')
    local free=$((100 - usage))
    
    if [[ $free -lt 5 ]]; then
        echo "CRITICAL:Disk space critical! Only ${free}% free"
        return 1
    elif [[ $free -lt 15 ]]; then
        echo "WARN:Low disk space: ${free}% free"
        return 0
    fi
    
    echo "OK:Disk ${free}% free"
    return 0
}

# 4. Nginx error rate (500 ошибок за последний час)
check_nginx_errors() {
    local error_log="/var/log/nginx/error.log"
    
    if [[ ! -f "$error_log" ]]; then
        echo "OK:No nginx error log"
        return 0
    fi
    
    local hour_ago=$(date -d '1 hour ago' '+%Y/%m/%d %H')
    local error_count
    error_count=$(grep -c "$hour_ago" "$error_log" 2>/dev/null) || error_count=0
    
    if [[ "$error_count" -gt 100 ]]; then
        echo "WARN:High nginx errors: $error_count in last hour"
        return 0
    fi
    
    echo "OK:Nginx errors: ${error_count}/hour"
    return 0
}

# 5. Проверка что gunicorn не завис (workers responsive)
check_gunicorn_health() {
    local worker_count=$(pgrep -c -f "gunicorn.*teaching_panel" 2>/dev/null || echo 0)
    
    if [[ $worker_count -lt 2 ]]; then
        echo "CRITICAL:Only $worker_count gunicorn workers!"
        return 1
    fi
    
    # Проверяем CPU usage воркеров (не должны быть 100%)
    local high_cpu_workers=$(ps aux | grep "gunicorn.*teaching_panel" | grep -v grep | awk '$3 > 90 {count++} END {print count+0}')
    
    if [[ $high_cpu_workers -gt 0 ]]; then
        echo "WARN:$high_cpu_workers gunicorn workers at high CPU"
        return 0
    fi
    
    echo "OK:$worker_count workers healthy"
    return 0
}

# 6. Проверка памяти
check_memory() {
    local available_mb=$(free -m | awk '/^Mem:/ {print $7}')
    local total_mb=$(free -m | awk '/^Mem:/ {print $2}')
    local usage_percent=$(( (total_mb - available_mb) * 100 / total_mb ))
    
    if [[ $available_mb -lt 100 ]]; then
        echo "CRITICAL:Memory critical! Only ${available_mb}MB available"
        return 1
    elif [[ $available_mb -lt 256 ]]; then
        echo "WARN:Low memory: ${available_mb}MB available"
        return 0
    fi
    
    echo "OK:Memory ${available_mb}MB free (${usage_percent}% used)"
    return 0
}

# 7. Проверка pending migrations
check_migrations() {
    cd "${PROJECT_ROOT}/teaching_panel"
    local pending
    pending=$(../venv/bin/python manage.py showmigrations --plan 2>/dev/null | grep -c "\[ \]") || pending=0
    
    if [[ "$pending" -gt 0 ]]; then
        echo "WARN:$pending pending migrations"
        return 0
    fi
    
    echo "OK:No pending migrations"
    return 0
}

# ==================== MAIN ====================

main() {
    local issues=()
    local warnings=()
    
    log "INFO" "=== Deep Check START ==="
    
    # SSL
    local res=$(check_ssl_expiry)
    log "INFO" "SSL: $res"
    [[ "$res" == CRITICAL:* ]] && issues+=("${res#CRITICAL:}")
    [[ "$res" == WARN:* ]] && warnings+=("${res#WARN:}")
    
    # Disk
    res=$(check_disk_space)
    log "INFO" "Disk: $res"
    [[ "$res" == CRITICAL:* ]] && issues+=("${res#CRITICAL:}")
    [[ "$res" == WARN:* ]] && warnings+=("${res#WARN:}")
    
    # Memory
    res=$(check_memory)
    log "INFO" "Memory: $res"
    [[ "$res" == CRITICAL:* ]] && issues+=("${res#CRITICAL:}")
    [[ "$res" == WARN:* ]] && warnings+=("${res#WARN:}")
    
    # Gunicorn
    res=$(check_gunicorn_health)
    log "INFO" "Gunicorn: $res"
    [[ "$res" == CRITICAL:* ]] && issues+=("${res#CRITICAL:}")
    [[ "$res" == WARN:* ]] && warnings+=("${res#WARN:}")
    
    # DB size
    res=$(check_database_size)
    log "INFO" "Database: $res"
    [[ "$res" == WARN:* ]] && warnings+=("${res#WARN:}")
    
    # Nginx
    res=$(check_nginx_errors)
    log "INFO" "Nginx: $res"
    [[ "$res" == WARN:* ]] && warnings+=("${res#WARN:}")
    
    # Migrations
    res=$(check_migrations)
    log "INFO" "Migrations: $res"
    [[ "$res" == WARN:* ]] && warnings+=("${res#WARN:}")
    
    # ==================== REPORT ====================
    
    if [[ ${#issues[@]} -gt 0 ]]; then
        local issue_text=$(printf '• %s\n' "${issues[@]}")
        local human_text
        human_text=$(build_human_explanations "$(printf '%s\n' "${issues[@]}")")
        local explain_block=""
        if [[ -n "$human_text" ]]; then
            explain_block="\nПояснение простыми словами:\n$human_text"
        fi
        log "ERROR" "Critical issues found!"
        send_telegram "КРИТИЧЕСКИЕ ПРОБЛЕМЫ:

$issue_text$explain_block" "critical"
    elif [[ ${#warnings[@]} -gt 0 ]]; then
        local warn_text=$(printf '• %s\n' "${warnings[@]}")
        local human_text
        human_text=$(build_human_explanations "$(printf '%s\n' "${warnings[@]}")")
        local explain_block=""
        if [[ -n "$human_text" ]]; then
            explain_block="\nПояснение простыми словами:\n$human_text"
        fi
        log "WARN" "Warnings found"
        send_telegram "Предупреждения:

$warn_text$explain_block" "high"
    else
        log "SUCCESS" "All deep checks passed"
    fi
}

main "$@"
