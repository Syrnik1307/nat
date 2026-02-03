#!/bin/bash
cd /var/www/teaching_panel/teaching_panel
source /var/www/teaching_panel/venv/bin/activate
export DJANGO_SETTINGS_MODULE=teaching_panel.settings
python << 'EOF'
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
import django
django.setup()
from django.conf import settings
print("SECURE_PROXY_SSL_HEADER:", getattr(settings, 'SECURE_PROXY_SSL_HEADER', 'NOT SET'))
print("SESSION_COOKIE_SECURE:", getattr(settings, 'SESSION_COOKIE_SECURE', 'NOT SET'))
print("CSRF_COOKIE_SECURE:", getattr(settings, 'CSRF_COOKIE_SECURE', 'NOT SET'))
print("SECURE_SSL_REDIRECT:", getattr(settings, 'SECURE_SSL_REDIRECT', 'NOT SET'))
EOF
