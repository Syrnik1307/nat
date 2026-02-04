"""
Staging settings для тестирования африканских фич
"""
from .settings import *

# Домен
ALLOWED_HOSTS = ['stage.lectiospace.ru', 'localhost', '127.0.0.1']

# Feature Flags - ВСЕ фичи включены для тестирования
FEATURE_AFRICA_MARKET = True
FEATURE_PWA_OFFLINE = True
FEATURE_MOBILE_MONEY = True
FEATURE_SMS_NOTIFICATIONS = True
FEATURE_MULTILINGUAL = True
FEATURE_ADAPTIVE_VIDEO = True

# Российские фичи тоже работают
FEATURE_YOOKASSA_PAYMENTS = True
FEATURE_TELEGRAM_SUPPORT = True

# Тестовые настройки
DEFAULT_CURRENCY = 'USD'
DEFAULT_LANGUAGE = 'en'
PAYMENT_PROVIDER = 'flutterwave'  # для Африки

# Frontend URL
FRONTEND_URL = 'https://stage.lectiospace.ru'

# Security (мягче для staging)
DEBUG = True
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
CSRF_TRUSTED_ORIGINS = ['https://stage.lectiospace.ru', 'http://localhost:3000']

# Email в консоль для тестирования
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

print("🧪 Settings: Staging (все фичи включены для тестирования)")
