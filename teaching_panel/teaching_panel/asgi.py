"""
ASGI config for teaching_panel project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os
import sys
from pathlib import Path

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')

# Ensure project source (teaching_panel/*) is first on sys.path to avoid stale root copies
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_SRC = BASE_DIR
if PROJECT_SRC.exists():
	sys.path.insert(0, str(PROJECT_SRC))

application = get_asgi_application()
