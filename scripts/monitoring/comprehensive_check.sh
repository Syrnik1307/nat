#!/bin/bash
# ============================================================
# LECTIO COMPREHENSIVE CHECK v1.0
# ============================================================
# Расширенная проверка всех компонентов системы.
# Включает тесты, не входящие в стандартный smoke_check.
#
# Расположение: /opt/lectio-monitor/comprehensive_check.sh
# Запуск: каждые 6 часов через cron или вручную
# ============================================================

set -uo pipefail

CONFIG_FILE="/opt/lectio-monitor/config.env"
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
fi

# ==================== КОНФИГУРАЦИЯ ====================
SITE_URL="${SITE_URL:-https://lectio.tw1.ru}"
BACKEND_URL="${BACKEND_URL:-https://lectio.tw1.ru}"
LOG_FILE="${LOG_FILE:-/var/log/lectio-monitor/comprehensive.log}"

SMOKE_TEACHER_EMAIL="${SMOKE_TEACHER_EMAIL:-smoke_teacher@test.local}"
SMOKE_TEACHER_PASSWORD="${SMOKE_TEACHER_PASSWORD:-SmokeTest123!}"
SMOKE_STUDENT_EMAIL="${SMOKE_STUDENT_EMAIL:-smoke_student@test.local}"
SMOKE_STUDENT_PASSWORD="${SMOKE_STUDENT_PASSWORD:-SmokeTest123!}"

ERRORS_BOT_TOKEN="${ERRORS_BOT_TOKEN:-}"
ERRORS_CHAT_ID="${ERRORS_CHAT_ID:-}"

mkdir -p "$(dirname "$LOG_FILE")"

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

# ==================== HTTP HELPERS ====================
http_get() {
    local url="$1"
    local token="${2:-}"
    local timeout="${3:-15}"
    
    local response
    response=$(curl -s -o /tmp/comp_body.json -w "%{http_code}|%{time_total}" \
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
    response=$(curl -s -o /tmp/comp_body.json -w "%{http_code}|%{time_total}" \
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
    response=$(curl -s -o /tmp/comp_token.json -w "%{http_code}" \
        --max-time 10 \
        -X POST \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"$email\",\"password\":\"$password\"}" \
        "${BACKEND_URL}/api/jwt/token/" 2>/dev/null) || response="000"
    
    if [[ "$response" == "200" ]]; then
        cat /tmp/comp_token.json | grep -o '"access":"[^"]*"' | cut -d'"' -f4
    else
        echo ""
    fi
}

# ==================== ТЕСТЫ ====================

# === Инфраструктурные тесты ===

test_nginx_config() {
    log_info "Testing: Nginx configuration"
    nginx -t 2>&1 | grep -q "syntax is ok" && echo "OK" || echo "FAIL:Nginx config syntax error"
}

test_gunicorn_workers() {
    log_info "Testing: Gunicorn workers"
    local workers=$(pgrep -c -f "gunicorn.*teaching_panel" 2>/dev/null || echo "0")
    if [[ "$workers" -gt 0 ]]; then
        echo "OK:$workers workers"
    else
        echo "FAIL:No gunicorn workers running"
    fi
}

test_redis_connection() {
    log_info "Testing: Redis connection"
    local result=$(redis-cli ping 2>/dev/null || echo "FAIL")
    if [[ "$result" == "PONG" ]]; then
        echo "OK"
    else
        echo "FAIL:Redis not responding"
    fi
}

test_celery_workers() {
    log_info "Testing: Celery workers (if enabled)"
    # Celery удалён, но проверяем на всякий случай
    if systemctl is-active --quiet celery 2>/dev/null; then
        echo "OK:Celery active"
    else
        echo "SKIP:Celery disabled"
    fi
}

test_disk_space() {
    log_info "Testing: Disk space"
    local usage=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')
    if [[ "$usage" -lt 90 ]]; then
        echo "OK:${usage}% used"
    elif [[ "$usage" -lt 95 ]]; then
        echo "WARN:${usage}% used"
    else
        echo "FAIL:${usage}% used (critical)"
    fi
}

test_memory_usage() {
    log_info "Testing: Memory usage"
    local usage=$(free | awk '/Mem:/ {printf "%.0f", $3/$2 * 100}')
    if [[ "$usage" -lt 85 ]]; then
        echo "OK:${usage}% used"
    elif [[ "$usage" -lt 95 ]]; then
        echo "WARN:${usage}% used"
    else
        echo "FAIL:${usage}% used (critical)"
    fi
}

# === Сетевые тесты ===

test_ssl_certificate() {
    log_info "Testing: SSL certificate expiry"
    local domain=$(echo "$SITE_URL" | sed 's|https://||' | sed 's|/.*||')
    local expiry=$(echo | openssl s_client -servername "$domain" -connect "$domain:443" 2>/dev/null | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)
    
    if [[ -z "$expiry" ]]; then
        echo "FAIL:Cannot check SSL"
        return
    fi
    
    local expiry_ts=$(date -d "$expiry" +%s 2>/dev/null || echo "0")
    local now_ts=$(date +%s)
    local days_left=$(( (expiry_ts - now_ts) / 86400 ))
    
    if [[ "$days_left" -gt 30 ]]; then
        echo "OK:${days_left} days left"
    elif [[ "$days_left" -gt 7 ]]; then
        echo "WARN:${days_left} days left"
    else
        echo "FAIL:${days_left} days left (renew now!)"
    fi
}

test_dns_resolution() {
    log_info "Testing: DNS resolution"
    local domain=$(echo "$SITE_URL" | sed 's|https://||' | sed 's|/.*||')
    local ip=$(dig +short "$domain" 2>/dev/null | head -1)
    
    if [[ -n "$ip" ]]; then
        echo "OK:$ip"
    else
        echo "FAIL:DNS resolution failed"
    fi
}

# === API Endpoint тесты ===

test_api_health() {
    log_info "Testing: /api/health/"
    local result=$(http_get "${BACKEND_URL}/api/health/")
    local code="${result%%|*}"
    local time="${result##*|}"
    
    if [[ "$code" == "200" ]]; then
        echo "OK:${time}s"
    else
        echo "FAIL:HTTP $code"
    fi
}

test_api_me() {
    local token="$1"
    log_info "Testing: /api/me/"
    local result=$(http_get "${BACKEND_URL}/api/me/" "$token")
    local code="${result%%|*}"
    
    if [[ "$code" == "200" ]]; then
        echo "OK"
    else
        echo "FAIL:HTTP $code"
    fi
}

test_schedule_lessons() {
    local token="$1"
    log_info "Testing: /api/schedule/lessons/"
    local result=$(http_get "${BACKEND_URL}/api/schedule/lessons/" "$token")
    local code="${result%%|*}"
    local time="${result##*|}"
    
    if [[ "$code" == "200" ]]; then
        if (( $(echo "$time > 3.0" | bc -l) )); then
            echo "SLOW:HTTP 200 in ${time}s"
        else
            echo "OK:${time}s"
        fi
    else
        echo "FAIL:HTTP $code"
    fi
}

test_schedule_groups() {
    local token="$1"
    log_info "Testing: /api/groups/"
    local result=$(http_get "${BACKEND_URL}/api/groups/" "$token")
    local code="${result%%|*}"
    
    if [[ "$code" == "200" ]]; then
        echo "OK"
    else
        echo "FAIL:HTTP $code"
    fi
}

test_recordings_teacher() {
    local token="$1"
    log_info "Testing: /schedule/api/recordings/teacher/"
    local result=$(http_get "${BACKEND_URL}/schedule/api/recordings/teacher/" "$token")
    local code="${result%%|*}"
    
    if [[ "$code" == "200" ]]; then
        echo "OK"
    else
        echo "FAIL:HTTP $code"
    fi
}

test_homework_list() {
    local token="$1"
    log_info "Testing: /api/homework/"
    local result=$(http_get "${BACKEND_URL}/api/homework/" "$token")
    local code="${result%%|*}"
    
    if [[ "$code" == "200" ]]; then
        echo "OK"
    else
        echo "FAIL:HTTP $code"
    fi
}

test_subscription() {
    local token="$1"
    log_info "Testing: /api/subscription/"
    local result=$(http_get "${BACKEND_URL}/api/subscription/" "$token")
    local code="${result%%|*}"
    
    if [[ "$code" == "200" ]]; then
        echo "OK"
    else
        echo "FAIL:HTTP $code"
    fi
}

test_analytics_teacher_stats() {
    local token="$1"
    log_info "Testing: /api/analytics/teacher/stats/"
    local result=$(http_get "${BACKEND_URL}/api/analytics/teacher/stats/" "$token")
    local code="${result%%|*}"
    
    if [[ "$code" == "200" ]]; then
        echo "OK"
    elif [[ "$code" == "403" ]]; then
        echo "OK:requires subscription"
    else
        echo "FAIL:HTTP $code"
    fi
}

test_zoom_pool() {
    local token="$1"
    log_info "Testing: /api/zoom-pool/accounts/"
    local result=$(http_get "${BACKEND_URL}/api/zoom-pool/accounts/" "$token")
    local code="${result%%|*}"
    
    # Может требовать admin права
    if [[ "$code" == "200" || "$code" == "403" ]]; then
        echo "OK"
    else
        echo "FAIL:HTTP $code"
    fi
}

test_students_list() {
    local token="$1"
    log_info "Testing: /api/students/"
    local result=$(http_get "${BACKEND_URL}/api/students/" "$token")
    local code="${result%%|*}"
    
    if [[ "$code" == "200" ]]; then
        echo "OK"
    else
        echo "FAIL:HTTP $code"
    fi
}

# === Статические файлы ===

test_static_manifest() {
    log_info "Testing: asset-manifest.json"
    local result=$(http_get "${SITE_URL}/asset-manifest.json")
    local code="${result%%|*}"
    
    if [[ "$code" == "200" ]]; then
        echo "OK"
    else
        echo "FAIL:HTTP $code"
    fi
}

test_static_css() {
    log_info "Testing: Main CSS bundle"
    # Получаем путь из asset-manifest
    local css_path=$(cat /tmp/comp_body.json 2>/dev/null | grep -o '"main.css":"[^"]*"' | cut -d'"' -f4)
    
    if [[ -n "$css_path" ]]; then
        local result=$(http_get "${SITE_URL}${css_path}")
        local code="${result%%|*}"
        
        if [[ "$code" == "200" ]]; then
            echo "OK"
        else
            echo "FAIL:HTTP $code"
        fi
    else
        echo "SKIP:No CSS in manifest"
    fi
}

test_static_js() {
    log_info "Testing: Main JS bundle"
    local js_path=$(cat /tmp/comp_body.json 2>/dev/null | grep -o '"main.js":"[^"]*"' | cut -d'"' -f4)
    
    if [[ -n "$js_path" ]]; then
        local result=$(http_get "${SITE_URL}${js_path}")
        local code="${result%%|*}"
        
        if [[ "$code" == "200" ]]; then
            echo "OK"
        else
            echo "FAIL:HTTP $code"
        fi
    else
        echo "SKIP:No JS in manifest"
    fi
}

# === Безопасность ===

test_security_headers() {
    log_info "Testing: Security headers"
    local headers=$(curl -sI "${SITE_URL}/" 2>/dev/null)
    local issues=""
    
    if ! echo "$headers" | grep -qi "X-Frame-Options"; then
        issues="${issues}X-Frame-Options missing, "
    fi
    
    if ! echo "$headers" | grep -qi "X-Content-Type-Options"; then
        issues="${issues}X-Content-Type-Options missing, "
    fi
    
    if [[ -z "$issues" ]]; then
        echo "OK"
    else
        echo "WARN:${issues%%, }"
    fi
}

test_cors_preflight() {
    log_info "Testing: CORS preflight"
    local response=$(curl -sI -X OPTIONS "${BACKEND_URL}/api/health/" \
        -H "Origin: ${SITE_URL}" \
        -H "Access-Control-Request-Method: GET" 2>/dev/null)
    
    if echo "$response" | grep -qi "Access-Control-Allow"; then
        echo "OK"
    else
        echo "WARN:CORS headers missing"
    fi
}

test_rate_limiting() {
    log_info "Testing: Rate limiting (login endpoint)"
    local responses=""
    
    for i in {1..5}; do
        local code=$(curl -s -o /dev/null -w "%{http_code}" \
            -X POST \
            -H "Content-Type: application/json" \
            -d '{"email":"test@test.com","password":"wrong"}' \
            "${BACKEND_URL}/api/jwt/token/" 2>/dev/null)
        responses="${responses}${code},"
    done
    
    if echo "$responses" | grep -q "429"; then
        echo "OK:Rate limit active"
    else
        echo "WARN:Rate limit may not be configured"
    fi
}

# ==================== MAIN ====================
run_comprehensive_check() {
    local results=()
    local fails=0
    local warns=0
    local teacher_token=""
    local student_token=""
    
    log_info "=== Comprehensive Check START ==="
    
    # Инфраструктура
    results+=("$(test_disk_space)")
    results+=("$(test_memory_usage)")
    results+=("$(test_gunicorn_workers)")
    results+=("$(test_redis_connection)")
    results+=("$(test_celery_workers)")
    
    # Сеть
    results+=("$(test_ssl_certificate)")
    results+=("$(test_dns_resolution)")
    
    # API Health
    results+=("$(test_api_health)")
    
    # Статика
    results+=("$(test_static_manifest)")
    
    # Авторизация учителя
    teacher_token=$(get_token_via_api "$SMOKE_TEACHER_EMAIL" "$SMOKE_TEACHER_PASSWORD")
    if [[ -n "$teacher_token" ]]; then
        results+=("Teacher auth:OK")
        
        results+=("$(test_api_me "$teacher_token")")
        results+=("$(test_schedule_lessons "$teacher_token")")
        results+=("$(test_schedule_groups "$teacher_token")")
        results+=("$(test_recordings_teacher "$teacher_token")")
        results+=("$(test_homework_list "$teacher_token")")
        results+=("$(test_subscription "$teacher_token")")
        results+=("$(test_analytics_teacher_stats "$teacher_token")")
        results+=("$(test_students_list "$teacher_token")")
        results+=("$(test_zoom_pool "$teacher_token")")
    else
        results+=("Teacher auth:FAIL")
        ((fails++))
    fi
    
    # Авторизация студента
    student_token=$(get_token_via_api "$SMOKE_STUDENT_EMAIL" "$SMOKE_STUDENT_PASSWORD")
    if [[ -n "$student_token" ]]; then
        results+=("Student auth:OK")
        results+=("$(test_homework_list "$student_token")")
    else
        results+=("Student auth:FAIL")
        ((fails++))
    fi
    
    # Безопасность
    results+=("$(test_security_headers)")
    results+=("$(test_cors_preflight)")
    # results+=("$(test_rate_limiting)")  # Может вызвать проблемы
    
    # Подсчёт результатов
    for res in "${results[@]}"; do
        if [[ "$res" == *"FAIL"* ]]; then
            ((fails++))
        elif [[ "$res" == *"WARN"* || "$res" == *"SLOW"* ]]; then
            ((warns++))
        fi
        log_info "Result: $res"
    done
    
    log_info "=== Comprehensive Check COMPLETE ==="
    log_info "Summary: ${#results[@]} tests, $fails failures, $warns warnings"
    
    # Вывод для мониторинга
    echo ""
    echo "========================================"
    echo "COMPREHENSIVE CHECK RESULTS"
    echo "========================================"
    echo "Total tests: ${#results[@]}"
    echo "Failures: $fails"
    echo "Warnings: $warns"
    echo ""
    
    if [[ $fails -gt 0 ]]; then
        echo "FAILED TESTS:"
        for res in "${results[@]}"; do
            if [[ "$res" == *"FAIL"* ]]; then
                echo "  - $res"
            fi
        done
    fi
    
    if [[ $warns -gt 0 ]]; then
        echo ""
        echo "WARNINGS:"
        for res in "${results[@]}"; do
            if [[ "$res" == *"WARN"* || "$res" == *"SLOW"* ]]; then
                echo "  - $res"
            fi
        done
    fi
    
    echo ""
    echo "========================================"
    
    return $fails
}

main() {
    run_comprehensive_check
    exit $?
}

main "$@"
