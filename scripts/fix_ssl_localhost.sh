#!/bin/bash
#
# fix_ssl_localhost.sh - Исправление ошибки SSL Handshake Timeout на localhost
#
# Проблема: Тестовые скрипты пытаются делать HTTPS-запросы к 127.0.0.1:8000,
#           но Gunicorn слушает HTTP. SSL handshake зависает.
#
# Использование:
#   ./scripts/fix_ssl_localhost.sh          # Диагностика
#   ./scripts/fix_ssl_localhost.sh --fix    # Автоматическое исправление
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PROJECT_DIR="${PROJECT_DIR:-/var/www/teaching-panel}"
FIX_MODE="${1:-}"

echo "=========================================="
echo "SSL Localhost Timeout - Диагностика"
echo "=========================================="
echo ""

ISSUES_FOUND=0

# 1. Проверка временных Python-скриптов в /tmp
echo -e "${YELLOW}[1/4] Проверка /tmp/*.py...${NC}"
TMP_SCRIPTS=$(find /tmp -maxdepth 1 -name "*.py" -type f 2>/dev/null || true)

if [ -n "$TMP_SCRIPTS" ]; then
    echo -e "${RED}Найдены Python-скрипты в /tmp:${NC}"
    echo "$TMP_SCRIPTS"
    
    # Проверяем, есть ли в них https://127.0.0.1
    for script in $TMP_SCRIPTS; do
        if grep -q "https://127\.0\.0\.1\|https://localhost" "$script" 2>/dev/null; then
            echo -e "${RED}  ⚠ $script содержит HTTPS к localhost!${NC}"
            ISSUES_FOUND=$((ISSUES_FOUND + 1))
            
            if [ "$FIX_MODE" == "--fix" ]; then
                echo -e "${GREEN}  → Удаляю $script${NC}"
                rm -f "$script"
            fi
        fi
    done
else
    echo -e "${GREEN}✓ Нет Python-скриптов в /tmp${NC}"
fi
echo ""

# 2. Проверка кода проекта
echo -e "${YELLOW}[2/4] Поиск https://localhost в коде проекта...${NC}"
if [ -d "$PROJECT_DIR" ]; then
    HTTPS_LOCALHOST=$(grep -rn "https://127\.0\.0\.1:8000\|https://localhost:8000" \
        --include="*.py" "$PROJECT_DIR" 2>/dev/null | grep -v "\.pyc" || true)
    
    if [ -n "$HTTPS_LOCALHOST" ]; then
        echo -e "${RED}Найдены проблемные строки:${NC}"
        echo "$HTTPS_LOCALHOST"
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
        
        if [ "$FIX_MODE" == "--fix" ]; then
            echo -e "${YELLOW}  → Автозамена https:// на http:// для localhost...${NC}"
            find "$PROJECT_DIR" -name "*.py" -type f -exec \
                sed -i 's|https://127\.0\.0\.1:8000|http://127.0.0.1:8000|g' {} \;
            find "$PROJECT_DIR" -name "*.py" -type f -exec \
                sed -i 's|https://localhost:8000|http://localhost:8000|g' {} \;
            echo -e "${GREEN}  ✓ Исправлено${NC}"
        fi
    else
        echo -e "${GREEN}✓ Нет HTTPS к localhost в коде${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Директория $PROJECT_DIR не найдена${NC}"
fi
echo ""

# 3. Проверка Gunicorn
echo -e "${YELLOW}[3/4] Проверка Gunicorn...${NC}"
if pgrep -f "gunicorn.*teaching_panel" > /dev/null 2>&1; then
    GUNICORN_BIND=$(ps aux | grep "gunicorn.*teaching_panel" | grep -v grep | head -1)
    echo -e "${GREEN}✓ Gunicorn запущен${NC}"
    
    # Проверяем, слушает ли на правильном порту
    if ss -tlnp 2>/dev/null | grep -q ":8000"; then
        echo -e "${GREEN}✓ Порт 8000 открыт${NC}"
    else
        echo -e "${YELLOW}⚠ Порт 8000 не найден в listening sockets${NC}"
    fi
else
    echo -e "${RED}✗ Gunicorn не запущен!${NC}"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
    
    if [ "$FIX_MODE" == "--fix" ]; then
        echo -e "${GREEN}  → Перезапуск gunicorn...${NC}"
        sudo systemctl restart gunicorn 2>/dev/null || \
            sudo systemctl restart teaching-panel 2>/dev/null || \
            echo -e "${RED}  ✗ Не удалось перезапустить${NC}"
    fi
fi
echo ""

# 4. Проверка health endpoint
echo -e "${YELLOW}[4/4] Проверка health endpoint...${NC}"
HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
    --connect-timeout 5 \
    "http://127.0.0.1:8000/api/health/" 2>/dev/null || echo "000")

if [ "$HEALTH_RESPONSE" == "200" ]; then
    echo -e "${GREEN}✓ Health endpoint отвечает (HTTP 200)${NC}"
elif [ "$HEALTH_RESPONSE" == "000" ]; then
    echo -e "${RED}✗ Сервер не отвечает (connection refused/timeout)${NC}"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
else
    echo -e "${YELLOW}⚠ Health endpoint вернул HTTP $HEALTH_RESPONSE${NC}"
fi
echo ""

# Итог
echo "=========================================="
if [ $ISSUES_FOUND -eq 0 ]; then
    echo -e "${GREEN}✓ Все проверки пройдены!${NC}"
    echo "  Ошибка SSL Timeout скорее всего была от временного скрипта,"
    echo "  который уже удалён или больше не запускается."
else
    echo -e "${RED}Найдено проблем: $ISSUES_FOUND${NC}"
    if [ "$FIX_MODE" != "--fix" ]; then
        echo ""
        echo "Для автоматического исправления запустите:"
        echo "  $0 --fix"
    fi
fi
echo "=========================================="

exit $ISSUES_FOUND
