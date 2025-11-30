"""
WSGI config for teaching_panel project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os
print("[WSGIDebug] teaching_panel.wsgi loaded")

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')

application = get_wsgi_application()
