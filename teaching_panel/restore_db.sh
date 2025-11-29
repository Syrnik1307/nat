#!/bin/bash
#
# Скрипт восстановления БД из резервной копии
# ВНИМАНИЕ: Останавливает Django перед восстановлением!
#

BACKUP_DIR="/var/backups/teaching_panel"
DB_PATH="/var/www/teaching_panel/teaching_panel/db.sqlite3"
SERVICE_NAME="teaching_panel"

echo "=== Восстановление БД Teaching Panel ==="
echo ""

# Проверка прав
if [ "$EUID" -ne 0 ]; then
   echo "❌ Запустите скрипт с правами root: sudo $0"
   exit 1
fi

# Список доступных бэкапов
echo "Доступные резервные копии:"
echo ""
ls -lht "$BACKUP_DIR"/db_backup_*.sqlite3.gz | head -10 | nl
echo ""

read -p "Введите номер бэкапа для восстановления (или 'q' для выхода): " CHOICE

if [ "$CHOICE" = "q" ]; then
    echo "Отменено"
    exit 0
fi

# Получаем файл по номеру
BACKUP_FILE=$(ls -t "$BACKUP_DIR"/db_backup_*.sqlite3.gz | sed -n "${CHOICE}p")

if [ -z "$BACKUP_FILE" ]; then
    echo "❌ Некорректный выбор!"
    exit 1
fi

echo ""
echo "Выбран бэкап: $BACKUP_FILE"
echo "Размер: $(du -h "$BACKUP_FILE" | cut -f1)"
echo "Дата: $(stat -c %y "$BACKUP_FILE" | cut -d'.' -f1)"
echo ""
read -p "❗ ВНИМАНИЕ: Текущая БД будет ПЕРЕЗАПИСАНА! Продолжить? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Отменено"
    exit 0
fi

# Создаем бэкап текущей БД перед восстановлением
EMERGENCY_BACKUP="/var/backups/teaching_panel/emergency_backup_$(date +%Y%m%d_%H%M%S).sqlite3"
echo "Создание аварийного бэкапа текущей БД..."
cp "$DB_PATH" "$EMERGENCY_BACKUP"
gzip "$EMERGENCY_BACKUP"
echo "✅ Аварийный бэкап: ${EMERGENCY_BACKUP}.gz"

# Останавливаем Django
echo "Остановка сервиса $SERVICE_NAME..."
systemctl stop "$SERVICE_NAME"
sleep 2

# Распаковываем и восстанавливаем
TEMP_FILE="/tmp/restore_db_$$.sqlite3"
echo "Распаковка бэкапа..."
gunzip -c "$BACKUP_FILE" > "$TEMP_FILE"

if [ $? -eq 0 ]; then
    echo "Проверка целостности..."
    sqlite3 "$TEMP_FILE" "PRAGMA integrity_check;" > /dev/null
    
    if [ $? -eq 0 ]; then
        echo "Восстановление БД..."
        mv "$TEMP_FILE" "$DB_PATH"
        chown www-data:www-data "$DB_PATH"
        chmod 664 "$DB_PATH"
        echo "✅ БД восстановлена!"
    else
        echo "❌ ОШИБКА: Бэкап поврежден!"
        rm -f "$TEMP_FILE"
        systemctl start "$SERVICE_NAME"
        exit 1
    fi
else
    echo "❌ ОШИБКА при распаковке!"
    systemctl start "$SERVICE_NAME"
    exit 1
fi

# Запускаем Django обратно
echo "Запуск сервиса $SERVICE_NAME..."
systemctl start "$SERVICE_NAME"
sleep 2

# Проверка статуса
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "✅ Сервис запущен успешно!"
else
    echo "❌ ОШИБКА запуска сервиса! Проверьте: journalctl -u $SERVICE_NAME -n 50"
    exit 1
fi

echo ""
echo "=== Восстановление завершено ==="
echo "Аварийный бэкап: ${EMERGENCY_BACKUP}.gz"
echo ""

exit 0
