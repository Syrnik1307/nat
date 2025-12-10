import sqlite3
from datetime import datetime

conn = sqlite3.connect('/var/www/teaching_panel/teaching_panel/db.sqlite3')
cursor = conn.cursor()

# Проверяем реальный Zoom аккаунт
zoom_account_id = '6w5GrnCgSgaHwMFFbhmlKw'
zoom_client_id = 'vNl9EzZTy6h2UifsGVERg'
zoom_client_secret = 'jqMJb4R3UgOQ1Q2FEHtkv6Tkz3CxNX87'

cursor.execute("SELECT id, email, is_active FROM zoom_pool_zoomaccount WHERE zoom_user_id = ?", (zoom_account_id,))
existing = cursor.fetchone()

if existing:
    account_id, email, is_active = existing
    print(f'Real account exists: {email} (id={account_id}, active={is_active})')
    # Убедимся что он активен и свободен
    cursor.execute('UPDATE zoom_pool_zoomaccount SET current_meetings = 0, is_active = 1 WHERE id = ?', (account_id,))
    print(f'Reset to active and free')
else:
    # Создаём реальный аккаунт
    now = datetime.now().isoformat()
    cursor.execute('''INSERT INTO zoom_pool_zoomaccount 
        (email, api_key, api_secret, zoom_user_id, max_concurrent_meetings, current_meetings, is_active, created_at, updated_at, last_used_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)''',
        ('zoom@teaching-panel.local', zoom_client_id, zoom_client_secret, zoom_account_id, 5, 0, 1, now, now))
    print(f'Created REAL Zoom account: {zoom_account_id}')

conn.commit()

# Статистика
cursor.execute('SELECT COUNT(*) FROM zoom_pool_zoomaccount')
total = cursor.fetchone()[0]
cursor.execute('SELECT COUNT(*) FROM zoom_pool_zoomaccount WHERE is_active = 1')
active = cursor.fetchone()[0]
cursor.execute('SELECT COUNT(*) FROM zoom_pool_zoomaccount WHERE is_active = 1 AND current_meetings = 0')
free = cursor.fetchone()[0]

print(f'\n=== ZOOM POOL STATUS ===')
print(f'Total: {total}')
print(f'Active: {active}')
print(f'Free: {free}')
print(f'\n✓ Real Zoom API enabled!')

conn.close()
