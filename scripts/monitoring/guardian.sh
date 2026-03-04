#!/bin/bash
# ============================================================
# LECTIO GUARDIAN — Автоматический страж production
# ============================================================
# Единый скрипт, который:
#   1. Проверяет ВСЮ бизнес-логику (авторизация, API, статика)
#   2. АВТОМАТИЧЕСКИ восстанавливает при поломке
#   3. Эскалирует алерт ТОЛЬКО если не может починить сам
#   4. Помнит "последнюю рабочую версию" для git rollback
#
# Уровни восстановления:
#   L1: Перезапуск сервисов (gunicorn + celery)
#   L2: Fix permissions + restart nginx
#   L3: Git rollback к последнему рабочему коммиту
#   L4: Полный откат (git + БД бэкап)
#
# Cron: */2 * * * * /opt/lectio-monitor/guardian.sh
# ============================================================

export TZ=Europe/Moscow
set -uo pipefail

# --- Конфигурация ---
CONFIG_FILE="/opt/lectio-monitor/config.env"
[[ -f "$CONFIG_FILE" ]] && source "$CONFIG_FILE"

SITE_URL="${SITE_URL:-https://lectiospace.ru}"
INTERNAL_URL="${INTERNAL_BACKEND_URL:-http://127.0.0.1:8000}"
PUBLIC_HOST="${PUBLIC_HOST:-lectiospace.ru}"
PROJECT_ROOT="${PROJECT_ROOT:-/var/www/teaching_panel}"
FRONTEND_BUILD="${FRONTEND_BUILD:-$PROJECT_ROOT/frontend/build}"

SMOKE_TEACHER_EMAIL="${SMOKE_TEACHER_EMAIL:-smoke_teacher@test.local}"
SMOKE_TEACHER_PASSWORD="${SMOKE_TEACHER_PASSWORD:-SmokeTest123!}"
SMOKE_STUDENT_EMAIL="${SMOKE_STUDENT_EMAIL:-smoke_student@test.local}"
SMOKE_STUDENT_PASSWORD="${SMOKE_STUDENT_PASSWORD:-SmokeTest123!}"

BOT_TOKEN="${ERRORS_BOT_TOKEN:-${TELEGRAM_BOT_TOKEN:-}}"
CHAT_ID="${ERRORS_CHAT_ID:-${TELEGRAM_CHAT_ID:-}}"

STATE_DIR="/var/run/lectio-monitor"
LOG_FILE="/var/log/lectio-monitor/guardian.log"
LOCK_FILE="$STATE_DIR/guardian.lock"
KNOWN_GOOD_FILE="$STATE_DIR/last_known_good"
RECOVERY_STATE="$STATE_DIR/guardian_recovery"
ALERT_STATE="$STATE_DIR/guardian_alert"

# Лимиты
MAX_RECOVERY_PER_HOUR=3
ALERT_COOLDOWN=600  # 10 мин между алертами (но КРИТИЧЕСКИЕ всегда проходят)
DEPLOY_GRACE=300    # 5 мин после деплоя — не трогаем

mkdir -p "$STATE_DIR" "$(dirname "$LOG_FILE")"

# ==================== ЛОГИРОВАНИЕ ====================
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# ==================== LOCKING ====================
acquire_lock() {
    if [[ -f "$LOCK_FILE" ]]; then
        local pid
        pid=$(cat "$LOCK_FILE" 2>/dev/null)
        if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
            exit 0  # Другой экземпляр работает
        fi
        rm -f "$LOCK_FILE"
    fi
    echo $$ > "$LOCK_FILE"
}

release_lock() { rm -f "$LOCK_FILE"; }

# ==================== ДЕПЛОЙ-ПАУЗА ====================
is_deploy_active() {
    local marker="$STATE_DIR/deploy_in_progress"
    local maint="$STATE_DIR/maintenance_mode"
    for f in "$marker" "$maint"; do
        if [[ -f "$f" ]]; then
            local age=$(( $(date +%s) - $(stat -c %Y "$f" 2>/dev/null || echo 0) ))
            if (( age < DEPLOY_GRACE )); then
                return 0
            fi
            rm -f "$f"
        fi
    done
    return 1
}

# ==================== TELEGRAM ====================
send_telegram() {
    local msg="$1"
    local priority="${2:-normal}"

    [[ -z "$BOT_TOKEN" || -z "$CHAT_ID" ]] && return

    # Проверка mute
    local mute_file="$STATE_DIR/mute_until"
    if [[ -f "$mute_file" ]]; then
        local until now
        until=$(cat "$mute_file" 2>/dev/null || echo "0")
        now=$(date +%s)
        [[ "$until" =~ ^[0-9]+$ ]] && (( now < until )) && return
    fi

    # Антиспам для non-critical (critical ВСЕГДА проходят)
    if [[ "$priority" != "critical" && -f "$ALERT_STATE" ]]; then
        local last_alert=$(stat -c %Y "$ALERT_STATE" 2>/dev/null || echo 0)
        local elapsed=$(( $(date +%s) - last_alert ))
        (( elapsed < ALERT_COOLDOWN )) && return
    fi

    local emoji prefix
    case "$priority" in
        critical) emoji="🚨" prefix="САЙТ СЛОМАН" ;;
        recovery) emoji="✅" prefix="ВОССТАНОВЛЕНО" ;;
        warning)  emoji="⚠️"  prefix="ПРЕДУПРЕЖДЕНИЕ" ;;
        *)        emoji="ℹ️"  prefix="ИНФО" ;;
    esac

    local full="$emoji $prefix

$msg

$(date '+%Y-%m-%d %H:%M:%S MSK')"

    curl -s --max-time 10 \
        "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -d "chat_id=${CHAT_ID}" \
        -d "text=${full}" \
        -d "parse_mode=HTML" > /dev/null 2>&1 || true

    touch "$ALERT_STATE"
}

# ==================== HTTP HELPERS ====================
# Возвращает HTTP_CODE
http_check() {
    local url="$1"
    local token="${2:-}"
    local timeout="${3:-10}"
    local headers=""

    [[ -n "$token" ]] && headers="-H 'Authorization: Bearer $token'"

    # Добавляем Host/X-Forwarded-Proto для внутренних запросов
    if [[ "$url" == http://127.0.0.1* || "$url" == http://localhost* ]]; then
        headers="$headers -H 'Host: $PUBLIC_HOST' -H 'X-Forwarded-Proto: https'"
    fi

    eval curl -s -o /dev/null -w '%{http_code}' \
        --max-time "$timeout" --connect-timeout 5 \
        $headers "'$url'" 2>/dev/null || echo "000"
}

# Возвращает тело ответа
http_body() {
    local url="$1"
    local token="${2:-}"
    local timeout="${3:-10}"
    local headers=""

    [[ -n "$token" ]] && headers="-H 'Authorization: Bearer $token'"

    if [[ "$url" == http://127.0.0.1* || "$url" == http://localhost* ]]; then
        headers="$headers -H 'Host: $PUBLIC_HOST' -H 'X-Forwarded-Proto: https'"
    fi

    eval curl -s --max-time "$timeout" --connect-timeout 5 \
        $headers "'$url'" 2>/dev/null || echo ""
}

# JWT токен
get_jwt() {
    local email="$1" password="$2"
    local headers="-H 'Content-Type: application/json'"
    if [[ "$INTERNAL_URL" == http://127.0.0.1* || "$INTERNAL_URL" == http://localhost* ]]; then
        headers="$headers -H 'Host: $PUBLIC_HOST' -H 'X-Forwarded-Proto: https'"
    fi

    local body
    body=$(eval curl -s --max-time 15 -X POST \
        $headers \
        -d "'{\"email\":\"$email\",\"password\":\"$password\"}'" \
        "'${INTERNAL_URL}/api/jwt/token/'" 2>/dev/null) || body=""

    echo "$body" | grep -o '"access":"[^"]*"' | cut -d'"' -f4 2>/dev/null || echo ""
}

# ==================== HTTP С RETRY ====================
# Retry для внешних URL (DNS/TLS могут блипнуть)
http_check_with_retry() {
    local url="$1"
    local token="${2:-}"
    local timeout="${3:-10}"
    local retries="${4:-3}"
    local code
    for ((i=1; i<=retries; i++)); do
        code=$(http_check "$url" "$token" "$timeout")
        if [[ "$code" == "200" ]]; then
            echo "$code"
            return
        fi
        # Не спим после последней попытки
        (( i < retries )) && sleep 2
    done
    echo "$code"
}

# ==================== ПРОВЕРКИ ====================
# Каждая функция возвращает 0=OK, 1=FAIL и записывает описание в ISSUES[]

ISSUES=()
SEVERITY="ok"  # ok, degraded, critical

add_issue() {
    local sev="$1" msg="$2"
    ISSUES+=("$msg")
    if [[ "$sev" == "critical" ]]; then
        SEVERITY="critical"
    elif [[ "$sev" == "degraded" && "$SEVERITY" != "critical" ]]; then
        SEVERITY="degraded"
    fi
}

check_services() {
    for svc in teaching_panel nginx; do
        if ! systemctl is-active --quiet "$svc" 2>/dev/null; then
            add_issue critical "Сервис $svc не активен"
        fi
    done
    # Celery не критичен для пользователей, но важен
    for svc in celery celery-beat; do
        if ! systemctl is-active --quiet "$svc" 2>/dev/null; then
            add_issue degraded "Сервис $svc не активен"
        fi
    done
}

check_http() {
    local code

    # 1. Внутренний health-check (достоверный — без DNS/TLS)
    code=$(http_check "${INTERNAL_URL}/api/health/")
    if [[ "$code" != "200" ]]; then
        add_issue critical "/api/health/: HTTP $code (backend не отвечает)"
        return
    fi

    # 2. Внешний URL (может блипнуть из-за DNS/TLS) — retry 3 раза
    code=$(http_check_with_retry "${SITE_URL}/" "" "10" "3")
    if [[ "$code" != "200" ]]; then
        # Backend жив (проверено выше), внешний не прошёл — сетевой блип
        add_issue degraded "Внешний URL: HTTP $code (после 3 попыток, backend OK)"
    fi
}

check_frontend_build() {
    local idx="$FRONTEND_BUILD/index.html"
    if [[ ! -f "$idx" ]]; then
        add_issue critical "index.html не найден"
        return
    fi

    local expected_js
    expected_js=$(grep -oE 'main\.[a-f0-9]+\.js' "$idx" | head -1 || true)
    if [[ -z "$expected_js" ]]; then
        add_issue critical "main.*.js не найден в index.html"
        return
    fi

    if [[ ! -f "$FRONTEND_BUILD/static/js/$expected_js" ]]; then
        add_issue critical "JS файл $expected_js отсутствует на диске!"
        return
    fi

    # HTTP проверка (с retry — внешний URL может блипнуть)
    local code
    code=$(http_check_with_retry "${SITE_URL}/static/js/${expected_js}" "" "10" "2")
    if [[ "$code" != "200" ]]; then
        # Файл на диске есть (проверено выше), значит nginx/сеть блипнул
        add_issue degraded "JS файл недоступен через HTTP: $code (файл на диске есть)"
    fi
}

check_auth() {
    # Учитель
    local teacher_token
    teacher_token=$(get_jwt "$SMOKE_TEACHER_EMAIL" "$SMOKE_TEACHER_PASSWORD")
    if [[ -z "$teacher_token" ]]; then
        add_issue critical "JWT учителя: не удалось получить токен"
        return
    fi

    local code
    code=$(http_check "${INTERNAL_URL}/api/me/" "$teacher_token")
    if [[ "$code" != "200" ]]; then
        add_issue critical "/api/me/ (учитель): HTTP $code"
        return
    fi

    # Проверяем ключевые API с токеном учителя
    for endpoint in "/api/schedule/lessons/" "/api/homework/" "/api/subscription/" "/api/groups/"; do
        code=$(http_check "${INTERNAL_URL}${endpoint}" "$teacher_token")
        if [[ "$code" != "200" ]]; then
            add_issue degraded "$endpoint: HTTP $code"
        fi
    done

    # Студент (менее критично)
    local student_token
    student_token=$(get_jwt "$SMOKE_STUDENT_EMAIL" "$SMOKE_STUDENT_PASSWORD")
    if [[ -z "$student_token" ]]; then
        add_issue degraded "JWT студента: не удалось получить токен"
        return
    fi

    code=$(http_check "${INTERNAL_URL}/api/homework/" "$student_token")
    if [[ "$code" != "200" ]]; then
        add_issue degraded "/api/homework/ (студент): HTTP $code"
    fi
}

check_resources() {
    # Диск
    local disk_pct
    disk_pct=$(df / | awk 'NR==2 {gsub(/%/,""); print $5}')
    if (( disk_pct > 90 )); then
        add_issue degraded "Диск заполнен на ${disk_pct}%"
    fi

    # Память
    local mem_avail
    mem_avail=$(free -m | awk '/^Mem:/ {print $7}')
    if (( mem_avail < 200 )); then
        add_issue degraded "Мало памяти: ${mem_avail}MB свободно"
    fi
}

check_error_rate() {
    # Проверяем всплеск 500-ок за последние 5 минут в nginx access log
    local access_log="/var/log/nginx/access.log"
    [[ ! -f "$access_log" ]] && return

    local recent_500s
    recent_500s=$(awk -v cutoff="$(date -d '5 minutes ago' '+%d/%b/%Y:%H:%M:%S' 2>/dev/null)" \
        '$9 ~ /^5[0-9][0-9]$/ && $4 > "["cutoff {count++} END {print count+0}' "$access_log" 2>/dev/null || echo "0")

    if (( recent_500s > 20 )); then
        add_issue critical "Всплеск 500-ок: $recent_500s за 5 мин"
    elif (( recent_500s > 5 )); then
        add_issue degraded "500-ки: $recent_500s за 5 мин"
    fi

    # Проверяем gunicorn ошибки в journalctl
    local gunicorn_errors
    gunicorn_errors=$(journalctl -u teaching_panel --since "5 min ago" --no-pager 2>/dev/null | \
        grep -cE "Internal Server Error|Traceback|ModuleNotFoundError|ImportError" || true)
    gunicorn_errors=${gunicorn_errors:-0}

    if (( gunicorn_errors > 10 )); then
        add_issue critical "Gunicorn крашит: $gunicorn_errors ошибок за 5 мин"
    elif (( gunicorn_errors > 3 )); then
        add_issue degraded "Gunicorn ошибки: $gunicorn_errors за 5 мин"
    fi
}

# ==================== ВОССТАНОВЛЕНИЕ ====================

get_recovery_count() {
    if [[ ! -f "$RECOVERY_STATE" ]]; then
        echo "0"
        return
    fi
    local count ts
    read -r count ts < "$RECOVERY_STATE" 2>/dev/null || echo "0"
    local now=$(date +%s)
    # Сброс счётчика через час
    if [[ -n "$ts" ]] && (( now - ts > 3600 )); then
        echo "0"
        return
    fi
    echo "${count:-0}"
}

inc_recovery_count() {
    local count
    count=$(get_recovery_count)
    count=$((count + 1))
    echo "$count $(date +%s)" > "$RECOVERY_STATE"
    echo "$count"
}

# L1: Перезапуск сервисов
recovery_L1() {
    log "RECOVERY L1: Перезапуск сервисов"
    
    for svc in teaching_panel celery celery-beat; do
        systemctl restart "$svc" 2>/dev/null || true
    done
    sleep 5
    
    # Быстрая проверка
    local code
    code=$(http_check "${INTERNAL_URL}/api/health/")
    if [[ "$code" == "200" ]]; then
        log "RECOVERY L1: Успех! /api/health/ = 200"
        return 0
    fi
    log "RECOVERY L1: Не помог (health=$code)"
    return 1
}

# L2: Fix permissions + restart nginx
recovery_L2() {
    log "RECOVERY L2: Fix permissions + restart nginx"
    
    # Права frontend
    chown -R www-data:www-data "$FRONTEND_BUILD" 2>/dev/null || true
    chmod -R 755 "$FRONTEND_BUILD" 2>/dev/null || true
    
    # Права static/media
    for d in staticfiles media; do
        local p="$PROJECT_ROOT/$d"
        [[ -d "$p" ]] && chown -R www-data:www-data "$p" && chmod -R 755 "$p"
    done
    
    # Restart nginx
    systemctl restart nginx 2>/dev/null || true
    systemctl restart teaching_panel 2>/dev/null || true
    sleep 5
    
    local code
    code=$(http_check "${SITE_URL}/")
    if [[ "$code" == "200" ]]; then
        log "RECOVERY L2: Успех!"
        return 0
    fi
    log "RECOVERY L2: Не помог (http=$code)"
    return 1
}

# L3: Git rollback к последнему рабочему коммиту
recovery_L3() {
    log "RECOVERY L3: Git rollback"
    
    if [[ ! -f "$KNOWN_GOOD_FILE" ]]; then
        log "RECOVERY L3: Нет записи о последней рабочей версии"
        return 1
    fi
    
    local good_commit
    good_commit=$(head -1 "$KNOWN_GOOD_FILE" | awk '{print $1}')
    if [[ -z "$good_commit" ]]; then
        log "RECOVERY L3: Пустой known_good"
        return 1
    fi
    
    local current_commit
    current_commit=$(cd "$PROJECT_ROOT" && git rev-parse --short HEAD 2>/dev/null)
    
    if [[ "$current_commit" == "$good_commit" ]]; then
        log "RECOVERY L3: Уже на рабочем коммите ($good_commit)"
        return 1  # L3 не поможет, уже на нём
    fi
    
    log "RECOVERY L3: Откат $current_commit -> $good_commit"
    
    # Снимаем immutable флаги
    chattr -i "$FRONTEND_BUILD/index.html" "$FRONTEND_BUILD/favicon.svg" \
        "$PROJECT_ROOT/teaching_panel/teaching_panel/settings.py" 2>/dev/null || true
    
    # Git rollback
    cd "$PROJECT_ROOT"
    git fetch origin 2>/dev/null || true
    git reset --hard "$good_commit" 2>/dev/null
    
    # Pip install на случай если зависимости изменились
    source "$PROJECT_ROOT/venv/bin/activate"
    pip install -q -r "$PROJECT_ROOT/teaching_panel/requirements.txt" 2>/dev/null || true
    
    # Collectstatic
    cd "$PROJECT_ROOT/teaching_panel"
    python manage.py collectstatic --noinput --clear 2>/dev/null || true
    
    # Fix permissions
    chown -R www-data:www-data "$FRONTEND_BUILD" 2>/dev/null || true
    chmod -R 755 "$FRONTEND_BUILD" 2>/dev/null || true
    
    # Restart все
    for svc in teaching_panel celery celery-beat nginx; do
        systemctl restart "$svc" 2>/dev/null || true
    done
    
    # Восстанавливаем immutable
    chattr +i "$FRONTEND_BUILD/index.html" "$FRONTEND_BUILD/favicon.svg" \
        "$PROJECT_ROOT/teaching_panel/teaching_panel/settings.py" 2>/dev/null || true
    
    sleep 5
    
    local code
    code=$(http_check "${INTERNAL_URL}/api/health/")
    if [[ "$code" == "200" ]]; then
        log "RECOVERY L3: Успех! Откатились на $good_commit"
        return 0
    fi
    log "RECOVERY L3: Не помог даже после отката"
    return 1
}

# Главная функция восстановления
attempt_recovery() {
    local count
    count=$(get_recovery_count)
    
    if (( count >= MAX_RECOVERY_PER_HOUR )); then
        log "Лимит восстановлений: $count/$MAX_RECOVERY_PER_HOUR в час"
        return 1
    fi
    
    count=$(inc_recovery_count)
    log "Попытка восстановления #$count"
    
    # Пробуем уровни по возрастанию
    if recovery_L1; then
        send_telegram "Самовосстановление (L1: restart сервисов)

ОК после перезапуска.
Проверьте логи:
journalctl -u teaching_panel -n 30" "recovery"
        return 0
    fi
    
    if recovery_L2; then
        send_telegram "Самовосстановление (L2: permissions + nginx)

ОК после фикса прав.
Проверьте логи:
journalctl -u teaching_panel -n 30" "recovery"
        return 0
    fi
    
    if recovery_L3; then
        local good_commit
        good_commit=$(head -1 "$KNOWN_GOOD_FILE" | awk '{print $1}')
        send_telegram "Самовосстановление (L3: git rollback)

Откатил код на $good_commit
ВНИМАНИЕ: твои последние изменения отменены!
Посмотри что случилось и передеплой." "recovery"
        return 0
    fi
    
    return 1  # Ничего не помогло
}

# ==================== KNOWN GOOD STATE ====================

save_known_good() {
    local commit
    commit=$(cd "$PROJECT_ROOT" && git rev-parse --short HEAD 2>/dev/null)
    local ts
    ts=$(date '+%Y-%m-%d %H:%M:%S')
    echo "$commit $ts" > "$KNOWN_GOOD_FILE"
    log "Saved known good: $commit at $ts"
}

# ==================== MAIN ====================

main() {
    acquire_lock
    trap release_lock EXIT
    
    # Пропуск во время деплоя
    if is_deploy_active; then
        log "Деплой/maintenance активен, пропускаю"
        exit 0
    fi
    
    # Запуск всех проверок
    ISSUES=()
    SEVERITY="ok"
    
    check_services
    check_http
    check_frontend_build
    check_auth
    check_resources
    check_error_rate
    
    # Всё хорошо?
    if [[ "$SEVERITY" == "ok" ]]; then
        # Сохраняем как "последнюю рабочую версию"
        save_known_good
        # Сброс счётчика восстановлений
        rm -f "$RECOVERY_STATE"
        log "OK: все проверки пройдены"
        exit 0
    fi
    
    # Есть проблемы
    local issue_text
    issue_text=$(printf '- %s\n' "${ISSUES[@]}")
    # Логируем каждую проблему отдельной строкой для читаемости
    log "PROBLEMS ($SEVERITY):"
    local issue
    for issue in "${ISSUES[@]}"; do
        log "  - $issue"
    done
    
    if [[ "$SEVERITY" == "critical" ]]; then
        # Пробуем автовосстановление
        log "Запускаю автовосстановление..."
        
        if attempt_recovery; then
            # Восстановились! Перепроверяем
            ISSUES=()
            SEVERITY="ok"
            check_services
            check_http
            check_frontend_build
            check_auth
            
            if [[ "$SEVERITY" == "ok" ]]; then
                save_known_good
                rm -f "$RECOVERY_STATE"
                log "Полное восстановление подтверждено"
            else
                local remaining
                remaining=$(printf '- %s\n' "${ISSUES[@]}")
                send_telegram "Частичное восстановление

Исправлено, но ещё есть проблемы:
$remaining

Нужна проверка вручную." "warning"
            fi
        else
            # Не удалось восстановить
            send_telegram "НЕ МОГУ ПОЧИНИТЬ АВТОМАТИЧЕСКИ!

Проблемы:
$issue_text

Что пробовал:
L1: restart сервисов
L2: fix permissions
L3: git rollback

ЧТО ДЕЛАТЬ:
1. ssh tp
2. sudo journalctl -u teaching_panel -n 50
3. или: .\emergency_rollback.ps1 с Windows" "critical"
        fi
    else
        # degraded — не критично, просто алерт
        send_telegram "Некритичные проблемы:
$issue_text

Сайт работает, но есть деградация." "warning"
    fi
}

main "$@"
