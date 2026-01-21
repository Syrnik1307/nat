#!/bin/sh
set -e

# DB migrate + static collect are safe no-ops when already applied
python manage.py migrate --noinput
python manage.py collectstatic --noinput || true

exec gunicorn teaching_panel.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 2 \
  --threads 4 \
  --timeout 120
