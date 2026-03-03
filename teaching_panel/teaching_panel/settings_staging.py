"""
Staging settings -- mirror of prod with relaxed security.
Staging tests the same code that will go to production.
"""
from .settings import *  # noqa: F401,F403
import os

# Domain
ALLOWED_HOSTS = ['stage.lectiospace.ru', 'localhost', '127.0.0.1']

# Feature Flags -- same as prod
FEATURE_YOOKASSA_PAYMENTS = True
FEATURE_TELEGRAM_SUPPORT = True

# Knowledge Map -- required because analytics/homework have FK to it
if 'knowledge_map' not in INSTALLED_APPS:
    INSTALLED_APPS.append('knowledge_map')

# Frontend URL
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://stage.lectiospace.ru')

# Security (relaxed for staging)
DEBUG = True
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
CSRF_TRUSTED_ORIGINS = ['https://stage.lectiospace.ru', 'http://localhost:3000']

# Redis/Celery -- separate DB from prod (prod: /0, /1; staging: /2, /3)
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://127.0.0.1:6379/2')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://127.0.0.1:6379/2')

if os.environ.get('REDIS_URL'):
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/3'),
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            },
        }
    }

# Email to console for testing
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# reCAPTCHA disabled on staging
RECAPTCHA_ENABLED = False

print("[Staging] Settings loaded: stage.lectiospace.ru")
