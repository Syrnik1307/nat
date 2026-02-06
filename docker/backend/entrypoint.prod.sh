#!/bin/sh
set -e

echo "=== Teaching Panel Backend Starting ==="
echo "Waiting for database..."

# Ждём готовности PostgreSQL (если используется)
if echo "$DATABASE_URL" | grep -q "postgresql"; then
    until python -c "
import os
import psycopg2
from urllib.parse import urlparse
url = urlparse(os.environ['DATABASE_URL'])
conn = psycopg2.connect(
    host=url.hostname,
    port=url.port or 5432,
    user=url.username,
    password=url.password,
    dbname=url.path[1:]
)
conn.close()
print('Database ready!')
" 2>/dev/null; do
        echo "Postgres not ready, waiting 2s..."
        sleep 2
    done
fi

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput || true

# Количество воркеров = 2 * CPU + 1 (но минимум 2, максимум 8)
WORKERS=${GUNICORN_WORKERS:-4}

echo "Starting Gunicorn with $WORKERS workers (gevent)..."
exec gunicorn teaching_panel.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "$WORKERS" \
  --worker-class gevent \
  --worker-connections 1000 \
  --timeout 60 \
  --graceful-timeout 30 \
  --keep-alive 5 \
  --max-requests 1500 \
  --max-requests-jitter 150 \
  --access-logfile - \
  --error-logfile - \
  --capture-output \
  --enable-stdio-inheritance
