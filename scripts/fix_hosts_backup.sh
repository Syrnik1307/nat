#!/bin/bash
# Исправляем ALLOWED_HOSTS и запускаем бэкап

ENV_FILE="/var/www/teaching_panel/teaching_panel/.env"

# 1. Добавляем lectio.tw1.ru в ALLOWED_HOSTS
if grep -q "lectio.tw1.ru" "$ENV_FILE"; then
    echo "lectio.tw1.ru уже в ALLOWED_HOSTS"
else
    sed -i 's/ALLOWED_HOSTS=.*/ALLOWED_HOSTS=lectio.space,www.lectio.space,lectio.tw1.ru,72.56.81.163,127.0.0.1,localhost/' "$ENV_FILE"
    echo "ALLOWED_HOSTS обновлён"
fi

# 2. Показать текущие ALLOWED_HOSTS
echo "Текущие ALLOWED_HOSTS:"
grep ALLOWED_HOSTS "$ENV_FILE"

# 3. Создать директорию для логов Django
mkdir -p /var/log/teaching_panel
chown www-data:www-data /var/log/teaching_panel

# 4. Запустить бэкап БД
echo ""
echo "=== Запуск бэкапа БД ==="
if [ -f "/var/www/teaching_panel/teaching_panel/backup_db.sh" ]; then
    bash /var/www/teaching_panel/teaching_panel/backup_db.sh
else
    echo "Скрипт бэкапа не найден, создаём бэкап вручную..."
    mkdir -p /var/backups/teaching_panel
    DB_PATH="/var/www/teaching_panel/teaching_panel/db.sqlite3"
    BACKUP_FILE="/var/backups/teaching_panel/db_backup_$(date +%Y%m%d_%H%M%S).sqlite3"
    if [ -f "$DB_PATH" ]; then
        sqlite3 "$DB_PATH" ".backup '$BACKUP_FILE'" && gzip "$BACKUP_FILE" && echo "Бэкап создан: ${BACKUP_FILE}.gz"
    fi
fi

# 5. Показать последние бэкапы
echo ""
echo "=== Последние бэкапы ==="
ls -la /var/backups/teaching_panel/*.gz 2>/dev/null | tail -5

# 6. Перезапуск сервиса
echo ""
echo "=== Перезапуск teaching_panel ==="
sudo systemctl restart teaching_panel
sleep 2
systemctl is-active teaching_panel
