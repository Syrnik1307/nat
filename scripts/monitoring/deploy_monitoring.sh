#!/bin/bash
# =============================================================================
# deploy_monitoring.sh - Деплой всей системы мониторинга на production
# =============================================================================
# Запуск: ./deploy_monitoring.sh
# 
# Что делает:
# 1. Копирует все скрипты мониторинга на сервер
# 2. Устанавливает права и cron задачи
# 3. Создаёт smoke-пользователей
# 4. Тестирует все проверки
# =============================================================================

set -e

SERVER="root@lectiospace.ru"
REMOTE_DIR="/opt/lectio-monitor"
LOCAL_DIR="$(dirname "$0")"

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================"
echo "  Деплой системы мониторинга Lectio"
echo "========================================"

# 1. Копируем все скрипты
echo -e "\n${YELLOW}[1/6] Копирование скриптов...${NC}"

SCRIPTS=(
    "smoke_check_v2.sh"
    "deep_check.sh"
    "heartbeat.sh"
    "integration_check.sh"
    "latency_check.sh"
    "security_check.sh"
    "setup_smoke_users.sh"
    "notify_failure.sh"
    "deploy_safe.sh"
  "ops_alerts_bot.py"
  "lectio-ops-bot.service.example"
)

for script in "${SCRIPTS[@]}"; do
    if [[ -f "$LOCAL_DIR/$script" ]]; then
        echo "  → $script"
        scp -q "$LOCAL_DIR/$script" "$SERVER:$REMOTE_DIR/"
    else
        echo "  ⚠ $script не найден, пропускаем"
    fi
done

# 2. Устанавливаем права
echo -e "\n${YELLOW}[2/6] Установка прав...${NC}"

ssh $SERVER "chmod +x $REMOTE_DIR/*.sh"
echo "  ✓ Права установлены"

# 3. Создаём smoke-пользователей (если не существуют)
echo -e "\n${YELLOW}[3/6] Создание smoke-пользователей...${NC}"

ssh $SERVER "cd /var/www/teaching_panel && $REMOTE_DIR/setup_smoke_users.sh"

# 4. Настраиваем cron
echo -e "\n${YELLOW}[4/6] Настройка cron...${NC}"

CRON_CONTENT="
# ============================================
# Lectio Monitoring - Auto-generated
# ============================================

# Базовая проверка здоровья (каждую минуту)
* * * * * $REMOTE_DIR/health_check.sh >> /var/log/lectio-monitor/health.log 2>&1

# Smoke-тесты бизнес-логики (каждые 5 минут)
*/5 * * * * $REMOTE_DIR/smoke_check_v2.sh >> /var/log/lectio-monitor/smoke.log 2>&1

# Глубокая проверка инфраструктуры (каждый час в :30)
30 * * * * $REMOTE_DIR/deep_check.sh >> /var/log/lectio-monitor/deep.log 2>&1

# Проверка интеграций (каждые 6 часов)
0 */6 * * * $REMOTE_DIR/integration_check.sh >> /var/log/lectio-monitor/integration.log 2>&1

# Проверка безопасности (каждые 15 минут)
*/15 * * * * $REMOTE_DIR/security_check.sh >> /var/log/lectio-monitor/security.log 2>&1

# Heartbeat для внешнего мониторинга (каждые 5 минут)
*/5 * * * * $REMOTE_DIR/heartbeat.sh >> /var/log/lectio-monitor/heartbeat.log 2>&1

# Ротация логов (ежедневно в 4:00)
0 4 * * * find /var/log/lectio-monitor -name '*.log' -mtime +7 -delete

# Бэкапы (3:00)
0 3 * * * /var/www/teaching_panel/scripts/backup_db.sh >> /var/log/lectio-monitor/backup.log 2>&1

# Очистка старых процессов (каждый час)
0 * * * * /var/www/teaching_panel/scripts/cleanup_processes.sh >> /var/log/lectio-monitor/cleanup.log 2>&1
"

echo "$CRON_CONTENT" | ssh $SERVER "crontab -"
echo "  ✓ Cron настроен"

# Показываем текущий cron
echo -e "\n  Текущие задачи:"
ssh $SERVER "crontab -l | grep -v '^#' | grep -v '^$' | head -10"

# 5. Создаём директории для логов
echo -e "\n${YELLOW}[5/6] Создание директорий...${NC}"

ssh $SERVER "mkdir -p /var/log/lectio-monitor /var/run/lectio-monitor"
echo "  ✓ Директории созданы"

# 6. Запускаем все проверки для теста
echo -e "\n${YELLOW}[6/6] Тестирование проверок...${NC}"

echo -e "\n  → smoke_check_v2.sh:"
ssh $SERVER "timeout 60 $REMOTE_DIR/smoke_check_v2.sh 2>&1 | tail -5" || echo "  (timeout или ошибка)"

echo -e "\n  → deep_check.sh:"
ssh $SERVER "timeout 30 $REMOTE_DIR/deep_check.sh 2>&1 | tail -3" || echo "  (timeout или ошибка)"

echo -e "\n  → integration_check.sh:"
ssh $SERVER "timeout 30 $REMOTE_DIR/integration_check.sh 2>&1 | tail -3" || echo "  (timeout или ошибка)"

echo -e "\n  → security_check.sh:"
ssh $SERVER "timeout 30 $REMOTE_DIR/security_check.sh 2>&1 | tail -3" || echo "  (timeout или ошибка)"

# Готово
echo -e "\n${GREEN}========================================"
echo "  ✅ Деплой мониторинга завершён!"
echo "========================================${NC}"

echo "
Что установлено:
  • smoke_check_v2.sh  - 11 бизнес-проверок (каждые 5 мин)
  • deep_check.sh      - SSL, диск, память (каждый час)
  • integration_check.sh - GDrive, Zoom, платежи (каждые 6 часов)
  • security_check.sh  - детекция атак (каждые 15 мин)
  • heartbeat.sh       - внешний uptime (каждые 5 мин)

Логи:
  /var/log/lectio-monitor/*.log

Следующие шаги:
  1. Настройте healthchecks.io и добавьте URL в heartbeat.sh
  2. Добавьте SENTRY_DSN в .env для Django
  3. Создайте Telegram группу (см. TELEGRAM_GROUP_SETUP.md)
  4. Проверьте алерты: ssh $SERVER 'tail -f /var/log/lectio-monitor/*.log'
"
