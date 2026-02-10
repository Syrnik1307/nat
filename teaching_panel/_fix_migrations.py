import sqlite3
from datetime import datetime

conn = sqlite3.connect('db.sqlite3')
now = datetime.now().isoformat()
conn.execute(
    'INSERT INTO django_migrations (app, name, applied) VALUES (?, ?, ?)',
    ('schedule', '0031_lessonrecording_deleted_at_and_more', now)
)
conn.execute(
    'INSERT INTO django_migrations (app, name, applied) VALUES (?, ?, ?)',
    ('schedule', '0032_merge_20260201_0829', now)
)
conn.commit()
print('OK: inserted 2 fake migration records')
conn.close()
