import sqlite3
from datetime import datetime

conn = sqlite3.connect('/var/www/teaching_panel/teaching_panel/db.sqlite3')
cursor = conn.cursor()

cursor.execute("SELECT id, email, is_active, current_meetings FROM zoom_pool_zoomaccount WHERE email = 'test@zoom.local'")
existing = cursor.fetchone()

if existing:
    account_id, email, is_active, current_meetings = existing
    print(f'Account exists: {email} (id={account_id})')
    cursor.execute('UPDATE zoom_pool_zoomaccount SET current_meetings = 0, is_active = 1 WHERE id = ?', (account_id,))
    print(f'Reset meetings: {current_meetings} -> 0')
else:
    now = datetime.now().isoformat()
    cursor.execute('''INSERT INTO zoom_pool_zoomaccount 
        (email, api_key, api_secret, zoom_user_id, max_concurrent_meetings, current_meetings, is_active, created_at, updated_at, last_used_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)''',
        ('test@zoom.local', 'test_api_key', 'test_api_secret', 'test_zoom_user_id', 5, 0, 1, now, now))
    print('Created new Zoom account: test@zoom.local')

conn.commit()

cursor.execute('SELECT COUNT(*) FROM zoom_pool_zoomaccount')
total = cursor.fetchone()[0]
cursor.execute('SELECT COUNT(*) FROM zoom_pool_zoomaccount WHERE is_active = 1')
active = cursor.fetchone()[0]
cursor.execute('SELECT COUNT(*) FROM zoom_pool_zoomaccount WHERE is_active = 1 AND current_meetings = 0')
free = cursor.fetchone()[0]

print(f'\nZOOM POOL: Total={total}, Active={active}, Free={free}')
print('Ready for quick lessons!')

conn.close()
