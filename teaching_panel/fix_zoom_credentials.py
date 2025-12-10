import sqlite3
from datetime import datetime

conn = sqlite3.connect('/var/www/teaching_panel/teaching_panel/db.sqlite3')
cursor = conn.cursor()

zoom_account_id = '6w5GrnCgSgaHwMFFbhmlKw'
zoom_client_id = 'vNl9EzZTy6h2UifsGVERg'
zoom_client_secret = 'jqMJb4R3UgOQ1Q2FEHtkv6Tkz3CxNX87'

# Обновляем реальный Zoom аккаунт с правильными креденшиалами
cursor.execute('''UPDATE zoom_pool_zoomaccount 
    SET api_key = ?, api_secret = ?, is_active = 1, current_meetings = 0
    WHERE zoom_user_id = ?''',
    (zoom_client_id, zoom_client_secret, zoom_account_id))

rows = cursor.rowcount
conn.commit()

if rows > 0:
    print(f'✓ Updated real Zoom account with correct credentials')
    cursor.execute('SELECT email, api_key, api_secret, zoom_user_id FROM zoom_pool_zoomaccount WHERE zoom_user_id = ?', (zoom_account_id,))
    result = cursor.fetchone()
    if result:
        email, api_key, api_secret, user_id = result
        print(f'  Email: {email}')
        print(f'  API Key (CLIENT_ID): {api_key[:20]}...')
        print(f'  API Secret (CLIENT_SECRET): {api_secret[:20]}...')
        print(f'  Zoom User ID: {user_id}')
else:
    print('✗ Account not found')

conn.close()
