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

# Reorder sys.path to prefer project source without shadowing celery package from site-packages
PROJECT_ROOT = Path(__file__).resolve().parent
PROJECT_SRC = PROJECT_ROOT
sys.path = [p for p in sys.path if p not in {str(PROJECT_ROOT), str(PROJECT_SRC)}]
if PROJECT_SRC.exists():
	sys.path.append(str(PROJECT_SRC))
if PROJECT_ROOT.exists():
	sys.path.append(str(PROJECT_ROOT))

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')

application = get_wsgi_application()
