"""
WSGI config for teaching_panel project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os
import sys
from pathlib import Path

print("[WSGIDebug] teaching_panel.wsgi loaded")

# Ensure project source (teaching_panel/*) is first on sys.path to avoid stale root copies
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_SRC = BASE_DIR
if PROJECT_SRC.exists():
	sys.path.insert(0, str(PROJECT_SRC))

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')

application = get_wsgi_application()
