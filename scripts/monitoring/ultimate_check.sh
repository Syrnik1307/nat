#!/bin/bash
# ============================================================
# LECTIO ULTIMATE HEALTH CHECK v1.0
# ============================================================
# Максимально полная проверка всех критических компонентов:
# - Инфраструктура (nginx, gunicorn, redis, disk, memory, CPU)
# - База данных (connectivity, integrity, orphaned records)
# - Авторизация (JWT, refresh, roles)
# - API endpoints (все критические)
# - Платежи (YooKassa, T-Bank доступность + тестовые запросы)
# - Google Drive (токен, upload test, quota)
# - Zoom (OAuth, API доступность)
# - Telegram (бот, webhooks)
# - Консистентность данных (ученики, группы, записи)
# - Статика (frontend build, assets)
# - SSL/Security
#
# Рекомендуемый запуск: каждые 2 часа или по cron
# Расположение: /opt/lectio-monitor/ultimate_check.sh
# ============================================================

set -uo pipefail

CONFIG_FILE="/opt/lectio-monitor/config.env"
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
fi

# ==================== КОНФИГУРАЦИЯ ====================
SITE_URL="${SITE_URL:-https://lectiospace.ru}"
BACKEND_URL="${BACKEND_URL:-https://lectiospace.ru}"
PROJECT_ROOT="${PROJECT_ROOT:-/var/www/teaching_panel}"
LOG_FILE="${LOG_FILE:-/var/log/lectio-monitor/ultimate.log}"
REPORT_FILE="/var/log/lectio-monitor/ultimate_report_$(date +%Y%m%d_%H%M%S).txt"

PYTHON="${PROJECT_ROOT}/venv/bin/python"
MANAGE="${PROJECT_ROOT}/teaching_panel/manage.py"

SMOKE_TEACHER_EMAIL="${SMOKE_TEACHER_EMAIL:-smoke_teacher@test.local}"
SMOKE_TEACHER_PASSWORD="${SMOKE_TEACHER_PASSWORD:-SmokeTest123!}"
SMOKE_STUDENT_EMAIL="${SMOKE_STUDENT_EMAIL:-smoke_student@test.local}"
SMOKE_STUDENT_PASSWORD="${SMOKE_STUDENT_PASSWORD:-SmokeTest123!}"

ERRORS_BOT_TOKEN="${ERRORS_BOT_TOKEN:-}"
ERRORS_CHAT_ID="${ERRORS_CHAT_ID:-}"

# Флаг: отправлять уведомление при успехе (по умолчанию нет)
# Включается через: --notify-success или NOTIFY_SUCCESS=1
NOTIFY_SUCCESS="${NOTIFY_SUCCESS:-0}"

mkdir -p "$(dirname "$LOG_FILE")" "$(dirname "$REPORT_FILE")"

# ==================== РЕЗУЛЬТАТЫ ====================
declare -A RESULTS
CRITICAL_COUNT=0
WARNING_COUNT=0
OK_COUNT=0
SKIP_COUNT=0

# ==================== ЛОГИРОВАНИЕ ====================
log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
}

log_result() {
    local category="$1"
    local test_name="$2"
    local result="$3"
    local details="${4:-}"
    
    local status_icon=""
    case "$result" in
        OK)     status_icon="[OK]"; ((OK_COUNT++)) ;;
        WARN)   status_icon="[WARN]"; ((WARNING_COUNT++)) ;;
        FAIL)   status_icon="[FAIL]"; ((CRITICAL_COUNT++)) ;;
        SKIP)   status_icon="[SKIP]"; ((SKIP_COUNT++)) ;;
    esac
    
    local full_key="${category}::${test_name}"
    RESULTS["$full_key"]="${result}|${details}"
    
    echo "$status_icon $category / $test_name: $details" | tee -a "$REPORT_FILE"
    log "INFO" "$status_icon $category / $test_name: $details"
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
    [[ "$priority" == "recovery" ]] && emoji="✅"

    curl -s -X POST "https://api.telegram.org/bot${ERRORS_BOT_TOKEN}/sendMessage" \
        -d "chat_id=${ERRORS_CHAT_ID}" \
        -d "text=${emoji} LECTIO ULTIMATE CHECK

$message

🕐 $(date '+%Y-%m-%d %H:%M:%S')
🖥️ Server: $(hostname)" \
        > /dev/null 2>&1 || true
}

# ==================== HTTP HELPERS ====================
http_get() {
    local url="$1"
    local token="${2:-}"
    local timeout="${3:-15}"
    
    local response
    response=$(curl -s -o /tmp/ult_body.json -w "%{http_code}|%{time_total}" \
        --max-time "$timeout" \
        --connect-timeout 5 \
        -H "Authorization: Bearer $token" \
        "$url" 2>/dev/null) || response="000|0"
    
    echo "$response"
}

http_post_json() {
    local url="$1"
    local data="$2"
    local token="${3:-}"
    local timeout="${4:-15}"
    
    local response
    response=$(curl -s -o /tmp/ult_body.json -w "%{http_code}|%{time_total}" \
        --max-time "$timeout" \
        --connect-timeout 5 \
        -X POST \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $token" \
        -d "$data" \
        "$url" 2>/dev/null) || response="000|0"
    
    echo "$response"
}

get_token_via_api() {
    local email="$1"
    local password="$2"
    
    local response
    response=$(curl -s -o /tmp/ult_token.json -w "%{http_code}" \
        --max-time 10 \
        -X POST \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"$email\",\"password\":\"$password\"}" \
        "${BACKEND_URL}/api/jwt/token/" 2>/dev/null) || response="000"
    
    if [[ "$response" == "200" ]]; then
        cat /tmp/ult_token.json | grep -o '"access":"[^"]*"' | cut -d'"' -f4
    else
        echo ""
    fi
}

# ==================== 1. ИНФРАСТРУКТУРА ====================

check_infra_disk() {
    local usage=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')
    if [[ "$usage" -lt 80 ]]; then
        log_result "INFRA" "Disk Space" "OK" "${usage}% used"
    elif [[ "$usage" -lt 90 ]]; then
        log_result "INFRA" "Disk Space" "WARN" "${usage}% used (warning)"
    else
        log_result "INFRA" "Disk Space" "FAIL" "${usage}% used (CRITICAL)"
    fi
}

check_infra_memory() {
    local usage=$(free | awk '/Mem:/ {printf "%.0f", $3/$2 * 100}')
    local available=$(free -m | awk '/Mem:/ {print $7}')
    if [[ "$usage" -lt 80 ]]; then
        log_result "INFRA" "Memory" "OK" "${usage}% used, ${available}MB available"
    elif [[ "$usage" -lt 90 ]]; then
        log_result "INFRA" "Memory" "WARN" "${usage}% used (warning)"
    else
        log_result "INFRA" "Memory" "FAIL" "${usage}% used (CRITICAL)"
    fi
}

check_infra_cpu() {
    local load=$(uptime | awk -F'load average:' '{print $2}' | awk -F',' '{print $1}' | xargs)
    local cores=$(nproc 2>/dev/null || echo "1")
    local load_int=$(echo "$load" | cut -d'.' -f1)
    
    if [[ "$load_int" -lt "$cores" ]]; then
        log_result "INFRA" "CPU Load" "OK" "Load: $load (cores: $cores)"
    elif [[ "$load_int" -lt $((cores * 2)) ]]; then
        log_result "INFRA" "CPU Load" "WARN" "Load: $load (high)"
    else
        log_result "INFRA" "CPU Load" "FAIL" "Load: $load (CRITICAL)"
    fi
}

check_infra_nginx() {
    if systemctl is-active --quiet nginx; then
        local config_test=$(nginx -t 2>&1)
        if echo "$config_test" | grep -q "syntax is ok"; then
            log_result "INFRA" "Nginx" "OK" "Running, config valid"
        else
            log_result "INFRA" "Nginx" "WARN" "Running, config issues"
        fi
    else
        log_result "INFRA" "Nginx" "FAIL" "Not running!"
    fi
}

check_infra_gunicorn() {
    local workers=$(pgrep -c -f "gunicorn.*teaching_panel" 2>/dev/null || echo "0")
    if [[ "$workers" -gt 0 ]]; then
        log_result "INFRA" "Gunicorn" "OK" "$workers workers running"
    else
        log_result "INFRA" "Gunicorn" "FAIL" "No workers found!"
    fi
}

check_infra_redis() {
    local result=$(redis-cli ping 2>/dev/null || echo "FAIL")
    if [[ "$result" == "PONG" ]]; then
        local keys=$(redis-cli dbsize 2>/dev/null | awk '{print $2}')
        log_result "INFRA" "Redis" "OK" "Running, $keys keys"
    else
        log_result "INFRA" "Redis" "FAIL" "Not responding"
    fi
}

check_infra_postgres() {
    # Проверяем PostgreSQL если используется
    if command -v psql &> /dev/null; then
        if pg_isready -q 2>/dev/null; then
            log_result "INFRA" "PostgreSQL" "OK" "Running"
        else
            log_result "INFRA" "PostgreSQL" "WARN" "Not responding or not used"
        fi
    else
        log_result "INFRA" "PostgreSQL" "SKIP" "Not installed (using SQLite?)"
    fi
}

check_infra_celery() {
    # Celery может быть отключен
    if systemctl is-active --quiet celery 2>/dev/null; then
        log_result "INFRA" "Celery" "OK" "Running"
    else
        log_result "INFRA" "Celery" "SKIP" "Disabled or not installed"
    fi
}

check_infra_logs_errors() {
    # Проверяем последние ошибки в логах
    local error_count=0
    
    if [[ -f "/var/log/nginx/error.log" ]]; then
        error_count=$((error_count + $(tail -100 /var/log/nginx/error.log 2>/dev/null | grep -c "error\|crit\|emerg" || echo "0")))
    fi
    
    local journal_errors=$(journalctl -u teaching_panel --since "1 hour ago" 2>/dev/null | grep -c "ERROR\|CRITICAL" || echo "0")
    error_count=$((error_count + journal_errors))
    
    if [[ "$error_count" -lt 5 ]]; then
        log_result "INFRA" "Recent Errors" "OK" "$error_count errors in last hour"
    elif [[ "$error_count" -lt 20 ]]; then
        log_result "INFRA" "Recent Errors" "WARN" "$error_count errors in last hour"
    else
        log_result "INFRA" "Recent Errors" "FAIL" "$error_count errors in last hour (HIGH)"
    fi
}

# ==================== 2. СЕТЬ И SSL ====================

check_network_ssl() {
    local domain=$(echo "$SITE_URL" | sed 's|https://||' | sed 's|/.*||')
    local expiry=$(echo | openssl s_client -servername "$domain" -connect "$domain:443" 2>/dev/null | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)
    
    if [[ -z "$expiry" ]]; then
        log_result "NETWORK" "SSL Certificate" "FAIL" "Cannot check SSL"
        return
    fi
    
    local expiry_ts=$(date -d "$expiry" +%s 2>/dev/null || echo "0")
    local now_ts=$(date +%s)
    local days_left=$(( (expiry_ts - now_ts) / 86400 ))
    
    if [[ "$days_left" -gt 30 ]]; then
        log_result "NETWORK" "SSL Certificate" "OK" "${days_left} days until expiry"
    elif [[ "$days_left" -gt 7 ]]; then
        log_result "NETWORK" "SSL Certificate" "WARN" "${days_left} days - renew soon!"
    else
        log_result "NETWORK" "SSL Certificate" "FAIL" "${days_left} days - RENEW NOW!"
    fi
}

check_network_dns() {
    local domain=$(echo "$SITE_URL" | sed 's|https://||' | sed 's|/.*||')
    local ip=$(dig +short "$domain" 2>/dev/null | head -1)
    
    if [[ -n "$ip" ]]; then
        log_result "NETWORK" "DNS Resolution" "OK" "$domain -> $ip"
    else
        log_result "NETWORK" "DNS Resolution" "FAIL" "DNS resolution failed"
    fi
}

check_network_https_redirect() {
    local http_url=$(echo "$SITE_URL" | sed 's|https://|http://|')
    local response=$(curl -sI -o /dev/null -w "%{http_code}|%{redirect_url}" --max-time 5 "$http_url" 2>/dev/null)
    local code="${response%%|*}"
    local redirect="${response##*|}"
    
    if [[ "$code" == "301" || "$code" == "302" ]] && echo "$redirect" | grep -q "https://"; then
        log_result "NETWORK" "HTTPS Redirect" "OK" "HTTP -> HTTPS works"
    else
        log_result "NETWORK" "HTTPS Redirect" "WARN" "HTTP redirect may not work (code: $code)"
    fi
}

check_network_security_headers() {
    local headers=$(curl -sI "${SITE_URL}/" --max-time 5 2>/dev/null)
    local issues=""
    
    echo "$headers" | grep -qi "X-Frame-Options" || issues="${issues}X-Frame-Options, "
    echo "$headers" | grep -qi "X-Content-Type-Options" || issues="${issues}X-Content-Type, "
    echo "$headers" | grep -qi "X-XSS-Protection" || issues="${issues}XSS-Protection, "
    
    if [[ -z "$issues" ]]; then
        log_result "NETWORK" "Security Headers" "OK" "All present"
    else
        log_result "NETWORK" "Security Headers" "WARN" "Missing: ${issues%, }"
    fi
}

# ==================== 3. БАЗА ДАННЫХ ====================

check_db_connectivity() {
    cd "${PROJECT_ROOT}/teaching_panel"
    
    local result
    result=$($PYTHON -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
import django
django.setup()

from django.db import connection
try:
    with connection.cursor() as cursor:
        cursor.execute('SELECT 1')
    print('OK')
except Exception as e:
    print(f'FAIL:{str(e)[:50]}')
" 2>&1 | tail -1)
    
    if [[ "$result" == "OK" ]]; then
        log_result "DATABASE" "Connectivity" "OK" "Database responding"
    else
        log_result "DATABASE" "Connectivity" "FAIL" "$result"
    fi
}

check_db_orphaned_students() {
    cd "${PROJECT_ROOT}/teaching_panel"
    
    local result
    result=$($PYTHON -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
import django
django.setup()

from accounts.models import CustomUser
from schedule.models import Group

students = CustomUser.objects.filter(role='student', is_active=True)
orphaned = 0
for s in students:
    if s.enrolled_groups.count() == 0:
        orphaned += 1

total = students.count()
percent = (orphaned / total * 100) if total > 0 else 0
print(f'{orphaned}|{total}|{percent:.1f}')
" 2>&1 | tail -1)
    
    local orphaned=$(echo "$result" | cut -d'|' -f1)
    local total=$(echo "$result" | cut -d'|' -f2)
    local percent=$(echo "$result" | cut -d'|' -f3)
    
    if (( $(echo "$percent < 10" | bc -l 2>/dev/null || echo "1") )); then
        log_result "DATABASE" "Orphaned Students" "OK" "$orphaned of $total (${percent}%)"
    elif (( $(echo "$percent < 30" | bc -l 2>/dev/null || echo "1") )); then
        log_result "DATABASE" "Orphaned Students" "WARN" "$orphaned of $total (${percent}%) without groups"
    else
        log_result "DATABASE" "Orphaned Students" "FAIL" "$orphaned of $total (${percent}%) - data loss?"
    fi
}

check_db_lessons_without_groups() {
    cd "${PROJECT_ROOT}/teaching_panel"
    
    local result
    result=$($PYTHON -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
import django
django.setup()

from schedule.models import Lesson

orphaned = Lesson.objects.filter(group__isnull=True).count()
total = Lesson.objects.count()
print(f'{orphaned}|{total}')
" 2>&1 | tail -1)
    
    local orphaned=$(echo "$result" | cut -d'|' -f1)
    local total=$(echo "$result" | cut -d'|' -f2)
    
    if [[ "$orphaned" == "0" ]]; then
        log_result "DATABASE" "Lessons Without Groups" "OK" "All $total lessons have groups"
    else
        log_result "DATABASE" "Lessons Without Groups" "WARN" "$orphaned of $total lessons without groups"
    fi
}

check_db_recordings_without_files() {
    cd "${PROJECT_ROOT}/teaching_panel"
    
    local result
    result=$($PYTHON -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
import django
django.setup()

from schedule.models import LessonRecording

# Записи без файлов (без gdrive_file_id и без download_url)
orphaned = LessonRecording.objects.filter(
    gdrive_file_id='',
    download_url=''
).count()
total = LessonRecording.objects.count()
print(f'{orphaned}|{total}')
" 2>&1 | tail -1)
    
    local orphaned=$(echo "$result" | cut -d'|' -f1)
    local total=$(echo "$result" | cut -d'|' -f2)
    
    if [[ "$orphaned" == "0" ]]; then
        log_result "DATABASE" "Recordings Without Files" "OK" "All $total recordings have files"
    elif [[ "$orphaned" -lt 5 ]]; then
        log_result "DATABASE" "Recordings Without Files" "WARN" "$orphaned of $total recordings missing files"
    else
        log_result "DATABASE" "Recordings Without Files" "FAIL" "$orphaned of $total recordings missing files!"
    fi
}

check_db_pending_payments() {
    cd "${PROJECT_ROOT}/teaching_panel"
    
    local result
    result=$($PYTHON -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
import django
django.setup()

from accounts.models import Payment
from django.utils import timezone
from datetime import timedelta

# Платежи pending более 1 часа
one_hour_ago = timezone.now() - timedelta(hours=1)
stuck = Payment.objects.filter(
    status='pending',
    created_at__lt=one_hour_ago
).count()

total_pending = Payment.objects.filter(status='pending').count()
print(f'{stuck}|{total_pending}')
" 2>&1 | tail -1)
    
    local stuck=$(echo "$result" | cut -d'|' -f1)
    local total=$(echo "$result" | cut -d'|' -f2)
    
    if [[ "$stuck" == "0" ]]; then
        log_result "DATABASE" "Stuck Payments" "OK" "No stuck payments ($total pending)"
    else
        log_result "DATABASE" "Stuck Payments" "WARN" "$stuck payments stuck >1 hour"
    fi
}

check_db_expired_subscriptions() {
    cd "${PROJECT_ROOT}/teaching_panel"
    
    local result
    result=$($PYTHON -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
import django
django.setup()

from accounts.models import Subscription
from django.utils import timezone

# Подписки с status=active но expires_at в прошлом
expired_but_active = Subscription.objects.filter(
    status='active',
    expires_at__lt=timezone.now()
).count()

active = Subscription.objects.filter(status='active').count()
print(f'{expired_but_active}|{active}')
" 2>&1 | tail -1)
    
    local expired=$(echo "$result" | cut -d'|' -f1)
    local active=$(echo "$result" | cut -d'|' -f2)
    
    if [[ "$expired" == "0" ]]; then
        log_result "DATABASE" "Subscription Status Sync" "OK" "$active active subscriptions valid"
    else
        log_result "DATABASE" "Subscription Status Sync" "FAIL" "$expired subscriptions marked active but expired!"
    fi
}

check_db_homework_without_teacher() {
    cd "${PROJECT_ROOT}/teaching_panel"
    
    local result
    result=$($PYTHON -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
import django
django.setup()

from homework.models import Homework

orphaned = Homework.objects.filter(teacher__isnull=True).count()
total = Homework.objects.count()
print(f'{orphaned}|{total}')
" 2>&1 | tail -1)
    
    local orphaned=$(echo "$result" | cut -d'|' -f1)
    local total=$(echo "$result" | cut -d'|' -f2)
    
    if [[ "$orphaned" == "0" ]]; then
        log_result "DATABASE" "Homework Integrity" "OK" "All $total homeworks have teachers"
    else
        log_result "DATABASE" "Homework Integrity" "FAIL" "$orphaned homeworks without teacher!"
    fi
}

# ==================== 4. АВТОРИЗАЦИЯ ====================

check_auth_jwt_login_teacher() {
    local token=$(get_token_via_api "$SMOKE_TEACHER_EMAIL" "$SMOKE_TEACHER_PASSWORD")
    
    if [[ -n "$token" ]]; then
        log_result "AUTH" "Teacher JWT Login" "OK" "Token obtained"
        echo "$token"
    else
        log_result "AUTH" "Teacher JWT Login" "FAIL" "Cannot get token"
        echo ""
    fi
}

check_auth_jwt_login_student() {
    local token=$(get_token_via_api "$SMOKE_STUDENT_EMAIL" "$SMOKE_STUDENT_PASSWORD")
    
    if [[ -n "$token" ]]; then
        log_result "AUTH" "Student JWT Login" "OK" "Token obtained"
        echo "$token"
    else
        log_result "AUTH" "Student JWT Login" "FAIL" "Cannot get token"
        echo ""
    fi
}

check_auth_token_refresh() {
    local refresh_token=$(cat /tmp/ult_token.json 2>/dev/null | grep -o '"refresh":"[^"]*"' | cut -d'"' -f4)
    
    if [[ -z "$refresh_token" ]]; then
        log_result "AUTH" "Token Refresh" "SKIP" "No refresh token available"
        return
    fi
    
    local result=$(http_post_json "${BACKEND_URL}/api/jwt/refresh/" "{\"refresh\":\"$refresh_token\"}")
    local code="${result%%|*}"
    
    if [[ "$code" == "200" ]]; then
        log_result "AUTH" "Token Refresh" "OK" "Refresh works"
    else
        log_result "AUTH" "Token Refresh" "FAIL" "HTTP $code"
    fi
}

check_auth_me_endpoint() {
    local token="$1"
    
    if [[ -z "$token" ]]; then
        log_result "AUTH" "/api/me/" "SKIP" "No token"
        return
    fi
    
    local result=$(http_get "${BACKEND_URL}/api/me/" "$token")
    local code="${result%%|*}"
    local time="${result##*|}"
    
    if [[ "$code" == "200" ]]; then
        log_result "AUTH" "/api/me/" "OK" "Response in ${time}s"
    else
        log_result "AUTH" "/api/me/" "FAIL" "HTTP $code"
    fi
}

check_auth_invalid_token() {
    local result=$(http_get "${BACKEND_URL}/api/me/" "invalid_token_12345")
    local code="${result%%|*}"
    
    if [[ "$code" == "401" ]]; then
        log_result "AUTH" "Invalid Token Rejection" "OK" "401 returned correctly"
    else
        log_result "AUTH" "Invalid Token Rejection" "WARN" "Expected 401, got $code"
    fi
}

# ==================== 5. API ENDPOINTS ====================

check_api_health() {
    local result=$(http_get "${BACKEND_URL}/api/health/")
    local code="${result%%|*}"
    local time="${result##*|}"
    
    if [[ "$code" == "200" ]]; then
        if grep -q '"database":true\|"database": true' /tmp/ult_body.json 2>/dev/null; then
            log_result "API" "/api/health/" "OK" "All systems OK (${time}s)"
        else
            log_result "API" "/api/health/" "WARN" "Response OK but DB check missing"
        fi
    else
        log_result "API" "/api/health/" "FAIL" "HTTP $code"
    fi
}

check_api_lessons() {
    local token="$1"
    local result=$(http_get "${BACKEND_URL}/api/schedule/lessons/" "$token")
    local code="${result%%|*}"
    local time="${result##*|}"
    
    if [[ "$code" == "200" ]]; then
        if (( $(echo "$time > 5.0" | bc -l 2>/dev/null || echo "0") )); then
            log_result "API" "Lessons List" "WARN" "Slow: ${time}s"
        else
            log_result "API" "Lessons List" "OK" "${time}s"
        fi
    else
        log_result "API" "Lessons List" "FAIL" "HTTP $code"
    fi
}

check_api_groups() {
    local token="$1"
    local result=$(http_get "${BACKEND_URL}/api/groups/" "$token")
    local code="${result%%|*}"
    
    if [[ "$code" == "200" ]]; then
        log_result "API" "Groups List" "OK" "Working"
    else
        log_result "API" "Groups List" "FAIL" "HTTP $code"
    fi
}

check_api_students() {
    local token="$1"
    local result=$(http_get "${BACKEND_URL}/api/students/" "$token")
    local code="${result%%|*}"
    
    if [[ "$code" == "200" ]]; then
        log_result "API" "Students List" "OK" "Working"
    else
        log_result "API" "Students List" "FAIL" "HTTP $code"
    fi
}

check_api_recordings() {
    local token="$1"
    local result=$(http_get "${BACKEND_URL}/schedule/api/recordings/teacher/" "$token")
    local code="${result%%|*}"
    
    if [[ "$code" == "200" ]]; then
        log_result "API" "Recordings List" "OK" "Working"
    else
        log_result "API" "Recordings List" "FAIL" "HTTP $code"
    fi
}

check_api_homework() {
    local token="$1"
    local result=$(http_get "${BACKEND_URL}/api/homework/" "$token")
    local code="${result%%|*}"
    
    if [[ "$code" == "200" ]]; then
        log_result "API" "Homework List" "OK" "Working"
    else
        log_result "API" "Homework List" "FAIL" "HTTP $code"
    fi
}

check_api_subscription() {
    local token="$1"
    local result=$(http_get "${BACKEND_URL}/api/subscription/" "$token")
    local code="${result%%|*}"
    
    if [[ "$code" == "200" ]]; then
        log_result "API" "Subscription" "OK" "Working"
    else
        log_result "API" "Subscription" "FAIL" "HTTP $code"
    fi
}

check_api_analytics() {
    local token="$1"
    local result=$(http_get "${BACKEND_URL}/api/analytics/teacher/stats/" "$token")
    local code="${result%%|*}"
    
    if [[ "$code" == "200" ]]; then
        log_result "API" "Analytics" "OK" "Working"
    elif [[ "$code" == "403" ]]; then
        log_result "API" "Analytics" "OK" "403 (requires subscription)"
    else
        log_result "API" "Analytics" "FAIL" "HTTP $code"
    fi
}

# ==================== 6. ПЛАТЕЖИ ====================

check_payment_yookassa_api() {
    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" \
        --max-time 10 \
        "https://api.yookassa.ru/v3/payments" 2>/dev/null) || http_code="000"
    
    if [[ "$http_code" == "401" || "$http_code" == "200" ]]; then
        log_result "PAYMENTS" "YooKassa API" "OK" "Reachable (HTTP $http_code)"
    else
        log_result "PAYMENTS" "YooKassa API" "FAIL" "Unreachable (HTTP $http_code)"
    fi
}

check_payment_tbank_api() {
    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" \
        --max-time 10 \
        "https://securepay.tinkoff.ru/v2/Init" 2>/dev/null) || http_code="000"
    
    if [[ "$http_code" == "405" || "$http_code" == "200" || "$http_code" == "400" ]]; then
        log_result "PAYMENTS" "T-Bank API" "OK" "Reachable (HTTP $http_code)"
    else
        log_result "PAYMENTS" "T-Bank API" "FAIL" "Unreachable (HTTP $http_code)"
    fi
}

check_payment_webhook_yookassa() {
    # Проверяем что webhook endpoint доступен (без авторизации должен вернуть 400/405/403)
    local result=$(http_post_json "${BACKEND_URL}/api/payments/yookassa/webhook/" '{}')
    local code="${result%%|*}"
    
    # Ожидаем 400 (bad request) или 403 (forbidden) - это значит endpoint работает
    if [[ "$code" == "400" || "$code" == "403" || "$code" == "200" ]]; then
        log_result "PAYMENTS" "YooKassa Webhook" "OK" "Endpoint responding (HTTP $code)"
    else
        log_result "PAYMENTS" "YooKassa Webhook" "FAIL" "Endpoint not working (HTTP $code)"
    fi
}

check_payment_webhook_tbank() {
    local result=$(http_post_json "${BACKEND_URL}/api/payments/tbank/webhook/" '{}')
    local code="${result%%|*}"
    
    if [[ "$code" == "400" || "$code" == "403" || "$code" == "200" ]]; then
        log_result "PAYMENTS" "T-Bank Webhook" "OK" "Endpoint responding (HTTP $code)"
    else
        log_result "PAYMENTS" "T-Bank Webhook" "FAIL" "Endpoint not working (HTTP $code)"
    fi
}

check_payment_create_test() {
    local token="$1"
    
    # Пробуем создать тестовый платёж (должен вернуть URL или ошибку подписки)
    local result=$(http_post_json "${BACKEND_URL}/api/subscription/create-payment/" '{"plan":"monthly","provider":"tbank"}' "$token")
    local code="${result%%|*}"
    
    # 200/201 = платёж создан, 400 = уже есть подписка, 403 = нет прав
    if [[ "$code" == "200" || "$code" == "201" ]]; then
        log_result "PAYMENTS" "Payment Creation" "OK" "Payment can be created"
    elif [[ "$code" == "400" ]]; then
        # Проверяем что это ожидаемая ошибка
        if grep -q "subscription\|active\|уже" /tmp/ult_body.json 2>/dev/null; then
            log_result "PAYMENTS" "Payment Creation" "OK" "Already subscribed (expected)"
        else
            log_result "PAYMENTS" "Payment Creation" "WARN" "400 error (check response)"
        fi
    else
        log_result "PAYMENTS" "Payment Creation" "FAIL" "HTTP $code"
    fi
}

# ==================== 7. GOOGLE DRIVE ====================

check_gdrive_connection() {
    cd "${PROJECT_ROOT}/teaching_panel"
    
    local result
    result=$($PYTHON -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
import django
django.setup()

from django.conf import settings
if not getattr(settings, 'USE_GDRIVE_STORAGE', False):
    print('SKIP:GDrive disabled')
else:
    try:
        from schedule.gdrive_utils import get_gdrive_manager
        manager = get_gdrive_manager()
        
        about = manager.service.about().get(fields='user,storageQuota').execute()
        user = about.get('user', {}).get('emailAddress', 'unknown')
        print(f'OK:{user}')
    except Exception as e:
        print(f'FAIL:{str(e)[:80]}')
" 2>&1 | tail -1)
    
    local status="${result%%:*}"
    local details="${result#*:}"
    
    if [[ "$status" == "OK" ]]; then
        log_result "GDRIVE" "Connection" "OK" "Connected as $details"
    elif [[ "$status" == "SKIP" ]]; then
        log_result "GDRIVE" "Connection" "SKIP" "$details"
    else
        log_result "GDRIVE" "Connection" "FAIL" "$details"
    fi
}

check_gdrive_quota() {
    cd "${PROJECT_ROOT}/teaching_panel"
    
    local result
    result=$($PYTHON -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
import django
django.setup()

from django.conf import settings
if not getattr(settings, 'USE_GDRIVE_STORAGE', False):
    print('SKIP:GDrive disabled')
else:
    try:
        from schedule.gdrive_utils import get_gdrive_manager
        manager = get_gdrive_manager()
        
        about = manager.service.about().get(fields='storageQuota').execute()
        quota = about.get('storageQuota', {})
        
        limit = int(quota.get('limit', 0))
        usage = int(quota.get('usage', 0))
        
        if limit > 0:
            percent = usage / limit * 100
            limit_gb = limit / (1024**3)
            usage_gb = usage / (1024**3)
            print(f'{percent:.1f}|{usage_gb:.1f}|{limit_gb:.1f}')
        else:
            print('UNLIMITED|0|0')
    except Exception as e:
        print(f'FAIL:{str(e)[:80]}')
" 2>&1 | tail -1)
    
    if [[ "$result" == SKIP:* ]]; then
        log_result "GDRIVE" "Quota" "SKIP" "${result#SKIP:}"
    elif [[ "$result" == FAIL:* ]]; then
        log_result "GDRIVE" "Quota" "FAIL" "${result#FAIL:}"
    elif [[ "$result" == UNLIMITED* ]]; then
        log_result "GDRIVE" "Quota" "OK" "Unlimited storage"
    else
        local percent=$(echo "$result" | cut -d'|' -f1)
        local usage=$(echo "$result" | cut -d'|' -f2)
        local limit=$(echo "$result" | cut -d'|' -f3)
        
        if (( $(echo "$percent < 80" | bc -l 2>/dev/null || echo "1") )); then
            log_result "GDRIVE" "Quota" "OK" "${usage}GB / ${limit}GB (${percent}%)"
        elif (( $(echo "$percent < 95" | bc -l 2>/dev/null || echo "1") )); then
            log_result "GDRIVE" "Quota" "WARN" "${usage}GB / ${limit}GB (${percent}%) - running low"
        else
            log_result "GDRIVE" "Quota" "FAIL" "${usage}GB / ${limit}GB (${percent}%) - FULL!"
        fi
    fi
}

check_gdrive_root_folder() {
    cd "${PROJECT_ROOT}/teaching_panel"
    
    local result
    result=$($PYTHON -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
import django
django.setup()

from django.conf import settings
if not getattr(settings, 'USE_GDRIVE_STORAGE', False):
    print('SKIP:GDrive disabled')
else:
    try:
        from schedule.gdrive_utils import get_gdrive_manager
        manager = get_gdrive_manager()
        
        root_id = getattr(settings, 'GDRIVE_ROOT_FOLDER_ID', None)
        if not root_id:
            print('FAIL:GDRIVE_ROOT_FOLDER_ID not set')
        else:
            files = manager.service.files().list(
                q=f\"'{root_id}' in parents\",
                pageSize=5,
                fields='files(id, name)'
            ).execute()
            
            count = len(files.get('files', []))
            print(f'OK:{count} items in root')
    except Exception as e:
        print(f'FAIL:{str(e)[:80]}')
" 2>&1 | tail -1)
    
    local status="${result%%:*}"
    local details="${result#*:}"
    
    if [[ "$status" == "OK" ]]; then
        log_result "GDRIVE" "Root Folder" "OK" "$details"
    elif [[ "$status" == "SKIP" ]]; then
        log_result "GDRIVE" "Root Folder" "SKIP" "$details"
    else
        log_result "GDRIVE" "Root Folder" "FAIL" "$details"
    fi
}

# ==================== 8. ZOOM ====================

check_zoom_oauth() {
    cd "${PROJECT_ROOT}/teaching_panel"
    
    local result
    result=$($PYTHON -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
import django
django.setup()

from accounts.models import CustomUser

# Проверяем есть ли хотя бы один учитель с Zoom credentials
teachers = CustomUser.objects.filter(
    role='teacher',
    zoom_account_id__isnull=False,
).exclude(zoom_account_id='').exclude(zoom_account_id__in=['bad', 'test', 'invalid'])

if teachers.count() == 0:
    print('SKIP:No teachers with Zoom credentials')
else:
    # Пробуем получить токен для первого учителя
    teacher = teachers.first()
    try:
        from schedule.zoom_client import ZoomAPIClient
        client = ZoomAPIClient(
            account_id=teacher.zoom_account_id,
            client_id=teacher.zoom_client_id,
            client_secret=teacher.zoom_client_secret
        )
        token = client._get_access_token()
        if token and len(token) > 20:
            print(f'OK:Token obtained for {teacher.email}')
        else:
            print('FAIL:Empty token')
    except Exception as e:
        print(f'FAIL:{str(e)[:80]}')
" 2>&1 | tail -1)
    
    local status="${result%%:*}"
    local details="${result#*:}"
    
    if [[ "$status" == "OK" ]]; then
        log_result "ZOOM" "OAuth Token" "OK" "$details"
    elif [[ "$status" == "SKIP" ]]; then
        log_result "ZOOM" "OAuth Token" "SKIP" "$details"
    else
        log_result "ZOOM" "OAuth Token" "FAIL" "$details"
    fi
}

check_zoom_api_availability() {
    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" \
        --max-time 10 \
        "https://api.zoom.us/v2/users/me" 2>/dev/null) || http_code="000"
    
    # 401 = API работает, просто нет авторизации
    if [[ "$http_code" == "401" || "$http_code" == "200" ]]; then
        log_result "ZOOM" "API Availability" "OK" "Reachable (HTTP $http_code)"
    else
        log_result "ZOOM" "API Availability" "FAIL" "Unreachable (HTTP $http_code)"
    fi
}

# ==================== 9. TELEGRAM ====================

check_telegram_bot() {
    if [[ -z "$ERRORS_BOT_TOKEN" ]]; then
        log_result "TELEGRAM" "Bot Token" "SKIP" "Not configured"
        return
    fi
    
    local response
    response=$(curl -s --max-time 10 \
        "https://api.telegram.org/bot${ERRORS_BOT_TOKEN}/getMe" 2>/dev/null)
    
    if echo "$response" | grep -q '"ok":true'; then
        local bot_name=$(echo "$response" | grep -o '"username":"[^"]*"' | cut -d'"' -f4)
        log_result "TELEGRAM" "Bot Status" "OK" "@$bot_name working"
    else
        log_result "TELEGRAM" "Bot Status" "FAIL" "Bot not responding"
    fi
}

check_telegram_send_test() {
    if [[ -z "$ERRORS_BOT_TOKEN" ]] || [[ -z "$ERRORS_CHAT_ID" ]]; then
        log_result "TELEGRAM" "Send Test" "SKIP" "Not configured"
        return
    fi
    
    # Не отправляем реально, просто проверяем что chat_id валидный
    local response
    response=$(curl -s --max-time 10 \
        "https://api.telegram.org/bot${ERRORS_BOT_TOKEN}/getChat?chat_id=${ERRORS_CHAT_ID}" 2>/dev/null)
    
    if echo "$response" | grep -q '"ok":true'; then
        log_result "TELEGRAM" "Chat Access" "OK" "Can access chat"
    else
        log_result "TELEGRAM" "Chat Access" "FAIL" "Cannot access chat"
    fi
}

# ==================== 10. СТАТИКА ====================

check_static_manifest() {
    local result=$(http_get "${SITE_URL}/asset-manifest.json")
    local code="${result%%|*}"
    
    if [[ "$code" == "200" ]]; then
        log_result "STATIC" "Asset Manifest" "OK" "Present"
    else
        log_result "STATIC" "Asset Manifest" "FAIL" "HTTP $code"
    fi
}

check_static_index() {
    local result=$(http_get "${SITE_URL}/")
    local code="${result%%|*}"
    
    if [[ "$code" == "200" ]]; then
        if grep -q "root\|React\|bundle" /tmp/ult_body.json 2>/dev/null; then
            log_result "STATIC" "Index HTML" "OK" "React app loaded"
        else
            log_result "STATIC" "Index HTML" "WARN" "HTML present but React markers missing"
        fi
    else
        log_result "STATIC" "Index HTML" "FAIL" "HTTP $code"
    fi
}

check_static_build_date() {
    local build_dir="${PROJECT_ROOT}/frontend/build"
    
    if [[ -d "$build_dir" ]]; then
        local build_date=$(stat -c %Y "$build_dir/index.html" 2>/dev/null || echo "0")
        local now=$(date +%s)
        local age_days=$(( (now - build_date) / 86400 ))
        
        if [[ "$age_days" -lt 7 ]]; then
            log_result "STATIC" "Build Age" "OK" "${age_days} days old"
        elif [[ "$age_days" -lt 30 ]]; then
            log_result "STATIC" "Build Age" "WARN" "${age_days} days old"
        else
            log_result "STATIC" "Build Age" "WARN" "${age_days} days old (consider rebuild)"
        fi
    else
        log_result "STATIC" "Build Age" "FAIL" "Build directory not found"
    fi
}

# ==================== MAIN ====================

run_ultimate_check() {
    echo "========================================" | tee "$REPORT_FILE"
    echo "LECTIO ULTIMATE HEALTH CHECK" | tee -a "$REPORT_FILE"
    echo "Started: $(date '+%Y-%m-%d %H:%M:%S')" | tee -a "$REPORT_FILE"
    echo "========================================" | tee -a "$REPORT_FILE"
    echo "" | tee -a "$REPORT_FILE"
    
    # 1. ИНФРАСТРУКТУРА
    echo "=== 1. INFRASTRUCTURE ===" | tee -a "$REPORT_FILE"
    check_infra_disk
    check_infra_memory
    check_infra_cpu
    check_infra_nginx
    check_infra_gunicorn
    check_infra_redis
    check_infra_postgres
    check_infra_celery
    check_infra_logs_errors
    echo "" | tee -a "$REPORT_FILE"
    
    # 2. СЕТЬ
    echo "=== 2. NETWORK & SSL ===" | tee -a "$REPORT_FILE"
    check_network_ssl
    check_network_dns
    check_network_https_redirect
    check_network_security_headers
    echo "" | tee -a "$REPORT_FILE"
    
    # 3. БАЗА ДАННЫХ
    echo "=== 3. DATABASE ===" | tee -a "$REPORT_FILE"
    check_db_connectivity
    check_db_orphaned_students
    check_db_lessons_without_groups
    check_db_recordings_without_files
    check_db_pending_payments
    check_db_expired_subscriptions
    check_db_homework_without_teacher
    echo "" | tee -a "$REPORT_FILE"
    
    # 4. АВТОРИЗАЦИЯ
    echo "=== 4. AUTHENTICATION ===" | tee -a "$REPORT_FILE"
    local teacher_token=$(check_auth_jwt_login_teacher)
    local student_token=$(check_auth_jwt_login_student)
    check_auth_token_refresh
    check_auth_me_endpoint "$teacher_token"
    check_auth_invalid_token
    echo "" | tee -a "$REPORT_FILE"
    
    # 5. API
    echo "=== 5. API ENDPOINTS ===" | tee -a "$REPORT_FILE"
    check_api_health
    if [[ -n "$teacher_token" ]]; then
        check_api_lessons "$teacher_token"
        check_api_groups "$teacher_token"
        check_api_students "$teacher_token"
        check_api_recordings "$teacher_token"
        check_api_homework "$teacher_token"
        check_api_subscription "$teacher_token"
        check_api_analytics "$teacher_token"
    fi
    echo "" | tee -a "$REPORT_FILE"
    
    # 6. ПЛАТЕЖИ
    echo "=== 6. PAYMENTS ===" | tee -a "$REPORT_FILE"
    check_payment_yookassa_api
    check_payment_tbank_api
    check_payment_webhook_yookassa
    check_payment_webhook_tbank
    if [[ -n "$teacher_token" ]]; then
        check_payment_create_test "$teacher_token"
    fi
    echo "" | tee -a "$REPORT_FILE"
    
    # 7. GOOGLE DRIVE
    echo "=== 7. GOOGLE DRIVE ===" | tee -a "$REPORT_FILE"
    check_gdrive_connection
    check_gdrive_quota
    check_gdrive_root_folder
    echo "" | tee -a "$REPORT_FILE"
    
    # 8. ZOOM
    echo "=== 8. ZOOM ===" | tee -a "$REPORT_FILE"
    check_zoom_oauth
    check_zoom_api_availability
    echo "" | tee -a "$REPORT_FILE"
    
    # 9. TELEGRAM
    echo "=== 9. TELEGRAM ===" | tee -a "$REPORT_FILE"
    check_telegram_bot
    check_telegram_send_test
    echo "" | tee -a "$REPORT_FILE"
    
    # 10. СТАТИКА
    echo "=== 10. STATIC FILES ===" | tee -a "$REPORT_FILE"
    check_static_manifest
    check_static_index
    check_static_build_date
    echo "" | tee -a "$REPORT_FILE"
    
    # ==================== ИТОГ ====================
    echo "========================================" | tee -a "$REPORT_FILE"
    echo "SUMMARY" | tee -a "$REPORT_FILE"
    echo "========================================" | tee -a "$REPORT_FILE"
    
    local total=$((OK_COUNT + WARNING_COUNT + CRITICAL_COUNT + SKIP_COUNT))
    
    echo "Total tests: $total" | tee -a "$REPORT_FILE"
    echo "  OK:       $OK_COUNT" | tee -a "$REPORT_FILE"
    echo "  WARNINGS: $WARNING_COUNT" | tee -a "$REPORT_FILE"
    echo "  FAILURES: $CRITICAL_COUNT" | tee -a "$REPORT_FILE"
    echo "  SKIPPED:  $SKIP_COUNT" | tee -a "$REPORT_FILE"
    echo "" | tee -a "$REPORT_FILE"
    
    # Отправляем алерт если есть критические проблемы
    if [[ $CRITICAL_COUNT -gt 0 ]]; then
        echo "STATUS: CRITICAL - $CRITICAL_COUNT failures detected!" | tee -a "$REPORT_FILE"
        
        # Собираем список проблем
        local issues=""
        for key in "${!RESULTS[@]}"; do
            local value="${RESULTS[$key]}"
            local status="${value%%|*}"
            local details="${value#*|}"
            if [[ "$status" == "FAIL" ]]; then
                local test_name="${key#*::}"
                issues="${issues}• ${test_name}: ${details}\n"
            fi
        done
        
        send_telegram "КРИТИЧЕСКИЕ ПРОБЛЕМЫ (${CRITICAL_COUNT}):

$(echo -e "$issues")

Всего проверок: $total
Предупреждений: $WARNING_COUNT" "critical"
        
    elif [[ $WARNING_COUNT -gt 5 ]]; then
        echo "STATUS: WARNING - $WARNING_COUNT warnings" | tee -a "$REPORT_FILE"
        
        send_telegram "Много предупреждений: $WARNING_COUNT

Всего проверок: $total
Провалов: $CRITICAL_COUNT" "high"
    else
        echo "STATUS: OK - All systems operational" | tee -a "$REPORT_FILE"
        
        # Опциональное уведомление об успехе (включается через --notify-success или NOTIFY_SUCCESS=1)
        if [[ "$NOTIFY_SUCCESS" == "1" ]]; then
            send_telegram "Все системы работают нормально!

Проверок: $total
OK: $OK_COUNT
Предупреждений: $WARNING_COUNT
Пропущено: $SKIP_COUNT" "recovery"
        fi
    fi
    
    echo "" | tee -a "$REPORT_FILE"
    echo "Report saved to: $REPORT_FILE" | tee -a "$REPORT_FILE"
    echo "Completed: $(date '+%Y-%m-%d %H:%M:%S')" | tee -a "$REPORT_FILE"
    
    return $CRITICAL_COUNT
}

main() {
    # Обработка аргументов командной строки
    for arg in "$@"; do
        case "$arg" in
            --notify-success)
                NOTIFY_SUCCESS=1
                ;;
            --help|-h)
                echo "Usage: $0 [--notify-success] [--help]"
                echo "  --notify-success   Send Telegram notification even when all tests pass"
                exit 0
                ;;
        esac
    done
    
    run_ultimate_check
    exit $?
}

main "$@"
