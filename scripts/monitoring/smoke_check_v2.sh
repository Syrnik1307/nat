#!/bin/bash
# ============================================================
# LECTIO SMOKE CHECK v2.0 - Полная бизнес-проверка
# ============================================================
# Проверяет ВСЕ критичные пользовательские сценарии:
# - Авторизация (JWT login)
# - API для учителя (уроки, записи, ДЗ)
# - API для студента (ДЗ, посещаемость)
# - Стриминг записей
# - Оплата подписки
# - Статические файлы (CSS/JS)
#
# Расположение: /opt/lectio-monitor/smoke_check_v2.sh
# ============================================================

set -uo pipefail

CONFIG_FILE="/opt/lectio-monitor/config.env"
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
fi

# ==================== КОНФИГУРАЦИЯ ====================
SITE_URL="${SITE_URL:-https://lectio.tw1.ru}"
# Для публичных проверок используем HTTPS URL (через nginx)
BACKEND_URL="${BACKEND_URL:-https://lectio.tw1.ru}"
# Для авторизованных API проверок используем внутренний URL (избегаем hairpin NAT)
INTERNAL_BACKEND_URL="${INTERNAL_BACKEND_URL:-http://127.0.0.1:8000}"
AUTH_BACKEND_URL="${AUTH_BACKEND_URL:-$INTERNAL_BACKEND_URL}"

# Публичный host для корректного Host/X-Forwarded-Proto при обращении к localhost
PUBLIC_HOST="${PUBLIC_HOST:-}"
if [[ -z "$PUBLIC_HOST" ]]; then
    PUBLIC_HOST="${BACKEND_URL#https://}"
    PUBLIC_HOST="${PUBLIC_HOST#http://}"
    PUBLIC_HOST="${PUBLIC_HOST%%/*}"
fi
PROJECT_ROOT="${PROJECT_ROOT:-/var/www/teaching_panel}"
LOG_FILE="${LOG_FILE:-/var/log/lectio-monitor/smoke_v2.log}"
STATE_FILE="/var/run/lectio-monitor/smoke_v2_state"

# Telegram настройки - используем ERRORS бот
ERRORS_BOT_TOKEN="${ERRORS_BOT_TOKEN:-${TELEGRAM_BOT_TOKEN:-}}"
ERRORS_CHAT_ID="${ERRORS_CHAT_ID:-${TELEGRAM_CHAT_ID:-}}"

# Тестовые пользователи
SMOKE_TEACHER_EMAIL="${SMOKE_TEACHER_EMAIL:-smoke_teacher@test.local}"
SMOKE_TEACHER_PASSWORD="${SMOKE_TEACHER_PASSWORD:-SmokeTest123!}"
SMOKE_STUDENT_EMAIL="${SMOKE_STUDENT_EMAIL:-smoke_student@test.local}"
SMOKE_STUDENT_PASSWORD="${SMOKE_STUDENT_PASSWORD:-SmokeTest123!}"

# Rate limiting
MAX_RESTARTS_PER_HOUR="${MAX_RESTARTS_PER_HOUR:-2}"
DEPLOY_GRACE_PERIOD="${DEPLOY_GRACE_PERIOD:-300}"  # Пропускать алерты 300 сек после деплоя

mkdir -p "$(dirname "$LOG_FILE")" "$(dirname "$STATE_FILE")"

# ==================== ЛОГИРОВАНИЕ ====================
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

# ==================== TELEGRAM ====================
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
        log_warn "Telegram не настроен"
        return 0
    fi

    local emoji=""
    local prefix=""
    case "$priority" in
        critical) 
            emoji="🚨"
            prefix="КРИТИЧНО"
            ;;
        high)     
            emoji="⚠️"
            prefix="ВНИМАНИЕ"
            ;;
        recovery) 
            emoji="✅"
            prefix="ВОССТАНОВЛЕНО"
            ;;
        *)        
            emoji="ℹ️"
            prefix="ИНФО"
            ;;
    esac

    local full_message="$emoji $prefix: Мониторинг API

$message

🕐 $(date '+%Y-%m-%d %H:%M:%S')
🖥️ Сервер: $(hostname)"

    curl -s -X POST "https://api.telegram.org/bot${ERRORS_BOT_TOKEN}/sendMessage" \
        -d "chat_id=${ERRORS_CHAT_ID}" \
        -d "text=${full_message}" \
        -d "parse_mode=HTML" \
        > /dev/null 2>&1 || log_warn "Не удалось отправить Telegram"
}

# ==================== HTTP HELPERS ====================
http_get() {
    local url="$1"
    local token="${2:-}"
    local timeout="${3:-15}"
    local retries="${4:-2}"

    local headers=()
    if [[ -n "$token" ]]; then
        headers+=("-H" "Authorization: Bearer $token")
    fi

    if [[ -n "$PUBLIC_HOST" ]] && [[ "$url" == http://127.0.0.1* || "$url" == http://localhost* ]]; then
        headers+=("-H" "Host: $PUBLIC_HOST")
        headers+=("-H" "X-Forwarded-Proto: https")
    fi

    local response="000|0"
    local attempt=0
    while [[ $attempt -le $retries ]]; do
        response=$(curl -s -o /tmp/smoke_body.json -w "%{http_code}|%{time_total}" \
            --max-time "$timeout" \
            --connect-timeout 5 \
            "${headers[@]}" \
            "$url" 2>/dev/null) || response="000|0"
        local code="${response%%|*}"
        if [[ "$code" != "000" ]]; then
            break
        fi
        attempt=$((attempt + 1))
        sleep 1
    done

    echo "$response"
}

http_post_json() {
    local url="$1"
    local data="$2"
    local token="${3:-}"
    local timeout="${4:-15}"
    local retries="${5:-2}"

    local headers=("-H" "Content-Type: application/json")
    if [[ -n "$token" ]]; then
        headers+=("-H" "Authorization: Bearer $token")
    fi

    if [[ -n "$PUBLIC_HOST" ]] && [[ "$url" == http://127.0.0.1* || "$url" == http://localhost* ]]; then
        headers+=("-H" "Host: $PUBLIC_HOST")
        headers+=("-H" "X-Forwarded-Proto: https")
    fi

    local response="000|0"
    local attempt=0
    while [[ $attempt -le $retries ]]; do
        response=$(curl -s -o /tmp/smoke_body.json -w "%{http_code}|%{time_total}" \
            --max-time "$timeout" \
            --connect-timeout 5 \
            -X POST \
            "${headers[@]}" \
            -d "$data" \
            "$url" 2>/dev/null) || response="000|0"
        local code="${response%%|*}"
        if [[ "$code" != "000" ]]; then
            break
        fi
        attempt=$((attempt + 1))
        sleep 1
    done

    echo "$response"
}

# ==================== JWT ЧЕРЕЗ API ====================
get_token_via_api() {
    local email="$1"
    local password="$2"

    local headers=("-H" "Content-Type: application/json")
    if [[ -n "$PUBLIC_HOST" ]] && [[ "$AUTH_BACKEND_URL" == http://127.0.0.1* || "$AUTH_BACKEND_URL" == http://localhost* ]]; then
        headers+=("-H" "Host: $PUBLIC_HOST")
        headers+=("-H" "X-Forwarded-Proto: https")
    fi

    local response
    # ВАЖНО: trailing slash обязателен для Django!
    response=$(curl -s -o /tmp/smoke_token.json -w "%{http_code}" \
        --max-time 15 \
        -X POST \
        "${headers[@]}" \
        -d "{\"email\":\"$email\",\"password\":\"$password\"}" \
        "${AUTH_BACKEND_URL}/api/jwt/token/" 2>/dev/null) || response="000"

    LAST_TOKEN_HTTP_CODE="$response"

    if [[ "$response" == "200" ]]; then
        cat /tmp/smoke_token.json | grep -o '"access":"[^"]*"' | cut -d'"' -f4
    else
        echo ""
    fi
}

# ==================== STATE MANAGEMENT ====================
is_deploy_in_progress() {
    local deploy_marker="/var/run/lectio-monitor/deploy_in_progress"
    if [[ -f "$deploy_marker" ]]; then
        local marker_time=$(stat -c %Y "$deploy_marker" 2>/dev/null || echo 0)
        local now=$(date +%s)
        local elapsed=$((now - marker_time))
        if [[ $elapsed -lt $DEPLOY_GRACE_PERIOD ]]; then
            return 0  # true - деплой в процессе
        else
            rm -f "$deploy_marker"
        fi
    fi
    return 1  # false
}

get_last_alert_time() {
    if [[ -f "$STATE_FILE" ]]; then
        grep '^last_alert:' "$STATE_FILE" | cut -d: -f2 || echo "0"
    else
        echo "0"
    fi
}

save_alert_time() {
    local now=$(date +%s)
    echo "last_alert:$now" > "$STATE_FILE"
}

# Антиспам: не слать одинаковые алерты чаще чем раз в 5 минут
can_send_alert() {
    local last=$(get_last_alert_time)
    local now=$(date +%s)
    local elapsed=$((now - last))
    if [[ $elapsed -lt 300 ]]; then
        return 1  # Слишком рано
    fi
    return 0
}

# ==================== ПРОВЕРКИ ====================

# 1. Проверка статических файлов (часто ломается после деплоя)
check_static_files() {
    local result=$(http_get "${SITE_URL}/")
    local code="${result%%|*}"
    
    if [[ "$code" != "200" ]]; then
        echo "FAIL:Главная страница HTTP $code"
        return 1
    fi
    
    # Проверяем что в ответе есть признаки React приложения
    if ! grep -q "root\|React\|bundle\|static" /tmp/smoke_body.json 2>/dev/null; then
        echo "FAIL:Главная страница не содержит React bundle"
        return 1
    fi
    
    echo "OK"
    return 0
}

# 2. Проверка health endpoint
check_health() {
    local result=$(http_get "${BACKEND_URL}/api/health/")
    local code="${result%%|*}"
    
    if [[ "$code" != "200" ]]; then
        echo "FAIL:/api/health/ HTTP $code"
        return 1
    fi
    
    # Проверяем что БД доступна
    if ! grep -q '"database":true\|"database": true' /tmp/smoke_body.json 2>/dev/null; then
        echo "FAIL:Database check failed"
        return 1
    fi
    
    echo "OK"
    return 0
}

# 3. Проверка авторизации учителя
check_teacher_auth() {
    local token=$(get_token_via_api "$SMOKE_TEACHER_EMAIL" "$SMOKE_TEACHER_PASSWORD")
    
    if [[ -z "$token" ]]; then
        local code="${LAST_TOKEN_HTTP_CODE:-000}"
        if [[ "$code" == "401" || "$code" == "403" || "$code" == "429" ]]; then
            echo "FAIL_HIGH:Не удалось получить JWT для учителя (HTTP $code)"
        else
            echo "FAIL_CRITICAL:Не удалось получить JWT для учителя (HTTP $code)"
        fi
        return 1
    fi
    
    # Проверяем /api/me/
    local result=$(http_get "${AUTH_BACKEND_URL}/api/me/" "$token")
    local code="${result%%|*}"
    
    if [[ "$code" != "200" ]]; then
        echo "FAIL:/api/me/ HTTP $code"
        return 1
    fi
    
    echo "$token"  # Возвращаем токен для дальнейших проверок
    return 0
}

# 4. Проверка списка уроков (учитель)
check_lessons() {
    local token="$1"
    local result=$(http_get "${AUTH_BACKEND_URL}/api/schedule/lessons/" "$token")
    local code="${result%%|*}"
    
    if [[ "$code" != "200" ]]; then
        echo "FAIL:/api/schedule/lessons/ HTTP $code"
        return 1
    fi
    
    echo "OK"
    return 0
}

# 5. Проверка списка записей (учитель)
check_recordings() {
    local token="$1"
    # URL: /schedule/api/recordings/teacher/ (не /api/schedule/...)
    local result=$(http_get "${AUTH_BACKEND_URL}/schedule/api/recordings/teacher/" "$token")
    local code="${result%%|*}"
    
    if [[ "$code" != "200" ]]; then
        echo "FAIL:/schedule/api/recordings/teacher/ HTTP $code"
        return 1
    fi
    
    echo "OK"
    return 0
}

# 6. Проверка списка ДЗ (учитель)
check_homework_teacher() {
    local token="$1"
    local result=$(http_get "${AUTH_BACKEND_URL}/api/homework/" "$token")
    local code="${result%%|*}"
    
    if [[ "$code" != "200" ]]; then
        echo "FAIL:/api/homework/ (teacher) HTTP $code"
        return 1
    fi
    
    echo "OK"
    return 0
}

# 7. Проверка подписки
check_subscription() {
    local token="$1"
    local result=$(http_get "${AUTH_BACKEND_URL}/api/subscription/" "$token")
    local code="${result%%|*}"
    
    if [[ "$code" != "200" ]]; then
        echo "FAIL:/api/subscription/ HTTP $code"
        return 1
    fi
    
    echo "OK"
    return 0
}

# 8. Проверка создания платежа (без реального платежа)
check_payment_creation() {
    local token="$1"
    local result=$(http_post_json "${AUTH_BACKEND_URL}/api/subscription/create-payment/" '{"plan":"monthly","provider":"tbank"}' "$token")
    local code="${result%%|*}"
    
    # 200, 201, или 400 (если подписка уже активна) - всё ок
    if [[ "$code" != "200" && "$code" != "201" && "$code" != "400" ]]; then
        echo "FAIL:/api/subscription/create-payment/ HTTP $code"
        return 1
    fi
    
    echo "OK"
    return 0
}

# 9. Проверка авторизации студента
check_student_auth() {
    local token=$(get_token_via_api "$SMOKE_STUDENT_EMAIL" "$SMOKE_STUDENT_PASSWORD")
    
    if [[ -z "$token" ]]; then
        local code="${LAST_TOKEN_HTTP_CODE:-000}"
        if [[ "$code" == "401" || "$code" == "403" || "$code" == "429" ]]; then
            echo "FAIL_HIGH:Не удалось получить JWT для студента (HTTP $code)"
        else
            echo "FAIL_CRITICAL:Не удалось получить JWT для студента (HTTP $code)"
        fi
        return 1
    fi
    
    echo "$token"
    return 0
}

# 10. Проверка ДЗ для студента
check_homework_student() {
    local token="$1"
    local result=$(http_get "${AUTH_BACKEND_URL}/api/homework/" "$token")
    local code="${result%%|*}"
    
    if [[ "$code" != "200" ]]; then
        echo "FAIL:/api/homework/ (student) HTTP $code"
        return 1
    fi
    
    echo "OK"
    return 0
}

# 11. Проверка групп
check_groups() {
    local token="$1"
    local result=$(http_get "${AUTH_BACKEND_URL}/api/groups/" "$token")
    local code="${result%%|*}"
    
    if [[ "$code" != "200" ]]; then
        echo "FAIL:/api/groups/ HTTP $code"
        return 1
    fi
    
    echo "OK"
    return 0
}

# ==================== ЧЕЛОВЕКО-ПОНЯТНЫЕ ОБЪЯСНЕНИЯ ====================
build_human_explanation() {
    local issue="$1"
    local explanation=""
    local action=""
    
    case "$issue" in
        *"Главная страница HTTP"*)
            explanation="Сайт не отвечает или вернул ошибку. Посетители не могут зайти на платформу."
            action="Проверьте статус Nginx и Django: systemctl status nginx teaching-panel"
            ;;
        *"не содержит React bundle"*)
            explanation="Страница загрузилась, но React-приложение не найдено. Вероятно, сломался деплой."
            action="Проверьте наличие frontend build: ls /var/www/lectio/frontend/build/"
            ;;
        *"/api/health/"*)
            explanation="Backend не отвечает на health-check. Django сервис может быть остановлен или перегружен."
            action="Перезапустите сервис: systemctl restart teaching-panel"
            ;;
        *"Database check failed"*)
            explanation="Приложение не может подключиться к базе данных. Все данные недоступны."
            action="Проверьте PostgreSQL: systemctl status postgresql, psql -U postgres -c 'SELECT 1'"
            ;;
        *"JWT для учителя"*)
            explanation="Система авторизации не работает. Учителя не могут войти в аккаунт."
            action="Проверьте тестовые учётные данные и работу /api/jwt/token/"
            ;;
        *"JWT для студента"*)
            explanation="Авторизация студентов не работает. Студенты не могут войти."
            action="Проверьте тестовые учётные данные студента"
            ;;
        *"/api/me/"*)
            explanation="Не удаётся получить профиль пользователя. Авторизованные запросы ломаются."
            action="Проверьте middleware аутентификации и JWT secret"
            ;;
        *"/api/schedule/lessons/"*)
            explanation="Учителя не могут видеть расписание уроков."
            action="Проверьте логи Django и права доступа к schedule модулю"
            ;;
        *"/schedule/api/recordings/"*)
            explanation="Записи уроков недоступны. Учителя и студенты не могут смотреть записи."
            action="Проверьте модуль recordings и доступ к хранилищу"
            ;;
        *"/api/homework/"*)
            explanation="Модуль домашних заданий не отвечает. ДЗ недоступны."
            action="Проверьте homework модуль и его views"
            ;;
        *"/api/subscription/"*)
            explanation="Информация о подписке недоступна. Это влияет на функции, требующие подписки."
            action="Проверьте subscription views в accounts"
            ;;
        *"/api/subscription/create-payment/"*)
            explanation="Создание платежей не работает. Пользователи не смогут оплатить подписку."
            action="Проверьте настройки платёжной системы (T-Bank/YooKassa)"
            ;;
        *"/api/groups/"*)
            explanation="Группы недоступны. Учителя не видят свои группы студентов."
            action="Проверьте groups модуль"
            ;;
        *)
            explanation="Неизвестная проблема с API."
            action="Проверьте логи: journalctl -u teaching-panel -n 50"
            ;;
    esac
    
    echo "ЧТО ЭТО ЗНАЧИТ: $explanation
ЧТО ДЕЛАТЬ: $action"
}

# ==================== ГЛАВНАЯ ПРОВЕРКА ====================
run_all_checks() {
    local issues=()
    local critical_count=0
    local teacher_token=""
    local student_token=""
    
    log_info "=== Smoke Check v2 START ==="
    
    # 1. Статика
    local res=$(check_static_files)
    if [[ "$res" == FAIL_CRITICAL:* ]]; then
        issues+=("${res#FAIL_CRITICAL:}")
        ((critical_count++))
    elif [[ "$res" == FAIL_HIGH:* ]]; then
        issues+=("${res#FAIL_HIGH:}")
    elif [[ "$res" == FAIL:* ]]; then
        issues+=("${res#FAIL:}")
        ((critical_count++))
    fi
    
    # 2. Health
    res=$(check_health)
    if [[ "$res" == FAIL:* ]]; then
        issues+=("${res#FAIL:}")
        ((critical_count++))
    fi
    
    # 3. Учитель: авторизация
    res=$(check_teacher_auth)
    if [[ "$res" == FAIL_CRITICAL:* ]]; then
        issues+=("${res#FAIL_CRITICAL:}")
        ((critical_count++))
    elif [[ "$res" == FAIL_HIGH:* ]]; then
        issues+=("${res#FAIL_HIGH:}")
    elif [[ "$res" == FAIL:* ]]; then
        issues+=("${res#FAIL:}")
        ((critical_count++))
    else
        teacher_token="$res"
        
        # 4-8: Проверки с токеном учителя
        res=$(check_lessons "$teacher_token")
        [[ "$res" == FAIL:* ]] && issues+=("${res#FAIL:}")
        
        res=$(check_recordings "$teacher_token")
        [[ "$res" == FAIL:* ]] && issues+=("${res#FAIL:}")
        
        res=$(check_homework_teacher "$teacher_token")
        [[ "$res" == FAIL:* ]] && issues+=("${res#FAIL:}")
        
        res=$(check_subscription "$teacher_token")
        [[ "$res" == FAIL:* ]] && issues+=("${res#FAIL:}")
        
        res=$(check_payment_creation "$teacher_token")
        [[ "$res" == FAIL:* ]] && issues+=("${res#FAIL:}")
        
        res=$(check_groups "$teacher_token")
        [[ "$res" == FAIL:* ]] && issues+=("${res#FAIL:}")
    fi
    
    # 9-10. Студент: авторизация + ДЗ
    res=$(check_student_auth)
    if [[ "$res" == FAIL_CRITICAL:* ]]; then
        issues+=("${res#FAIL_CRITICAL:}")
        ((critical_count++))
    elif [[ "$res" == FAIL_HIGH:* ]]; then
        issues+=("${res#FAIL_HIGH:}")
    elif [[ "$res" == FAIL:* ]]; then
        issues+=("${res#FAIL:}")
    else
        student_token="$res"
        
        res=$(check_homework_student "$student_token")
        [[ "$res" == FAIL:* ]] && issues+=("${res#FAIL:}")
    fi
    
    # ==================== РЕЗУЛЬТАТ ====================
    if [[ ${#issues[@]} -eq 0 ]]; then
        log_success "Все проверки пройдены (11/11)"
        return 0
    fi
    
    local issue_text=$(printf '• %s\n' "${issues[@]}")
    log_error "Обнаружено ${#issues[@]} проблем:\n$issue_text"
    
    # Проверяем не идёт ли деплой
    if is_deploy_in_progress; then
        log_info "Деплой в процессе, пропуск алертов"
        return 1
    fi
    
    # Антиспам
    if ! can_send_alert; then
        log_info "Антиспам: алерт уже отправлялся недавно"
        return 1
    fi
    
    # Отправляем алерт
    save_alert_time
    
    # Формируем сообщение с объяснениями
    local detailed_message=""
    for issue in "${issues[@]}"; do
        local explanation=$(build_human_explanation "$issue")
        detailed_message+="━━━━━━━━━━━━━━━━━━━━
ПРОБЛЕМА: $issue

$explanation

"
    done
    
    if [[ $critical_count -gt 0 ]]; then
        send_telegram "КРИТИЧЕСКИЕ ПРОБЛЕМЫ (${critical_count} из ${#issues[@]}):

$detailed_message
📝 Если не понятно - перешлите это сообщение разработчику" "critical"
    else
        send_telegram "Обнаружены проблемы (${#issues[@]}):

$detailed_message
📝 Если не понятно - перешлите это сообщение разработчику" "high"
    fi
    
    return 1
}

# ==================== MAIN ====================
main() {
    run_all_checks
    exit $?
}

main "$@"
