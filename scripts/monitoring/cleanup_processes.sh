#!/bin/bash
# ============================================================
# CLEANUP ZOMBIE PROCESSES - запускается через cron каждый час
# ============================================================
# Убивает дублирующиеся процессы, старые npm, node и т.д.
# ============================================================

set -u

LOG_FILE="/var/log/lectio-monitor/cleanup.log"

# Загружаем конфигурацию (важно для cron: env переменные иначе не доступны)
CONFIG_FILE="/opt/lectio-monitor/config.env"
if [[ -f "$CONFIG_FILE" ]]; then
    # shellcheck disable=SC1090
    source "$CONFIG_FILE"
fi

# Telegram (бот ошибок) — используем те же переменные, что и health_check.sh
ERRORS_BOT_TOKEN="${ERRORS_BOT_TOKEN:-${TELEGRAM_BOT_TOKEN:-}}"
ERRORS_CHAT_ID="${ERRORS_CHAT_ID:-${TELEGRAM_CHAT_ID:-}}"

# Memory thresholds (MB)
MEMORY_WARN_MB=${MEMORY_WARN_MB:-400}
MEMORY_CRITICAL_MB=${MEMORY_CRITICAL_MB:-250}
SWAP_USED_WARN_MB=${SWAP_USED_WARN_MB:-512}
SWAP_USED_CRITICAL_MB=${SWAP_USED_CRITICAL_MB:-1024}
OOM_LOOKBACK_MINUTES=${OOM_LOOKBACK_MINUTES:-15}

# Anti-spam: не чаще одного memory-алерта за интервал
MEMORY_ALERT_STATE="/var/run/lectio-monitor/memory_alert_state"
MIN_ALERT_INTERVAL_SEC=1800

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

build_human_explanation() {
    local mem_available=$1
    local swap_used=$2
    local swap_total=$3
    local oom_events="$4"
    local killed=$5
    
    local lines=()
    
    # Определяем главную причину
    if [[ -n "$oom_events" ]]; then
        lines+=("ПРОБЛЕМА: Система убивала процессы из-за нехватки памяти (OOM Killer).")
        lines+=("ЧТО ЭТО ЗНАЧИТ: Памяти не хватило и Linux автоматически завершил процессы.")
        lines+=("ЧТО ДЕЛАТЬ: Увеличить RAM на сервере или найти утечку памяти.")
    elif [[ $swap_used -ge $SWAP_USED_WARN_MB ]]; then
        lines+=("ПРОБЛЕМА: Сервер активно использует swap (${swap_used}MB из ${swap_total}MB).")
        lines+=("ЧТО ЭТО ЗНАЧИТ: Оперативной памяти не хватает, данные сбрасываются на диск. Это замедляет работу сайта.")
        if [[ $swap_used -ge $SWAP_USED_CRITICAL_MB ]]; then
            lines+=("ЧТО ДЕЛАТЬ: Срочно перезагрузить сервер или увеличить RAM.")
        else
            lines+=("ЧТО ДЕЛАТЬ: Проверить какие процессы потребляют много памяти (см. список ниже). Перезапустить teaching_panel если нужно.")
        fi
    elif [[ $mem_available -lt $MEMORY_WARN_MB ]]; then
        lines+=("ПРОБЛЕМА: Мало свободной оперативной памяти (${mem_available}MB).")
        lines+=("ЧТО ЭТО ЗНАЧИТ: При дальнейшем росте нагрузки сервер начнёт тормозить.")
        lines+=("ЧТО ДЕЛАТЬ: Следить за ситуацией. При ухудшении — перезапустить сервисы.")
    fi
    
    if [[ $killed -gt 0 ]]; then
        lines+=("АВТОМАТИЧЕСКИ: Убито ${killed} зависших npm/node процессов (старше 10 мин).")
    fi
    
    printf '%s\n' "${lines[@]}"
}

send_telegram() {
    local message="$1"
    local priority="${2:-normal}"  # normal, high, critical

    if [[ -z "$ERRORS_BOT_TOKEN" ]] || [[ -z "$ERRORS_CHAT_ID" ]]; then
        log "Telegram Errors Bot не настроен, пропуск алерта"
        return 0
    fi

    local emoji=""
    local prefix=""
    case "$priority" in
        critical) 
            emoji="🚨🚨🚨"
            prefix="КРИТИЧНО"
            ;;
        high)     
            emoji="⚠️"
            prefix="ВНИМАНИЕ"
            ;;
        *)        
            emoji="ℹ️"
            prefix="ИНФО"
            ;;
    esac

    local full_message="$emoji $prefix: Нагрузка на память

$message

🕐 $(date '+%Y-%m-%d %H:%M:%S')
🖥️ Сервер: $(hostname)"

    curl -s -X POST "https://api.telegram.org/bot${ERRORS_BOT_TOKEN}/sendMessage" \
        -d "chat_id=${ERRORS_CHAT_ID}" \
        -d "text=${full_message}" \
        > /dev/null 2>&1 || log "Не удалось отправить Telegram алерт"
}

get_memory_metrics() {
    # Outputs: "available_mb swap_used_mb swap_total_mb"
    local available
    local swap_used
    local swap_total
    available=$(free -m | awk '/^Mem:/ {print $7}')
    swap_used=$(free -m | awk '/^Swap:/ {print $3}')
    swap_total=$(free -m | awk '/^Swap:/ {print $2}')
    echo "$available $swap_used $swap_total"
}

oom_events_recent() {
    if command -v journalctl >/dev/null 2>&1; then
        journalctl -k --since "${OOM_LOOKBACK_MINUTES} minutes ago" --no-pager 2>/dev/null | grep -iE 'out of memory: killed process|oom-kill|oom killer' | tail -3
    fi
}

should_send_memory_alert() {
    local now
    now=$(date +%s)

    if [[ -f "$MEMORY_ALERT_STATE" ]]; then
        local last
        last=$(cat "$MEMORY_ALERT_STATE" 2>/dev/null || echo 0)
        if [[ "$last" =~ ^[0-9]+$ ]]; then
            local elapsed=$((now - last))
            if [[ "$elapsed" -lt "$MIN_ALERT_INTERVAL_SEC" ]]; then
                return 1
            fi
        fi
    fi

    mkdir -p "$(dirname "$MEMORY_ALERT_STATE")" 2>/dev/null || true
    echo "$now" > "$MEMORY_ALERT_STATE" 2>/dev/null || true
    return 0
}

top_processes_snapshot() {
    # Ограничиваем размер сообщения (Telegram ~4096 символов)
    echo "Топ процессов по памяти:"
    echo "  PID   MEM    RSS КОМАНДА"
    ps aux --sort=-%mem | head -8 | tail -7 | awk '{printf "  %5s %4s%% %5sMB %s\n", $2, $4, int($6/1024), $11}'
    echo ""
    echo "Топ процессов по CPU:"
    echo "  PID   CPU    RSS КОМАНДА"
    ps aux --sort=-%cpu | head -5 | tail -4 | awk '{printf "  %5s %4s%% %5sMB %s\n", $2, $3, int($6/1024), $11}'
}

kill_build_hogs_if_needed() {
    # Используем только в критическом memory pressure.
    # Убиваем то, что не должно жить в проде постоянно: npm/node/serve.
    local killed=0

    # npm (install/ci/run) старше 10 минут
    while read -r pid; do
        [[ -z "$pid" ]] && continue
        local age
        age=$(ps -o etimes= -p "$pid" 2>/dev/null | tr -d ' ')
        if [[ -n "$age" && "$age" -gt 600 ]]; then
            sudo kill -9 "$pid" 2>/dev/null && killed=$((killed + 1))
        fi
    done < <(pgrep -f 'npm install|npm ci|npm run' 2>/dev/null || true)

    # node serve / react-scripts / webpack старше 10 минут
    while read -r pid; do
        [[ -z "$pid" ]] && continue
        local age
        age=$(ps -o etimes= -p "$pid" 2>/dev/null | tr -d ' ')
        if [[ -n "$age" && "$age" -gt 600 ]]; then
            sudo kill -9 "$pid" 2>/dev/null && killed=$((killed + 1))
        fi
    done < <(pgrep -f 'node .*serve -s|react-scripts|webpack' 2>/dev/null || true)

    echo "$killed"
}

log "Starting cleanup..."

# ==================== MEMORY PRESSURE ALERTS ====================
mem_metrics=$(get_memory_metrics)
mem_available_mb=$(echo "$mem_metrics" | awk '{print $1}')
swap_used_mb=$(echo "$mem_metrics" | awk '{print $2}')
swap_total_mb=$(echo "$mem_metrics" | awk '{print $3}')

oom_tail=$(oom_events_recent)

memory_is_critical=false
memory_is_warn=false

if [[ "$mem_available_mb" -lt "$MEMORY_CRITICAL_MB" ]] || [[ "$swap_used_mb" -ge "$SWAP_USED_CRITICAL_MB" ]]; then
    memory_is_critical=true
elif [[ "$mem_available_mb" -lt "$MEMORY_WARN_MB" ]] || [[ "$swap_used_mb" -ge "$SWAP_USED_WARN_MB" ]]; then
    memory_is_warn=true
fi

if [[ -n "$oom_tail" ]]; then
    memory_is_critical=true
fi

if [[ "$memory_is_critical" == true ]] || [[ "$memory_is_warn" == true ]]; then
    if should_send_memory_alert; then
        killed_count=0
        if [[ "$memory_is_critical" == true ]]; then
            killed_count=$(kill_build_hogs_if_needed)
        fi
        
        snapshot=$(top_processes_snapshot)
        human_explanation=$(build_human_explanation "$mem_available_mb" "$swap_used_mb" "$swap_total_mb" "$oom_tail" "$killed_count")
        
        msg="$human_explanation

📊 Состояние памяти:
• RAM свободно: ${mem_available_mb}MB (порог предупреждения: <${MEMORY_WARN_MB}MB)
• Swap занято: ${swap_used_mb}/${swap_total_mb}MB (порог предупреждения: >${SWAP_USED_WARN_MB}MB)"

        if [[ -n "$oom_tail" ]]; then
            msg+="

⚠️ OOM Killer события за последние ${OOM_LOOKBACK_MINUTES} мин:
${oom_tail}"
        fi
        
        msg+="

${snapshot}"

        if [[ "$memory_is_critical" == true ]]; then
            send_telegram "$msg" "critical"
        else
            send_telegram "$msg" "high"
        fi
    fi
fi

# 1. Kill old npm processes (older than 30 min)
npm_killed=$(pgrep -f 'npm install|npm ci|npm run' | while read pid; do
    age=$(ps -o etimes= -p "$pid" 2>/dev/null | tr -d ' ')
    if [[ -n "$age" && "$age" -gt 1800 ]]; then
        sudo kill -9 "$pid" 2>/dev/null && echo "$pid"
    fi
done | wc -l)
[[ "$npm_killed" -gt 0 ]] && log "Killed $npm_killed old npm processes"

# 2. Kill stale 'serve' processes
serve_killed=$(pgrep -f 'serve -s' | while read pid; do
    sudo kill -9 "$pid" 2>/dev/null && echo "$pid"
done | wc -l)
[[ "$serve_killed" -gt 0 ]] && log "Killed $serve_killed serve processes"

# 3. Kill zombie processes
zombies=$(ps aux | awk '$8 ~ /Z/ {print $2}')
for pid in $zombies; do
    parent=$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' ')
    [[ -n "$parent" ]] && sudo kill -9 "$parent" 2>/dev/null
done
[[ -n "$zombies" ]] && log "Cleaned up zombie processes"

# 4. Check for duplicate celery processes
celery_count=$(pgrep -cf 'celery.*worker' 2>/dev/null || echo 0)
if [[ "$celery_count" -gt 5 ]]; then
    log "Warning: $celery_count celery processes detected, restarting celery-combined"
    sudo systemctl restart celery-combined 2>/dev/null || true
fi

# 5. Clear old log files (> 7 days)
find /var/log/teaching_panel -name "*.log" -mtime +7 -exec truncate -s 0 {} \; 2>/dev/null
find /var/log/celery -name "*.log" -mtime +7 -exec truncate -s 0 {} \; 2>/dev/null

# 6. Clear systemd journal (keep 100MB)
sudo journalctl --vacuum-size=100M 2>/dev/null

log "Cleanup complete. Memory: $(free -m | awk '/Mem:/ {print $3"/"$2"MB"}')"
