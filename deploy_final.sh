#!/bin/bash

# Teaching Panel Production Deployment Script
# Deploy without password using SSH keys
# Usage: bash deploy_prod.sh

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
SERVER="tp"  # SSH alias (must be configured in ~/.ssh/config)
PROJECT_PATH="/var/www/teaching_panel"
VENV_PATH="${PROJECT_PATH}/venv"
DJANGO_PATH="${PROJECT_PATH}/teaching_panel"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Teaching Panel Production Deployment${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Check if SSH alias exists
echo -e "${YELLOW}📡 Проверка подключения к серверу...${NC}"
if ! ssh -O check "$SERVER" >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Кэш SSH не активен, подключаюсь...${NC}"
fi

# Start the deployment
echo -e "${YELLOW}🚀 Начинаем деплой...${NC}\n"

# Execute deployment commands via SSH
ssh "$SERVER" << 'EOFCOMMANDS'

# Colors for remote output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

PROJECT_PATH="/var/www/teaching_panel"
VENV_PATH="${PROJECT_PATH}/venv"
DJANGO_PATH="${PROJECT_PATH}/teaching_panel"

# Step 1: Pull latest code
echo -e "${YELLOW}📥 Шаг 1: Обновление кода из Git...${NC}"
cd "$PROJECT_PATH" || exit 1
sudo -u www-data git pull origin main
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Ошибка при git pull${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Код обновлен${NC}\n"

# Step 2: Install dependencies
echo -e "${YELLOW}📦 Шаг 2: Установка зависимостей...${NC}"
cd "$DJANGO_PATH" || exit 1
source "$VENV_PATH/bin/activate"
pip install -r requirements.txt --quiet
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Ошибка при pip install${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Зависимости установлены${NC}\n"

# Step 3: Run migrations
echo -e "${YELLOW}🔄 Шаг 3: Запуск миграций БД...${NC}"
python manage.py migrate --noinput
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Ошибка при миграции${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Миграции выполнены${NC}\n"

# Step 4: Collect static files
echo -e "${YELLOW}📄 Шаг 4: Сбор статических файлов...${NC}"
python manage.py collectstatic --noinput --clear
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Ошибка при collectstatic${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Статические файлы собраны${NC}\n"

# Step 5: Restart services
echo -e "${YELLOW}🔄 Шаг 5: Перезапуск сервисов...${NC}"
sudo systemctl restart teaching_panel
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Ошибка при перезапуске teaching_panel${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Teaching Panel перезапущен${NC}"

sudo systemctl restart nginx
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Ошибка при перезапуске nginx${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Nginx перезапущен${NC}\n"

# Step 6: Verify status
echo -e "${YELLOW}✔️ Шаг 6: Проверка статуса...${NC}"
echo ""
sudo systemctl status teaching_panel --no-pager
echo ""
sudo systemctl status nginx --no-pager
echo ""

# Step 7: Check logs for errors
echo -e "${YELLOW}📋 Последние логи (проверка ошибок):${NC}"
sudo journalctl -u teaching_panel -n 10 --no-pager

EOFCOMMANDS

# Check deployment result
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}✅ ДЕПЛОЙ УСПЕШНО ЗАВЕРШЕН!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${BLUE}Проверка доступности:${NC}"
    echo "  - API: https://teaching-panel.ru/api/"
    echo "  - Frontend: https://teaching-panel.ru/"
    echo ""
    echo -e "${BLUE}Полезные команды:${NC}"
    echo "  - Логи: ssh tp 'sudo journalctl -u teaching_panel -f'"
    echo "  - Статус: ssh tp 'sudo systemctl status teaching_panel'"
    echo "  - Перезапуск: ssh tp 'sudo systemctl restart teaching_panel'"
else
    echo -e "\n${RED}========================================${NC}"
    echo -e "${RED}❌ ДЕПЛОЙ ЗАВЕРШИЛСЯ С ОШИБКОЙ${NC}"
    echo -e "${RED}========================================${NC}"
    exit 1
fi
