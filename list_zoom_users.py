#!/usr/bin/env python
import os, sys
import django

sys.path.insert(0, '/var/www/teaching_panel/teaching_panel')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from schedule.zoom_client import my_zoom_api_client

try:
    data = my_zoom_api_client._get_request('users')
    print(data)
except Exception as e:
    print(f'Error: {e}')
