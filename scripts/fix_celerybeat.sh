#!/bin/bash
#
# fix_celerybeat.sh - Исправление ошибки Permission denied для celerybeat-schedule
#
# Использование:
#   ./scripts/fix_celerybeat.sh          # Диагностика
#   ./scripts/fix_celerybeat.sh --fix    # Автоматическое исправление
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_DIR="${PROJECT_DIR:-/var/www/teaching_panel/teaching_panel}"
CELERYBEAT_FILE="$PROJECT_DIR/celerybeat-schedule"
FIX_MODE="${1:-}"

echo "=========================================="
echo "Celerybeat Schedule - Диагностика"
echo "=========================================="
echo ""

ISSUES_FOUND=0

# 1. Проверка файла celerybeat-schedule
echo -e "${YELLOW}[1/4] Проверка файла celerybeat-schedule...${NC}"

if [ -f "$CELERYBEAT_FILE" ]; then
    FILE_OWNER=$(stat -c '%U:%G' "$CELERYBEAT_FILE" 2>/dev/null || echo "unknown")
    FILE_PERMS=$(stat -c '%a' "$CELERYBEAT_FILE" 2>/dev/null || echo "000")
    FILE_SIZE=$(stat -c '%s' "$CELERYBEAT_FILE" 2>/dev/null || echo "0")
    
    echo "  Файл: $CELERYBEAT_FILE"
    echo "  Владелец: $FILE_OWNER"
    echo "  Права: $FILE_PERMS"
    echo "  Размер: $FILE_SIZE байт"
    
    if [ "$FILE_OWNER" != "www-data:www-data" ]; then
        echo -e "${RED}  ✗ Неправильный владелец! Должен быть www-data:www-data${NC}"
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
        
        if [ "$FIX_MODE" == "--fix" ]; then
            echo -e "${GREEN}  → Исправляю владельца...${NC}"
            sudo chown www-data:www-data "$CELERYBEAT_FILE"
        fi
    else
        echo -e "${GREEN}  ✓ Владелец правильный${NC}"
    fi
    
    # Проверка на повреждение (попытка открыть как shelve)
    if ! python3 -c "import shelve; s=shelve.open('${CELERYBEAT_FILE%%-schedule}', 'r'); s.close()" 2>/dev/null; then
        echo -e "${RED}  ✗ Файл повреждён!${NC}"
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
        
        if [ "$FIX_MODE" == "--fix" ]; then
            echo -e "${GREEN}  → Удаляю повреждённый файл...${NC}"
            sudo rm -f "$CELERYBEAT_FILE" "${CELERYBEAT_FILE}.db" "${CELERYBEAT_FILE}.dir" "${CELERYBEAT_FILE}.bak"
        fi
    else
        echo -e "${GREEN}  ✓ Файл не повреждён${NC}"
    fi
else
    echo -e "${YELLOW}  ⚠ Файл не существует (будет создан при запуске celery-beat)${NC}"
fi
echo ""

# 2. Проверка прав директории
echo -e "${YELLOW}[2/4] Проверка прав директории...${NC}"

DIR_OWNER=$(stat -c '%U:%G' "$PROJECT_DIR" 2>/dev/null || echo "unknown")
DIR_PERMS=$(stat -c '%a' "$PROJECT_DIR" 2>/dev/null || echo "000")

echo "  Директория: $PROJECT_DIR"
echo "  Владелец: $DIR_OWNER"
echo "  Права: $DIR_PERMS"

# www-data должен иметь право на запись
if [ ! -w "$PROJECT_DIR" ] && [ "$(whoami)" == "www-data" ]; then
    echo -e "${RED}  ✗ www-data не может писать в директорию!${NC}"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
else
    echo -e "${GREEN}  ✓ Права директории в порядке${NC}"
fi
echo ""

# 3. Проверка количества процессов celery-beat
echo -e "${YELLOW}[3/4] Проверка процессов celery-beat...${NC}"

BEAT_PROCS=$(pgrep -af "celery.*beat" 2>/dev/null | wc -l)

if [ "$BEAT_PROCS" -gt 1 ]; then
    echo -e "${RED}  ✗ Запущено несколько процессов celery-beat: $BEAT_PROCS${NC}"
    pgrep -af "celery.*beat"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
    
    if [ "$FIX_MODE" == "--fix" ]; then
        echo -e "${GREEN}  → Останавливаю все процессы и перезапускаю сервис...${NC}"
        sudo pkill -f "celery.*beat" || true
        sleep 2
        sudo systemctl start celery-beat
    fi
elif [ "$BEAT_PROCS" -eq 1 ]; then
    echo -e "${GREEN}  ✓ Запущен 1 процесс celery-beat${NC}"
else
    echo -e "${YELLOW}  ⚠ celery-beat не запущен${NC}"
    
    if [ "$FIX_MODE" == "--fix" ]; then
        echo -e "${GREEN}  → Запускаю celery-beat...${NC}"
        sudo systemctl start celery-beat
    fi
fi
echo ""

# 4. Проверка статуса сервиса
echo -e "${YELLOW}[4/4] Проверка статуса сервиса...${NC}"

if systemctl is-active --quiet celery-beat; then
    echo -e "${GREEN}  ✓ Сервис celery-beat активен${NC}"
else
    echo -e "${RED}  ✗ Сервис celery-beat не активен${NC}"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
    
    if [ "$FIX_MODE" == "--fix" ]; then
        echo -e "${GREEN}  → Перезапускаю сервис...${NC}"
        sudo systemctl restart celery-beat
    fi
fi
echo ""

# Итог
echo "=========================================="
if [ $ISSUES_FOUND -eq 0 ]; then
    echo -e "${GREEN}✓ Все проверки пройдены!${NC}"
else
    echo -e "${RED}Найдено проблем: $ISSUES_FOUND${NC}"
    if [ "$FIX_MODE" != "--fix" ]; then
        echo ""
        echo "Для автоматического исправления запустите:"
        echo "  $0 --fix"
    else
        echo ""
        echo "Проверьте статус:"
        echo "  sudo systemctl status celery-beat"
    fi
fi
echo "=========================================="

exit $ISSUES_FOUND
