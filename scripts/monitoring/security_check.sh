#!/bin/bash
# ============================================================
# LECTIO SECURITY MONITOR - Обнаружение атак и подозрительной активности
# ============================================================
# Анализирует логи на предмет:
# - Brute force атаки (много 401/403)
# - SQL injection попытки
# - Path traversal
# - Подозрительные User-Agents (сканеры)
# - Аномальный трафик с одного IP
#
# Запуск: каждые 15 минут
# Расположение: /opt/lectio-monitor/security_check.sh
# ============================================================

set -uo pipefail

CONFIG_FILE="/opt/lectio-monitor/config.env"
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
fi

NGINX_ACCESS_LOG="/var/log/nginx/access.log"
NGINX_ERROR_LOG="/var/log/nginx/error.log"
DJANGO_LOG="/var/log/teaching_panel/error.log"
LOG_FILE="/var/log/lectio-monitor/security.log"
STATE_FILE="/var/run/lectio-monitor/security_state"
BLOCKED_IPS_FILE="/var/run/lectio-monitor/blocked_ips"

ERRORS_BOT_TOKEN="${ERRORS_BOT_TOKEN:-${TELEGRAM_BOT_TOKEN:-}}"
ERRORS_CHAT_ID="${ERRORS_CHAT_ID:-${TELEGRAM_CHAT_ID:-}}"

# Пороги
BRUTE_FORCE_THRESHOLD=50    # 401/403 за 15 минут с одного IP
REQUESTS_THRESHOLD=500      # Запросов за 15 минут с одного IP
SCAN_PATTERNS_THRESHOLD=10  # Подозрительных запросов за 15 минут

# Антиспам
ALERT_COOLDOWN=1800  # 30 минут

mkdir -p "$(dirname "$LOG_FILE")" "$(dirname "$STATE_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$1] $2" | tee -a "$LOG_FILE"
}

send_telegram() {
    local message="$1"
    local priority="${2:-high}"

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
    local alert_hash=$(echo "$message" | md5sum | cut -d' ' -f1)
    local state_key="${STATE_FILE}_${alert_hash}"
    
    if [[ -f "$state_key" ]]; then
        local last_alert=$(cat "$state_key" 2>/dev/null || echo 0)
        local now=$(date +%s)
        if [[ $((now - last_alert)) -lt $ALERT_COOLDOWN ]]; then
            return 0
        fi
    fi
    echo $(date +%s) > "$state_key"
    
    local emoji="🔒"
    [[ "$priority" == "critical" ]] && emoji="🚨🔐"
    
    curl -s -X POST "https://api.telegram.org/bot${ERRORS_BOT_TOKEN}/sendMessage" \
        -d "chat_id=${ERRORS_CHAT_ID}" \
        -d "text=${emoji} SECURITY ALERT

$message

🕐 $(date '+%Y-%m-%d %H:%M:%S')" \
        > /dev/null 2>&1 || true
}

# ==================== ДЕТЕКТОРЫ ====================

# 1. Brute force detection (много 401/403 с одного IP)
detect_brute_force() {
    if [[ ! -f "$NGINX_ACCESS_LOG" ]]; then
        return 0
    fi
    
    local time_window=$(date -d '15 minutes ago' '+%d/%b/%Y:%H:%M' 2>/dev/null || date '+%d/%b/%Y:%H')
    
    # Находим IP с большим количеством 401/403
    local suspicious_ips
    suspicious_ips=$(awk -v threshold="$BRUTE_FORCE_THRESHOLD" '
        $9 == "401" || $9 == "403" {
            ip=$1
            count[ip]++
        }
        END {
            for (ip in count) {
                if (count[ip] >= threshold) {
                    print ip, count[ip]
                }
            }
        }
    ' "$NGINX_ACCESS_LOG" 2>/dev/null | head -5)
    
    if [[ -n "$suspicious_ips" ]]; then
        echo "BRUTE_FORCE:$suspicious_ips"
        return 1
    fi
    
    return 0
}

# 2. SQL Injection attempts
detect_sql_injection() {
    if [[ ! -f "$NGINX_ACCESS_LOG" ]]; then
        return 0
    fi
    
    # Паттерны SQL injection
    local sqli_patterns="UNION.*SELECT|SELECT.*FROM|DROP.*TABLE|INSERT.*INTO|DELETE.*FROM|OR.*1.*=.*1|AND.*1.*=.*1|'.*OR.*'|\".*OR.*\"|SLEEP\(|BENCHMARK\(|LOAD_FILE\(|INTO.*OUTFILE"
    
    local sqli_attempts
    sqli_attempts=$(grep -iE "$sqli_patterns" "$NGINX_ACCESS_LOG" 2>/dev/null | tail -10 | wc -l)
    
    if [[ "$sqli_attempts" -gt 0 ]]; then
        local sample=$(grep -iE "$sqli_patterns" "$NGINX_ACCESS_LOG" 2>/dev/null | tail -3 | awk '{print $1, $7}')
        echo "SQL_INJECTION:$sqli_attempts attempts. Sample: $sample"
        return 1
    fi
    
    return 0
}

# 3. Path traversal attempts
detect_path_traversal() {
    if [[ ! -f "$NGINX_ACCESS_LOG" ]]; then
        return 0
    fi
    
    local traversal_patterns="\.\./|\.\.%2f|\.\.%5c|/etc/passwd|/etc/shadow|/proc/self|/var/log"
    
    local traversal_attempts
    traversal_attempts=$(grep -iE "$traversal_patterns" "$NGINX_ACCESS_LOG" 2>/dev/null | tail -20 | wc -l)
    
    if [[ "$traversal_attempts" -gt "$SCAN_PATTERNS_THRESHOLD" ]]; then
        echo "PATH_TRAVERSAL:$traversal_attempts attempts detected"
        return 1
    fi
    
    return 0
}

# 4. Suspicious scanners (по User-Agent)
detect_scanners() {
    if [[ ! -f "$NGINX_ACCESS_LOG" ]]; then
        return 0
    fi
    
    # Известные сканеры уязвимостей
    local scanner_patterns="nikto|nmap|sqlmap|dirbuster|gobuster|wpscan|nuclei|acunetix|nessus|qualys|masscan|zmap|zgrab"
    
    local scanner_hits
    scanner_hits=$(grep -iE "$scanner_patterns" "$NGINX_ACCESS_LOG" 2>/dev/null | wc -l)
    
    if [[ "$scanner_hits" -gt 0 ]]; then
        local scanner_ips=$(grep -iE "$scanner_patterns" "$NGINX_ACCESS_LOG" 2>/dev/null | awk '{print $1}' | sort -u | head -5)
        echo "SCANNER:Detected scanner activity from: $scanner_ips"
        return 1
    fi
    
    return 0
}

# 5. Аномальный трафик (слишком много запросов с одного IP)
detect_anomaly() {
    if [[ ! -f "$NGINX_ACCESS_LOG" ]]; then
        return 0
    fi
    
    # Топ IP по количеству запросов за последние 15 минут
    local top_ips
    top_ips=$(awk -v threshold="$REQUESTS_THRESHOLD" '
        {
            ip=$1
            count[ip]++
        }
        END {
            for (ip in count) {
                if (count[ip] >= threshold) {
                    print ip, count[ip]
                }
            }
        }
    ' "$NGINX_ACCESS_LOG" 2>/dev/null | sort -k2 -nr | head -3)
    
    if [[ -n "$top_ips" ]]; then
        echo "ANOMALY:High traffic IPs: $top_ips"
        return 1
    fi
    
    return 0
}

# 6. Проверка 500 ошибок (признак эксплуатации уязвимости)
detect_exploitation() {
    if [[ ! -f "$NGINX_ACCESS_LOG" ]]; then
        return 0
    fi
    
    # Много 500 ошибок за короткое время
    local error_count
    error_count=$(awk '$9 == "500" {count++} END {print count+0}' "$NGINX_ACCESS_LOG" 2>/dev/null)
    
    if [[ "$error_count" -gt 20 ]]; then
        echo "EXPLOITATION:$error_count internal errors - possible exploitation attempt"
        return 1
    fi
    
    return 0
}

# ==================== MAIN ====================

main() {
    local alerts=()
    
    log "INFO" "=== Security Check START ==="
    
    # Brute force
    local res
    res=$(detect_brute_force) && true
    if [[ -n "$res" ]]; then
        log "ALERT" "$res"
        alerts+=("$res")
    fi
    
    # SQL Injection
    res=$(detect_sql_injection) && true
    if [[ -n "$res" ]]; then
        log "ALERT" "$res"
        alerts+=("$res")
    fi
    
    # Path traversal
    res=$(detect_path_traversal) && true
    if [[ -n "$res" ]]; then
        log "ALERT" "$res"
        alerts+=("$res")
    fi
    
    # Scanners
    res=$(detect_scanners) && true
    if [[ -n "$res" ]]; then
        log "ALERT" "$res"
        alerts+=("$res")
    fi
    
    # Anomaly
    res=$(detect_anomaly) && true
    if [[ -n "$res" ]]; then
        log "WARN" "$res"
        # Не добавляем в алерты, только лог
    fi
    
    # Exploitation
    res=$(detect_exploitation) && true
    if [[ -n "$res" ]]; then
        log "ALERT" "$res"
        alerts+=("$res")
    fi
    
    # ==================== REPORT ====================
    
    if [[ ${#alerts[@]} -gt 0 ]]; then
        local alert_text=$(printf '• %s\n' "${alerts[@]}")
        send_telegram "Обнаружена подозрительная активность:

$alert_text

Рекомендуется проверить логи вручную." "critical"
    else
        log "INFO" "No security issues detected"
    fi
}

main "$@"
