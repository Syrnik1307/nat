#!/bin/bash
# ============================================================
# SAFE DEPLOY SCRIPT с автоматическим откатом
# ============================================================
# Этот скрипт обеспечивает безопасный деплой с:
# - Pre-deploy проверками
# - Бэкапом текущей версии
# - Автоматическим откатом при проблемах
# - Telegram уведомлениями
# - Фиксацией прав доступа
#
# Использование: ./deploy_safe.sh [frontend|backend|full]
# ============================================================

set -euo pipefail

# Загружаем конфигурацию (если скрипт запускается вручную, переменные могут быть не экспортированы)
CONFIG_FILE="/opt/lectio-monitor/config.env"
if [[ -f "$CONFIG_FILE" ]]; then
    # shellcheck disable=SC1090
    source "$CONFIG_FILE"
fi

# ==================== КОНФИГУРАЦИЯ ====================
SITE_URL="https://lectio.tw1.ru"
PROJECT_ROOT="/var/www/teaching_panel"
FRONTEND_BUILD="$PROJECT_ROOT/frontend/build"
BACKEND_DIR="$PROJECT_ROOT/teaching_panel"
VENV_DIR="$PROJECT_ROOT/venv"
BACKUP_DIR="$PROJECT_ROOT/backups"
LOG_FILE="/var/log/lectio-monitor/deploy.log"

# Services
BACKEND_SERVICE="teaching_panel"
NGINX_SERVICE="nginx"

# Telegram - используем отдельный бот для ошибок/деплоя
# Fallback на старые переменные для обратной совместимости
ERRORS_BOT_TOKEN="${ERRORS_BOT_TOKEN:-${TELEGRAM_BOT_TOKEN:-}}"
ERRORS_CHAT_ID="${ERRORS_CHAT_ID:-${TELEGRAM_CHAT_ID:-}}"

# Rollback settings
HEALTH_CHECK_RETRIES=5
HEALTH_CHECK_DELAY=3

# ==================== LOGGING & ALERTS ====================

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

send_telegram() {
    local message="$1"
    local emoji="${2:-ℹ️}"

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
    
    local full_message="$emoji LECTIO DEPLOY

$message

🕐 $(date '+%Y-%m-%d %H:%M:%S')"

    curl -s -X POST "https://api.telegram.org/bot${ERRORS_BOT_TOKEN}/sendMessage" \
        -d "chat_id=${ERRORS_CHAT_ID}" \
        -d "text=${full_message}" \
        -d "parse_mode=HTML" \
        > /dev/null 2>&1 || true
}

# ==================== BACKUP FUNCTIONS ====================

backup_frontend() {
    local backup_name="frontend_$(date +%Y%m%d_%H%M%S)"
    local backup_path="$BACKUP_DIR/$backup_name"
    
    mkdir -p "$BACKUP_DIR"
    
    if [[ -d "$FRONTEND_BUILD" ]]; then
        cp -a "$FRONTEND_BUILD" "$backup_path"
        log_info "Frontend забэкаплен в $backup_path"
        echo "$backup_path"
    else
        log_warn "Frontend build не найден для бэкапа"
        echo ""
    fi
}

backup_backend() {
    local backup_name="backend_$(date +%Y%m%d_%H%M%S)"
    local backup_path="$BACKUP_DIR/$backup_name"
    
    mkdir -p "$BACKUP_DIR"
    
    # Бэкапим только важные файлы (не venv)
    cd "$PROJECT_ROOT"
    tar -czf "${backup_path}.tar.gz" \
        --exclude='*.pyc' \
        --exclude='__pycache__' \
        --exclude='.git' \
        teaching_panel/ \
        2>/dev/null || true
    
    log_info "Backend забэкаплен в ${backup_path}.tar.gz"
    echo "${backup_path}.tar.gz"
}

rollback_frontend() {
    local backup_path="$1"
    
    if [[ -z "$backup_path" ]] || [[ ! -d "$backup_path" ]]; then
        log_error "Нет валидного бэкапа для отката"
        return 1
    fi
    
    log_warn "Откат frontend к $backup_path"
    
    rm -rf "$FRONTEND_BUILD"
    cp -a "$backup_path" "$FRONTEND_BUILD"
    
    # Исправляем права
    chown -R www-data:www-data "$FRONTEND_BUILD"
    chmod -R 755 "$FRONTEND_BUILD"
    
    log_success "Frontend откачен успешно"
}

# ==================== HEALTH CHECK ====================

check_site_health() {
    local retries="${1:-$HEALTH_CHECK_RETRIES}"
    local delay="${2:-$HEALTH_CHECK_DELAY}"
    
    for ((i=1; i<=retries; i++)); do
        local http_code
        http_code=$(curl -s -o /dev/null -w "%{http_code}" \
            --max-time 10 \
            --connect-timeout 5 \
            "$SITE_URL" 2>/dev/null) || http_code="000"
        
        if [[ "$http_code" == "200" ]]; then
            log_success "Health check пройден (попытка $i/$retries)"
            return 0
        fi
        
        log_warn "Health check failed: HTTP $http_code (попытка $i/$retries)"
        
        if [[ $i -lt $retries ]]; then
            sleep "$delay"
        fi
    done
    
    log_error "Health check провален после $retries попыток"
    return 1
}

# ==================== FIX PERMISSIONS ====================

fix_permissions() {
    log_info "Исправление прав доступа..."
    
    # Frontend
    if [[ -d "$FRONTEND_BUILD" ]]; then
        chown -R www-data:www-data "$FRONTEND_BUILD"
        chmod -R 755 "$FRONTEND_BUILD"
    fi
    
    # Static files
    local static_dir="$PROJECT_ROOT/staticfiles"
    if [[ -d "$static_dir" ]]; then
        chown -R www-data:www-data "$static_dir"
        chmod -R 755 "$static_dir"
    fi
    
    # Media files
    local media_dir="$PROJECT_ROOT/media"
    if [[ -d "$media_dir" ]]; then
        chown -R www-data:www-data "$media_dir"
        chmod -R 755 "$media_dir"
    fi
    
    log_success "Права исправлены"
}

# ==================== DEPLOY FUNCTIONS ====================

deploy_frontend() {
    local source_build="$1"
    
    log_info "Деплой frontend..."
    send_telegram "Начат деплой frontend" "🚀"
    
    # Устанавливаем маркер деплоя чтобы smoke_check не спамил алертами
    mkdir -p /var/run/lectio-monitor
    touch /var/run/lectio-monitor/deploy_in_progress
    
    # 1. Pre-deploy check
    if ! check_site_health 1 0; then
        log_warn "Сайт недоступен перед деплоем, продолжаем..."
    fi
    
    # 2. Backup
    local backup_path
    backup_path=$(backup_frontend)
    
    # 3. Deploy
    log_info "Копирование новой сборки..."
    rm -rf "${FRONTEND_BUILD}_new"
    cp -a "$source_build" "${FRONTEND_BUILD}_new"
    
    # 4. Atomic swap
    rm -rf "${FRONTEND_BUILD}_old"
    if [[ -d "$FRONTEND_BUILD" ]]; then
        mv "$FRONTEND_BUILD" "${FRONTEND_BUILD}_old"
    fi
    mv "${FRONTEND_BUILD}_new" "$FRONTEND_BUILD"
    
    # 5. Fix permissions (КРИТИЧЕСКИ ВАЖНО!)
    fix_permissions
    
    # 6. Restart services
    systemctl restart "$NGINX_SERVICE"
    
    # 7. Health check
    sleep 2
    if check_site_health; then
        log_success "Frontend деплой успешен!"
        send_telegram "Frontend успешно задеплоен!" "✅"
        
        # Cleanup old backup
        rm -rf "${FRONTEND_BUILD}_old"
        
        # Убираем маркер деплоя
        rm -f /var/run/lectio-monitor/deploy_in_progress
        
        return 0
    else
        log_error "Health check провален, откат..."
        send_telegram "Frontend деплой провален, выполняется откат..." "⚠️"
        
        # Rollback
        rm -rf "$FRONTEND_BUILD"
        if [[ -d "${FRONTEND_BUILD}_old" ]]; then
            mv "${FRONTEND_BUILD}_old" "$FRONTEND_BUILD"
        elif [[ -n "$backup_path" ]] && [[ -d "$backup_path" ]]; then
            rollback_frontend "$backup_path"
        fi
        
        fix_permissions
        systemctl restart "$NGINX_SERVICE"
        
        if check_site_health; then
            log_success "Откат успешен"
            send_telegram "Откат frontend выполнен успешно" "🔄"
        else
            send_telegram "КРИТИЧЕСКАЯ ОШИБКА: откат не помог!" "🚨"
        fi
        
        return 1
    fi
}

deploy_backend() {
    log_info "Деплой backend..."
    send_telegram "Начат деплой backend" "🚀"
    
    # Устанавливаем маркер деплоя чтобы smoke_check не спамил алертами
    mkdir -p /var/run/lectio-monitor
    touch /var/run/lectio-monitor/deploy_in_progress
    
    # 1. Backup
    local backup_path
    backup_path=$(backup_backend)
    
    # 2. Pull latest code
    cd "$PROJECT_ROOT"
    git fetch origin
    git reset --hard origin/main
    
    # 3. Install dependencies
    source "$VENV_DIR/bin/activate"
    pip install -r requirements.txt --quiet
    
    # 4. Migrations
    cd "$BACKEND_DIR"
    python manage.py migrate --noinput
    
    # 5. Collect static
    python manage.py collectstatic --noinput --clear
    
    # 6. Fix permissions
    fix_permissions
    
    # 7. Restart service
    systemctl restart "$BACKEND_SERVICE"
    
    # 8. Health check
    sleep 3
    if check_site_health; then
        log_success "Backend деплой успешен!"
        send_telegram "Backend успешно задеплоен!" "✅"
        
        # Убираем маркер деплоя
        rm -f /var/run/lectio-monitor/deploy_in_progress
        
        return 0
    else
        log_error "Backend health check провален"
        send_telegram "Backend деплой провален!" "🚨"
        return 1
    fi
}

deploy_full() {
    log_info "Полный деплой..."
    
    deploy_backend
    
    local frontend_source="$1"
    if [[ -n "$frontend_source" ]] && [[ -d "$frontend_source" ]]; then
        deploy_frontend "$frontend_source"
    fi
}

# ==================== CLEANUP OLD BACKUPS ====================

cleanup_old_backups() {
    local max_age_days="${1:-7}"
    
    log_info "Очистка бэкапов старше $max_age_days дней..."
    
    find "$BACKUP_DIR" -type f -mtime +"$max_age_days" -delete 2>/dev/null || true
    find "$BACKUP_DIR" -type d -empty -delete 2>/dev/null || true
    
    log_success "Очистка завершена"
}

# ==================== MAIN ====================

main() {
    local deploy_type="${1:-frontend}"
    local source_path="${2:-}"
    
    mkdir -p /var/log/lectio-monitor
    mkdir -p "$BACKUP_DIR"
    
    case "$deploy_type" in
        frontend)
            if [[ -z "$source_path" ]]; then
                echo "Usage: $0 frontend /path/to/build"
                exit 1
            fi
            deploy_frontend "$source_path"
            ;;
        backend)
            deploy_backend
            ;;
        full)
            deploy_full "$source_path"
            ;;
        cleanup)
            cleanup_old_backups "${2:-7}"
            ;;
        *)
            echo "Usage: $0 [frontend|backend|full|cleanup] [source_path]"
            exit 1
            ;;
    esac
}

main "$@"
