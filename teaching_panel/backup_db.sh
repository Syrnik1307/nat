#!/bin/bash
#
# Скрипт автоматического резервного копирования БД Teaching Panel
# Запускать через cron каждый день в 3:00 ночи
#

# Конфигурация
DB_PATH="/var/www/teaching_panel/teaching_panel/db.sqlite3"
BACKUP_DIR="/var/backups/teaching_panel"
RETENTION_DAYS=30
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/db_backup_$DATE.sqlite3"
LOGFILE="$BACKUP_DIR/backup.log"

# Создаем директорию если не существует
mkdir -p "$BACKUP_DIR"

# Функция логирования
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOGFILE"
}

log "=== Начало резервного копирования ==="

# Проверка существования БД
if [ ! -f "$DB_PATH" ]; then
    log "ОШИБКА: База данных не найдена: $DB_PATH"
    exit 1
fi

# Создаем резервную копию через sqlite3 (безопасный метод для работающей БД)
if command -v sqlite3 &> /dev/null; then
    log "Создание копии через sqlite3..."
    sqlite3 "$DB_PATH" ".backup '$BACKUP_FILE'"
    if [ $? -eq 0 ]; then
        log "✅ Резервная копия создана: $BACKUP_FILE"
        
        # Сжатие для экономии места
        gzip "$BACKUP_FILE"
        log "✅ Копия сжата: ${BACKUP_FILE}.gz"
        
        # Размер файла
        SIZE=$(du -h "${BACKUP_FILE}.gz" | cut -f1)
        log "Размер: $SIZE"
    else
        log "❌ ОШИБКА при создании копии!"
        exit 1
    fi
else
    # Fallback: простое копирование (работает только если БД не заблокирована)
    log "sqlite3 не найден, использую cp..."
    cp "$DB_PATH" "$BACKUP_FILE"
    gzip "$BACKUP_FILE"
    log "✅ Копия создана (через cp): ${BACKUP_FILE}.gz"
fi

# Удаляем старые бэкапы (старше RETENTION_DAYS дней)
log "Удаление бэкапов старше $RETENTION_DAYS дней..."
find "$BACKUP_DIR" -name "db_backup_*.sqlite3.gz" -type f -mtime +$RETENTION_DAYS -delete
DELETED=$?
if [ $DELETED -eq 0 ]; then
    log "✅ Старые бэкапы очищены"
fi

# Статистика
BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/db_backup_*.sqlite3.gz 2>/dev/null | wc -l)
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)
log "📊 Всего бэкапов: $BACKUP_COUNT, общий размер: $TOTAL_SIZE"

log "=== Резервное копирование завершено ==="
log ""

# Проверка целостности последнего бэкапа
LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/db_backup_*.sqlite3.gz 2>/dev/null | head -1)
if [ -n "$LATEST_BACKUP" ]; then
    gunzip -t "$LATEST_BACKUP" 2>/dev/null
    if [ $? -eq 0 ]; then
        log "✅ Последний бэкап проверен, целостность OK"
    else
        log "❌ ВНИМАНИЕ: Последний бэкап поврежден!"
    fi
fi

exit 0
