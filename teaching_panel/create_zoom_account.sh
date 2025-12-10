#!/bin/bash
# Создаём тестовый Zoom аккаунт через прямой SQL

DB_PATH="/var/www/teaching_panel/db.sqlite3"

# Проверяем наличие базы
if [ ! -f "$DB_PATH" ]; then
    echo "❌ База данных не найдена: $DB_PATH"
    exit 1
fi

# Создаём тестовый аккаунт
python3 << 'PY'
import sqlite3
from datetime import datetime

conn = sqlite3.connect('/var/www/teaching_panel/db.sqlite3')
cursor = conn.cursor()

# Проверяем существование
cursor.execute("SELECT id, email, is_active, current_meetings FROM zoom_pool_zoomaccount WHERE email = 'test@zoom.local'")
existing = cursor.fetchone()

if existing:
    account_id, email, is_active, current_meetings = existing
    print(f"✓ Аккаунт существует: {email} (id={account_id})")
    
    # Сбрасываем занятость
    cursor.execute("""
        UPDATE zoom_pool_zoomaccount 
        SET current_meetings = 0, is_active = 1, updated_at = ?
        WHERE id = ?
    """, (datetime.now().isoformat(), account_id))
    print(f"✓ Сброшен счётчик встреч: {current_meetings} → 0")
else:
    # Создаём новый
    now = datetime.now().isoformat()
    cursor.execute("""
        INSERT INTO zoom_pool_zoomaccount 
        (email, api_key, api_secret, zoom_user_id, max_concurrent_meetings, current_meetings, is_active, created_at, updated_at, last_used_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
    """, (
        'test@zoom.local',
        'test_api_key',
        'test_api_secret', 
        'test_zoom_user_id',
        5,  # max_concurrent_meetings
        0,  # current_meetings
        1,  # is_active
        now,
        now
    ))
    print(f"✓ Создан новый Zoom аккаунт: test@zoom.local")

conn.commit()

# Статистика
cursor.execute("SELECT COUNT(*) FROM zoom_pool_zoomaccount")
total = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM zoom_pool_zoomaccount WHERE is_active = 1")
active = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM zoom_pool_zoomaccount WHERE is_active = 1 AND current_meetings = 0")
free = cursor.fetchone()[0]

print(f"\n=== ZOOM POOL STATUS ===")
print(f"Total: {total}")
print(f"Active: {active}")
print(f"Free: {free}")
print(f"\n✓ Готово! Теперь можно создавать быстрые уроки.")

conn.close()
PY
