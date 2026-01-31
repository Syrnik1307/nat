#!/bin/bash
# ============================================================
# DEPLOY NEW UNIFIED MONITORING
# ============================================================
# Устанавливает новую систему мониторинга и отключает старый спам
# ============================================================

set -e

echo "=== Deploying Unified Monitoring ==="

# 1. Копируем новый скрипт
sudo cp /tmp/unified_monitor.sh /opt/lectio-monitor/unified_monitor.sh
sudo chmod +x /opt/lectio-monitor/unified_monitor.sh
sudo chown root:root /opt/lectio-monitor/unified_monitor.sh

echo "[OK] Unified monitor installed"

# 2. Обновляем crontab - убираем старый спам, добавляем unified
# Сохраняем текущий crontab
crontab -l > /tmp/old_crontab.txt 2>/dev/null || true

# Удаляем старые задачи мониторинга
grep -v 'health_check.sh\|smoke_check_v2.sh\|deep_check.sh\|cleanup_processes.sh' /tmp/old_crontab.txt > /tmp/new_crontab.txt 2>/dev/null || true

# Добавляем новую единую задачу (раз в 5 минут)
echo "*/5 * * * * /opt/lectio-monitor/unified_monitor.sh >> /var/log/lectio-monitor/unified.log 2>&1" >> /tmp/new_crontab.txt

# Оставляем cleanup (раз в день в 3:00) и deploy_safe cleanup
echo "0 3 * * * /opt/lectio-monitor/deploy_safe.sh cleanup 7 >> /var/log/lectio-monitor/cleanup.log 2>&1" >> /tmp/new_crontab.txt

# Применяем новый crontab
crontab /tmp/new_crontab.txt

echo "[OK] Crontab updated"
echo ""
echo "New cron schedule:"
crontab -l | grep -v '^#' | grep -v '^$'

# 3. Очищаем старые state файлы чтобы не было проблем
sudo rm -f /var/run/lectio-monitor/memory_alert_state 2>/dev/null || true
sudo rm -f /var/run/lectio-monitor/smoke_v2_state 2>/dev/null || true
sudo rm -f /var/run/lectio-monitor/alert_* 2>/dev/null || true

echo ""
echo "[OK] Old state files cleaned"

# 4. Тестовый запуск
echo ""
echo "=== Test Run ==="
/opt/lectio-monitor/unified_monitor.sh

echo ""
echo "=== DONE ==="
echo ""
echo "Summary:"
echo "  - Old monitoring (health_check, smoke_check, deep_check) DISABLED"
echo "  - New unified_monitor.sh runs every 5 minutes"
echo "  - Alerts only for CRITICAL issues"
echo "  - Anti-spam: max 1 alert per issue every 2 hours"
echo ""
echo "To mute alerts for 1 hour:"
echo "  echo \$((\$(date +%s) + 3600)) > /var/run/lectio-monitor/mute_until"
