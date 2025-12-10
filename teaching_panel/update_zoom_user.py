import sqlite3

DB_PATH = '/var/www/teaching_panel/teaching_panel/db.sqlite3'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("UPDATE zoom_pool_zoomaccount SET zoom_user_id='me', current_meetings=0, is_active=1 WHERE email='zoom@teaching-panel.local'")
print('Updated rows:', cursor.rowcount)

cursor.execute('SELECT id, email, zoom_user_id, current_meetings, is_active FROM zoom_pool_zoomaccount WHERE email=?', ('zoom@teaching-panel.local',))
print('Row:', cursor.fetchone())

conn.commit()
conn.close()
