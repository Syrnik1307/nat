#!/bin/bash
# ============================================================
# LECTIO MONITORING SYSTEM INSTALLER
# ============================================================
# Этот скрипт устанавливает полную систему мониторинга
# и автовосстановления на production сервере
#
# Запуск: sudo bash install_monitoring.sh
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="/opt/lectio-monitor"

echo "=============================================="
echo " LECTIO MONITORING SYSTEM INSTALLER"
echo "=============================================="

# ==================== ПРОВЕРКИ ====================

if [[ $EUID -ne 0 ]]; then
    echo "Ошибка: Требуются права root"
    echo "Запустите: sudo bash $0"
    exit 1
fi

# ==================== СОЗДАНИЕ ДИРЕКТОРИЙ ====================

echo "[1/8] Создание директорий..."

mkdir -p "$INSTALL_DIR"
mkdir -p /var/log/lectio-monitor
mkdir -p /var/run/lectio-monitor
mkdir -p /var/www/teaching_panel/backups

chown -R www-data:www-data /var/log/lectio-monitor
chown -R www-data:www-data /var/run/lectio-monitor
chown -R www-data:www-data /var/www/teaching_panel/backups

# ==================== КОПИРОВАНИЕ СКРИПТОВ ====================

echo "[2/8] Копирование скриптов..."

cp "$SCRIPT_DIR/health_check.sh" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/deploy_safe.sh" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/notify_failure.sh" "$INSTALL_DIR/"

chmod +x "$INSTALL_DIR"/*.sh

# Конфигурация
if [[ ! -f "$INSTALL_DIR/config.env" ]]; then
    cp "$SCRIPT_DIR/config.env.example" "$INSTALL_DIR/config.env"
    echo "⚠️  ВАЖНО: Отредактируйте $INSTALL_DIR/config.env"
    echo "   Добавьте TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID"
fi

# ==================== SYSTEMD SERVICES ====================

echo "[3/8] Установка systemd сервисов..."

# Teaching panel service (обновлённый с watchdog)
cp "$SCRIPT_DIR/systemd/teaching_panel.service" /etc/systemd/system/
cp "$SCRIPT_DIR/systemd/failure-notifier@.service" /etc/systemd/system/

# Добавляем OnFailure в teaching_panel
if ! grep -q "OnFailure" /etc/systemd/system/teaching_panel.service; then
    sed -i '/\[Unit\]/a OnFailure=failure-notifier@%n.service' /etc/systemd/system/teaching_panel.service
fi

systemctl daemon-reload

# ==================== CRON JOBS ====================

echo "[4/8] Настройка cron jobs..."

# Health check каждую минуту
CRON_HEALTH="* * * * * /opt/lectio-monitor/health_check.sh >> /var/log/lectio-monitor/cron.log 2>&1"

# Cleanup бэкапов раз в день
CRON_CLEANUP="0 3 * * * /opt/lectio-monitor/deploy_safe.sh cleanup 7 >> /var/log/lectio-monitor/cleanup.log 2>&1"

# Добавляем в crontab если ещё нет
(crontab -l 2>/dev/null | grep -v "lectio-monitor" || true; echo "$CRON_HEALTH"; echo "$CRON_CLEANUP") | crontab -

echo "Cron jobs установлены"

# ==================== LOGROTATE ====================

echo "[5/8] Настройка logrotate..."

cat > /etc/logrotate.d/lectio-monitor << 'EOF'
/var/log/lectio-monitor/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
}
EOF

# ==================== HEALTH ENDPOINT ====================

echo "[6/8] Проверка health endpoint..."

# Проверяем что есть Django health endpoint
HEALTH_VIEW="/var/www/teaching_panel/teaching_panel/teaching_panel/health.py"
if [[ ! -f "$HEALTH_VIEW" ]]; then
    echo "Создаём health endpoint для Django..."
    
    cat > "$HEALTH_VIEW" << 'PYEOF'
"""
Health Check Endpoint for Monitoring
"""
from django.http import JsonResponse
from django.db import connection
import time

def health_check(request):
    """
    Простой health check endpoint для мониторинга.
    Возвращает 200 если всё ок, 500 если есть проблемы.
    """
    status = {
        'status': 'healthy',
        'timestamp': time.time(),
        'checks': {}
    }
    
    # Проверка базы данных
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        status['checks']['database'] = 'ok'
    except Exception as e:
        status['status'] = 'unhealthy'
        status['checks']['database'] = str(e)
    
    http_status = 200 if status['status'] == 'healthy' else 500
    return JsonResponse(status, status=http_status)
PYEOF
    
    # Добавляем URL (если ещё нет)
    URLS_FILE="/var/www/teaching_panel/teaching_panel/teaching_panel/urls.py"
    if ! grep -q "health_check" "$URLS_FILE"; then
        echo "Добавляем health URL..."
        # Добавить импорт и путь вручную
        echo "⚠️  ВАЖНО: Добавьте в urls.py:"
        echo "   from .health import health_check"
        echo "   path('api/health/', health_check, name='health_check'),"
    fi
fi

# ==================== ПРАВА ДОСТУПА ====================

echo "[7/8] Настройка прав доступа..."

# Разрешаем www-data выполнять systemctl restart без пароля
SUDOERS_FILE="/etc/sudoers.d/lectio-monitor"
cat > "$SUDOERS_FILE" << 'EOF'
# Позволяет www-data перезапускать сервисы для автовосстановления
www-data ALL=(ALL) NOPASSWD: /bin/systemctl restart teaching_panel
www-data ALL=(ALL) NOPASSWD: /bin/systemctl restart nginx
www-data ALL=(ALL) NOPASSWD: /bin/systemctl status teaching_panel
www-data ALL=(ALL) NOPASSWD: /bin/systemctl status nginx
www-data ALL=(ALL) NOPASSWD: /bin/chown -R www-data\:www-data /var/www/teaching_panel/frontend/build
www-data ALL=(ALL) NOPASSWD: /bin/chmod -R 755 /var/www/teaching_panel/frontend/build
EOF

chmod 440 "$SUDOERS_FILE"

# ==================== ФИНАЛЬНЫЕ ПРОВЕРКИ ====================

echo "[8/8] Финальные проверки..."

# Проверяем что всё на месте
echo ""
echo "Проверка установки:"
echo "  ✓ Scripts: $(ls $INSTALL_DIR/*.sh | wc -l) файлов"
echo "  ✓ Config: $INSTALL_DIR/config.env"
echo "  ✓ Logs: /var/log/lectio-monitor/"
echo "  ✓ Cron: $(crontab -l | grep -c lectio-monitor) jobs"

# Тестовый запуск health check
echo ""
echo "Запуск тестовой проверки..."
if "$INSTALL_DIR/health_check.sh"; then
    echo "  ✓ Health check работает"
else
    echo "  ⚠ Health check обнаружил проблемы (см. логи)"
fi

echo ""
echo "=============================================="
echo " УСТАНОВКА ЗАВЕРШЕНА!"
echo "=============================================="
echo ""
echo "ВАЖНО: Выполните следующие шаги:"
echo ""
echo "1. Отредактируйте конфигурацию Telegram:"
echo "   nano $INSTALL_DIR/config.env"
echo ""
echo "2. Добавьте health endpoint в Django urls.py:"
echo "   path('api/health/', health_check, name='health_check'),"
echo ""
echo "3. Перезапустите сервисы:"
echo "   systemctl restart teaching_panel"
echo ""
echo "4. Проверьте работу мониторинга:"
echo "   tail -f /var/log/lectio-monitor/health.log"
echo ""
echo "=============================================="
