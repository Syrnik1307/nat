"""
Development settings - локальная разработка
"""
from .settings import *

# Feature Flags - можешь включать что нужно
FEATURE_AFRICA_MARKET = True  # тестируем африканские фичи
FEATURE_PWA_OFFLINE = True
FEATURE_MOBILE_MONEY = False  # можно не тестировать платежи локально
FEATURE_SMS_NOTIFICATIONS = False
FEATURE_MULTILINGUAL = True
FEATURE_ADAPTIVE_VIDEO = True

FEATURE_YOOKASSA_PAYMENTS = True
FEATURE_TELEGRAM_SUPPORT = True

# Development настройки
DEBUG = True
ALLOWED_HOSTS = ['*']

# Frontend
FRONTEND_URL = 'http://localhost:3000'

# Email в консоль
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

print("🔧 Settings: Development (локальная разработка)")
