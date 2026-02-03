#!/bin/bash
# ============================================================
# LECTIO HEALTH CHECK & AUTO-RECOVERY SCRIPT
# ============================================================
# Этот скрипт выполняет комплексную проверку здоровья сайта
# и автоматически восстанавливает сервисы при обнаружении проблем
# 
# Расположение на сервере: /opt/lectio-monitor/health_check.sh
# ============================================================

set -euo pipefail

# Загружаем конфигурацию (важно для cron: env переменные иначе не доступны)
CONFIG_FILE="/opt/lectio-monitor/config.env"
if [[ -f "$CONFIG_FILE" ]]; then
    # shellcheck disable=SC1090
    source "$CONFIG_FILE"
fi

# ==================== КОНФИГУРАЦИЯ ====================
SITE_URL="https://lectiospace.ru"
API_URL="https://lectiospace.ru/api/health/"
FRONTEND_BUILD="/var/www/teaching_panel/frontend/build"
BACKEND_SERVICE="teaching_panel"
NGINX_SERVICE="nginx"
LOG_FILE="/var/log/lectio-monitor/health.log"
ALERT_LOG="/var/log/lectio-monitor/alerts.log"
STATE_FILE="/var/run/lectio-monitor/state"
LOCK_FILE="/var/run/lectio-monitor/health.lock"

# Telegram настройки для бота ошибок (заполнить при деплое)
# ERRORS_BOT_TOKEN - отдельный бот для уведомлений об ошибках сайта
# Fallback на старые переменные для обратной совместимости
ERRORS_BOT_TOKEN="${ERRORS_BOT_TOKEN:-${TELEGRAM_BOT_TOKEN:-}}"
ERRORS_CHAT_ID="${ERRORS_CHAT_ID:-${TELEGRAM_CHAT_ID:-}}"

# Thresholds
MAX_RESPONSE_TIME=5          # секунды
MAX_RECOVERY_ATTEMPTS=3      # макс попыток восстановления
RECOVERY_COOLDOWN=300        # 5 минут между попытками восстановления

# ==================== ФУНКЦИИ ЛОГИРОВАНИЯ ====================

log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
}

log_info() { log "INFO" "$1"; }
log_warn() { log "WARN" "$1"; }
log_error() { log "ERROR" "$1"; }
log_success() { log "SUCCESS" "$1"; }

# ==================== TELEGRAM ALERTS ====================

build_human_explanations() {
    local issue
    local lines=()
    while IFS= read -r issue; do
        [[ -z "$issue" ]] && continue
        case "$issue" in
            "Backend сервис не активен"*)
                lines+=("• Приложение остановлено — сайт может не открываться. Действие: проверить и перезапустить teaching_panel.")
                ;;
            "Nginx не активен"*)
                lines+=("• Веб‑сервер не работает — страницы и API могут быть недоступны. Действие: перезапустить nginx.")
                ;;
            "HTTP статус:"*)
                lines+=("• Сайт отвечает ошибкой вместо нормальной страницы. Действие: проверить логи nginx и приложения.")
                ;;
            "Медленный ответ:"*)
                lines+=("• Сайт работает, но медленно — возможны задержки у пользователей. Действие: проверить нагрузку и БД.")
                ;;
            "Static файлы недоступны"*)
                lines+=("• Не загружаются стили/скрипты — интерфейс может выглядеть сломанным. Действие: исправить права на файлы фронтенда.")
                ;;
            "Проблема с правами доступа frontend"*)
                lines+=("• Файлы интерфейса недоступны для чтения. Действие: восстановить права доступа.")
                ;;
            "Мало места на диске"*)
                lines+=("• Диск почти заполнен — записи/логи могут не сохраняться. Действие: освободить место или расширить диск.")
                ;;
            "Мало памяти"*)
                lines+=("• Оперативной памяти мало — сервер уходит в swap и начинает тормозить. Действие: проверить память, перезапустить тяжёлые процессы или увеличить RAM.")
                ;;
            "Проблема с gunicorn воркерами"*)
                lines+=("• Процессы приложения нестабильны — часть запросов может падать. Действие: перезапустить teaching_panel и проверить логи.")
                ;;
            *)
                lines+=("• Требуется проверка логов и состояния сервисов.")
                ;;
        esac
    done <<< "$1"

    printf '%s\n' "${lines[@]}"
}

get_memory_snapshot() {
    local mem_available
    local mem_total
    local swap_used
    local swap_total

    mem_available=$(free -m | awk '/^Mem:/ {print $7}')
    mem_total=$(free -m | awk '/^Mem:/ {print $2}')
    swap_used=$(free -m | awk '/^Swap:/ {print $3}')
    swap_total=$(free -m | awk '/^Swap:/ {print $2}')

    echo "Память: доступно ${mem_available}MB из ${mem_total}MB; swap ${swap_used}/${swap_total}MB"
}

send_telegram() {
    local message="$1"
    local priority="${2:-normal}"  # normal, high, critical

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
        log_warn "Telegram Errors Bot не настроен, пропуск отправки алерта"
        return 0
    fi
    
    local emoji=""
    case "$priority" in
        critical) emoji="🚨🚨🚨" ;;
        high)     emoji="⚠️" ;;
        *)        emoji="ℹ️" ;;
    esac
    
    local full_message="$emoji LECTIO MONITOR

$message

🕐 $(date '+%Y-%m-%d %H:%M:%S')
🖥️ Server: $(hostname)"

    curl -s -X POST "https://api.telegram.org/bot${ERRORS_BOT_TOKEN}/sendMessage" \
        -d "chat_id=${ERRORS_CHAT_ID}" \
        -d "text=${full_message}" \
        -d "parse_mode=HTML" \
        > /dev/null 2>&1 || log_warn "Не удалось отправить Telegram алерт"
    
    echo "$(date '+%Y-%m-%d %H:%M:%S') [$priority] $message" >> "$ALERT_LOG"
}

# ==================== ПРОВЕРКИ ЗДОРОВЬЯ ====================

check_service_active() {
    local service="$1"
    if systemctl is-active --quiet "$service"; then
        return 0
    else
        return 1
    fi
}

check_http_status() {
    local url="$1"
    local expected_code="${2:-200}"
    local timeout="${3:-10}"
    
    local response
    response=$(curl -s -o /dev/null -w "%{http_code}:%{time_total}" \
        --max-time "$timeout" \
        --connect-timeout 5 \
        "$url" 2>/dev/null) || response="000:0"
    
    local http_code="${response%%:*}"
    local time_total="${response##*:}"
    
    echo "$http_code:$time_total"
    
    if [[ "$http_code" == "$expected_code" ]]; then
        return 0
    else
        return 1
    fi
}

check_frontend_permissions() {
    local index_file="$FRONTEND_BUILD/index.html"
    
    if [[ ! -f "$index_file" ]]; then
        log_error "index.html не найден!"
        return 1
    fi
    
    # Проверяем права через stat (быстрее чем sudo -u www-data test)
    local owner=$(stat -c '%U' "$index_file" 2>/dev/null)
    local perms=$(stat -c '%a' "$index_file" 2>/dev/null)
    
    # Проверяем что владелец www-data или права позволяют чтение всем
    if [[ "$owner" != "www-data" ]] && [[ "${perms:2:1}" -lt 4 ]]; then
        log_error "index.html: неправильные права (owner=$owner, perms=$perms)"
        return 1
    fi
    
    # Проверяем static/js директорию
    local static_js="$FRONTEND_BUILD/static/js"
    if [[ -d "$static_js" ]]; then
        local js_perms=$(stat -c '%a' "$static_js" 2>/dev/null)
        # Нужно минимум 5 (r-x) для директории
        if [[ "${js_perms:2:1}" -lt 5 ]]; then
            log_error "static/js: недостаточные права (perms=$js_perms)"
            return 1
        fi
    fi
    
    return 0
}

check_disk_space() {
    local min_percent="${1:-10}"  # минимум 10% свободного места
    local usage
    usage=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')
    
    local free=$((100 - usage))
    if [[ $free -lt $min_percent ]]; then
        log_error "Критически мало места на диске: ${free}% свободно"
        return 1
    fi
    return 0
}

check_memory() {
    local min_mb="${1:-256}"  # минимум 256MB свободной памяти
    local available
    available=$(free -m | awk '/^Mem:/ {print $7}')
    
    if [[ $available -lt $min_mb ]]; then
        log_warn "Мало доступной памяти: ${available}MB"
        return 1
    fi
    return 0
}

check_gunicorn_workers() {
    local worker_count
    worker_count=$(pgrep -c -f "gunicorn.*teaching_panel" 2>/dev/null || echo "0")
    
    if [[ $worker_count -lt 2 ]]; then
        log_error "Недостаточно gunicorn воркеров: $worker_count"
        return 1
    fi
    return 0
}

check_database() {
    cd /var/www/teaching_panel/teaching_panel
    source ../venv/bin/activate
    
    if python -c "
import django
django.setup()
from django.db import connection
cursor = connection.cursor()
cursor.execute('SELECT 1')
" 2>/dev/null; then
        return 0
    else
        log_error "База данных недоступна"
        return 1
    fi
}

# ==================== RECOVERY ACTIONS ====================

fix_frontend_permissions() {
    log_info "Восстановление прав доступа frontend..."
    
    sudo chown -R www-data:www-data "$FRONTEND_BUILD"
    sudo chmod -R 755 "$FRONTEND_BUILD"
    
    if check_frontend_permissions; then
        log_success "Права доступа восстановлены"
        return 0
    else
        log_error "Не удалось восстановить права"
        return 1
    fi
}

restart_service() {
    local service="$1"
    log_info "Перезапуск сервиса $service..."
    
    sudo systemctl restart "$service"
    sleep 3
    
    if check_service_active "$service"; then
        log_success "Сервис $service перезапущен успешно"
        return 0
    else
        log_error "Не удалось перезапустить $service"
        return 1
    fi
}

full_recovery() {
    log_info "Запуск полного восстановления..."
    
    local success=true
    
    # 1. Права доступа
    fix_frontend_permissions || success=false
    
    # 2. Перезапуск backend
    restart_service "$BACKEND_SERVICE" || success=false
    
    # 3. Перезапуск nginx
    restart_service "$NGINX_SERVICE" || success=false
    
    # 4. Финальная проверка
    sleep 5
    local result
    result=$(check_http_status "$SITE_URL")
    local code="${result%%:*}"
    
    if [[ "$code" == "200" ]]; then
        log_success "Полное восстановление успешно завершено"
        return 0
    else
        log_error "Полное восстановление не удалось (HTTP $code)"
        return 1
    fi
}

# ==================== RECOVERY STATE MANAGEMENT ====================

get_recovery_attempts() {
    if [[ -f "$STATE_FILE" ]]; then
        cat "$STATE_FILE" | grep "attempts:" | cut -d: -f2 || echo "0"
    else
        echo "0"
    fi
}

get_last_recovery_time() {
    if [[ -f "$STATE_FILE" ]]; then
        cat "$STATE_FILE" | grep "last_recovery:" | cut -d: -f2 || echo "0"
    else
        echo "0"
    fi
}

update_recovery_state() {
    local attempts="$1"
    local timestamp=$(date +%s)
    
    mkdir -p "$(dirname "$STATE_FILE")"
    cat > "$STATE_FILE" << EOF
attempts:$attempts
last_recovery:$timestamp
EOF
}

reset_recovery_state() {
    rm -f "$STATE_FILE"
}

can_attempt_recovery() {
    local attempts
    attempts=$(get_recovery_attempts)
    
    if [[ $attempts -ge $MAX_RECOVERY_ATTEMPTS ]]; then
        local last_time
        last_time=$(get_last_recovery_time)
        local now=$(date +%s)
        local elapsed=$((now - last_time))
        
        if [[ $elapsed -lt $RECOVERY_COOLDOWN ]]; then
            log_warn "Достигнут лимит попыток восстановления, ожидание cooldown"
            return 1
        else
            # Cooldown прошёл, сбрасываем счётчик
            reset_recovery_state
        fi
    fi
    
    return 0
}

# ==================== ГЛАВНАЯ ПРОВЕРКА ====================

run_health_check() {
    local issues=()
    local critical=false
    
    log_info "Начало проверки здоровья..."
    
    # 1. Проверка сервисов
    if ! check_service_active "$BACKEND_SERVICE"; then
        issues+=("Backend сервис не активен")
        critical=true
    fi
    
    if ! check_service_active "$NGINX_SERVICE"; then
        issues+=("Nginx не активен")
        critical=true
    fi
    
    # 2. Проверка HTTP статуса
    local http_result
    http_result=$(check_http_status "$SITE_URL")
    local http_code="${http_result%%:*}"
    local response_time="${http_result##*:}"
    
    if [[ "$http_code" != "200" ]]; then
        issues+=("HTTP статус: $http_code (ожидался 200)")
        critical=true
    elif (( $(echo "$response_time > $MAX_RESPONSE_TIME" | bc -l 2>/dev/null || echo 0) )); then
        issues+=("Медленный ответ: ${response_time}s")
    fi
    
    # 2.5 КРИТИЧНО: Проверка static файлов через HTTP (именно они падают с 403!)
    # Проверяем доступность static директории через HTTP
    local static_result
    static_result=$(check_http_status "${SITE_URL}/static/js/" "" 5)
    local static_code="${static_result%%:*}"
    
    # 403 = проблема с правами, 404 = OK (listing отключен), 200 = OK
    if [[ "$static_code" == "403" ]]; then
        issues+=("Static файлы недоступны (403 Forbidden) - проблема с правами!")
        critical=true
    fi
    
    # 3. Проверка прав доступа frontend
    if ! check_frontend_permissions; then
        issues+=("Проблема с правами доступа frontend")
        critical=true
    fi
    
    # 4. Проверка диска и памяти
    if ! check_disk_space; then
        issues+=("Мало места на диске")
    fi
    
    local memory_snapshot=""
    if ! check_memory; then
        issues+=("Мало памяти")
        memory_snapshot=$(get_memory_snapshot)
    fi
    
    # 5. Проверка gunicorn
    if ! check_gunicorn_workers; then
        issues+=("Проблема с gunicorn воркерами")
    fi
    
    # ==================== ПРИНЯТИЕ РЕШЕНИЙ ====================
    
    if [[ ${#issues[@]} -eq 0 ]]; then
        log_success "Все проверки пройдены успешно"
        reset_recovery_state
        return 0
    fi
    
    # Есть проблемы
    local issue_text
    issue_text=$(printf '%s\n' "${issues[@]}")
    local human_text
    human_text=$(build_human_explanations "$issue_text")
    local explain_block=""
    if [[ -n "$human_text" ]]; then
        explain_block="\n\nПояснение простыми словами:\n$human_text"
    fi
    local memory_block=""
    if [[ -n "$memory_snapshot" ]]; then
        memory_block="\n\n$memory_snapshot"
    fi
    log_warn "Обнаружены проблемы:\n$issue_text"
    
    if [[ "$critical" == true ]]; then
        send_telegram "🔴 КРИТИЧЕСКИЕ ПРОБЛЕМЫ ОБНАРУЖЕНЫ!

    $issue_text${explain_block}${memory_block}

    🔄 Запуск автоматического восстановления..." "critical"
        
        # Попытка автовосстановления
        if can_attempt_recovery; then
            local attempts
            attempts=$(get_recovery_attempts)
            attempts=$((attempts + 1))
            update_recovery_state "$attempts"
            
            log_info "Попытка восстановления #$attempts"
            
            if full_recovery; then
                send_telegram "✅ САЙТ ВОССТАНОВЛЕН!

Автоматическое восстановление успешно завершено.
Попытка #$attempts" "high"
                reset_recovery_state
                return 0
            else
                send_telegram "❌ АВТОВОССТАНОВЛЕНИЕ НЕ ПОМОГЛО!

Попытка #$attempts из $MAX_RECOVERY_ATTEMPTS

ТРЕБУЕТСЯ РУЧНОЕ ВМЕШАТЕЛЬСТВО!" "critical"
                return 1
            fi
        else
            send_telegram "⛔ ЛИМИТ ПОПЫТОК ИСЧЕРПАН!

Достигнуто максимальное количество попыток восстановления.
Ожидание cooldown ($RECOVERY_COOLDOWN секунд).

ТРЕБУЕТСЯ РУЧНОЕ ВМЕШАТЕЛЬСТВО!" "critical"
            return 1
        fi
    else
        # Не критичные проблемы
        send_telegram "⚠️ Обнаружены некритичные проблемы:

$issue_text${explain_block}${memory_block}" "normal"
        return 0
    fi
}

# ==================== LOCK MECHANISM ====================

acquire_lock() {
    local lock_dir
    lock_dir=$(dirname "$LOCK_FILE")
    mkdir -p "$lock_dir"
    
    if [[ -f "$LOCK_FILE" ]]; then
        local pid
        pid=$(cat "$LOCK_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            log_warn "Другой экземпляр уже запущен (PID: $pid)"
            exit 0
        else
            # Stale lock file
            rm -f "$LOCK_FILE"
        fi
    fi
    
    echo $$ > "$LOCK_FILE"
}

release_lock() {
    rm -f "$LOCK_FILE"
}

# ==================== MAIN ====================

main() {
    # Создаём директории для логов
    mkdir -p /var/log/lectio-monitor
    mkdir -p /var/run/lectio-monitor
    
    acquire_lock
    trap release_lock EXIT
    
    run_health_check
}

main "$@"
