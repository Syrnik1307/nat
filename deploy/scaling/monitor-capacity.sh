#!/bin/bash
# =============================================================================
# Capacity Monitoring Script for Lectio Space
# Run periodically (cron) or manually to check system health
# =============================================================================

echo "======================================"
echo "  Lectio Space Capacity Monitor"
echo "  $(date)"
echo "======================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Thresholds
CPU_WARN=70
CPU_CRIT=90
MEM_WARN=80
MEM_CRIT=95
DISK_WARN=80
DISK_CRIT=90
CONN_WARN=40
CONN_CRIT=80

# ============ CPU ============
echo "📊 CPU Usage:"
CPU=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1 | cut -d'.' -f1)
if [ "$CPU" -gt "$CPU_CRIT" ]; then
    echo -e "  ${RED}⚠️  CPU: ${CPU}% (CRITICAL)${NC}"
elif [ "$CPU" -gt "$CPU_WARN" ]; then
    echo -e "  ${YELLOW}⚠️  CPU: ${CPU}% (WARNING)${NC}"
else
    echo -e "  ${GREEN}✓ CPU: ${CPU}%${NC}"
fi

# ============ MEMORY ============
echo ""
echo "📊 Memory Usage:"
MEM=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100}')
MEM_USED=$(free -h | grep Mem | awk '{print $3}')
MEM_TOTAL=$(free -h | grep Mem | awk '{print $2}')
if [ "$MEM" -gt "$MEM_CRIT" ]; then
    echo -e "  ${RED}⚠️  Memory: ${MEM}% (${MEM_USED}/${MEM_TOTAL}) - CRITICAL${NC}"
elif [ "$MEM" -gt "$MEM_WARN" ]; then
    echo -e "  ${YELLOW}⚠️  Memory: ${MEM}% (${MEM_USED}/${MEM_TOTAL}) - WARNING${NC}"
else
    echo -e "  ${GREEN}✓ Memory: ${MEM}% (${MEM_USED}/${MEM_TOTAL})${NC}"
fi

# ============ DISK ============
echo ""
echo "📊 Disk Usage:"
DISK=$(df / | tail -1 | awk '{print $5}' | tr -d '%')
if [ "$DISK" -gt "$DISK_CRIT" ]; then
    echo -e "  ${RED}⚠️  Disk: ${DISK}% - CRITICAL${NC}"
elif [ "$DISK" -gt "$DISK_WARN" ]; then
    echo -e "  ${YELLOW}⚠️  Disk: ${DISK}% - WARNING${NC}"
else
    echo -e "  ${GREEN}✓ Disk: ${DISK}%${NC}"
fi

# ============ PostgreSQL Connections ============
echo ""
echo "📊 PostgreSQL Connections:"
if command -v psql &> /dev/null; then
    PG_CONN=$(sudo -u postgres psql -t -c "SELECT count(*) FROM pg_stat_activity WHERE state != 'idle';" 2>/dev/null | tr -d ' ')
    PG_MAX=$(sudo -u postgres psql -t -c "SHOW max_connections;" 2>/dev/null | tr -d ' ')
    if [ -n "$PG_CONN" ] && [ -n "$PG_MAX" ]; then
        PG_PCT=$((PG_CONN * 100 / PG_MAX))
        if [ "$PG_PCT" -gt "$CONN_CRIT" ]; then
            echo -e "  ${RED}⚠️  Active: ${PG_CONN}/${PG_MAX} (${PG_PCT}%) - CRITICAL${NC}"
        elif [ "$PG_PCT" -gt "$CONN_WARN" ]; then
            echo -e "  ${YELLOW}⚠️  Active: ${PG_CONN}/${PG_MAX} (${PG_PCT}%) - WARNING${NC}"
        else
            echo -e "  ${GREEN}✓ Active: ${PG_CONN}/${PG_MAX} (${PG_PCT}%)${NC}"
        fi
    else
        echo "  (Could not query PostgreSQL)"
    fi
else
    echo "  (psql not available)"
fi

# ============ Services Status ============
echo ""
echo "📊 Service Status:"
for service in teaching_panel celery celery-beat celery-default celery-heavy redis nginx pgbouncer; do
    STATUS=$(systemctl is-active $service 2>/dev/null)
    if [ "$STATUS" = "active" ]; then
        echo -e "  ${GREEN}✓ ${service}: running${NC}"
    elif [ "$STATUS" = "inactive" ] || [ "$STATUS" = "unknown" ]; then
        # Skip non-existent services silently
        :
    else
        echo -e "  ${RED}✗ ${service}: ${STATUS}${NC}"
    fi
done

# ============ Gunicorn Workers ============
echo ""
echo "📊 Gunicorn Workers:"
GUNICORN_PIDS=$(pgrep -f "gunicorn.*teaching_panel" 2>/dev/null | wc -l)
echo "  Workers: $GUNICORN_PIDS"

# ============ Celery Workers ============
echo ""
echo "📊 Celery Workers:"
CELERY_PIDS=$(pgrep -f "celery.*worker" 2>/dev/null | wc -l)
echo "  Worker processes: $CELERY_PIDS"

# ============ Health Check ============
echo ""
echo "📊 API Health Check:"
HEALTH=$(curl -s -m 5 http://127.0.0.1:8000/api/health/ 2>/dev/null)
if [ $? -eq 0 ] && [ -n "$HEALTH" ]; then
    echo -e "  ${GREEN}✓ API responding${NC}"
else
    echo -e "  ${RED}✗ API not responding${NC}"
fi

# ============ Recommendations ============
echo ""
echo "======================================"
echo "  Capacity Recommendations"
echo "======================================"

# Calculate stage
if [ "$CPU" -gt 60 ] || [ "$MEM" -gt 70 ]; then
    echo -e "${YELLOW}⚠️  System load high. Consider scaling to next stage.${NC}"
    echo "   Current specs may be insufficient."
    echo "   See: deploy/scaling/README.md"
fi

if [ -n "$PG_PCT" ] && [ "$PG_PCT" -gt 50 ]; then
    echo -e "${YELLOW}⚠️  PostgreSQL connections at ${PG_PCT}%.${NC}"
    echo "   Consider installing PgBouncer for connection pooling."
fi

echo ""
echo "Done."
