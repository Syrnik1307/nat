"""
Production settings для России (lectiospace.ru)
"""
from .settings import *

# Домен
ALLOWED_HOSTS = ['lectiospace.ru', 'www.lectiospace.ru']

# Feature Flags - ТОЛЬКО российские фичи
FEATURE_AFRICA_MARKET = False
FEATURE_PWA_OFFLINE = False
FEATURE_MOBILE_MONEY = False
FEATURE_SMS_NOTIFICATIONS = False
FEATURE_MULTILINGUAL = False
FEATURE_ADAPTIVE_VIDEO = False

# Российские фичи включены
FEATURE_YOOKASSA_PAYMENTS = True
FEATURE_TELEGRAM_SUPPORT = True

# Валюта и язык
DEFAULT_CURRENCY = 'RUB'
DEFAULT_LANGUAGE = 'ru'

# Платежный провайдер
PAYMENT_PROVIDER = 'yookassa'

# Frontend URL
FRONTEND_URL = 'https://lectiospace.ru'

# Security
DEBUG = False
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_TRUSTED_ORIGINS = ['https://lectiospace.ru']

print("🇷🇺 Settings: Production Russia (lectiospace.ru)")
