"""
Конфигурация Telegram бота
"""
import os
from django.conf import settings

# Токен бота
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')

# URL фронтенда
WEBAPP_URL = (
    os.environ.get('WEBAPP_URL') or 
    getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
).rstrip('/')

# Redis для хранения состояний диалогов
REDIS_URL = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/2')

# TTL для состояний диалогов (15 минут — достаточно для сложных wizard'ов)
DIALOG_STATE_TTL = 60 * 15

# TTL для кэша данных (1 час)
CACHE_TTL = 60 * 60

# Автоочистка Redis каждые 3 дня (в секундах)
REDIS_CLEANUP_INTERVAL = 60 * 60 * 24 * 3

# Лимиты рассылок (для защиты от спама)
# Учитывая 10 000 учителей:
BROADCAST_LIMITS = {
    'per_hour': 10,      # макс. 10 рассылок в час на учителя
    'per_day': 50,       # макс. 50 рассылок в день на учителя
    'recipients_per_broadcast': 500,  # макс. 500 получателей за раз
    'cooldown_seconds': 60,  # минимум 60 сек между рассылками
}

# Telegram API лимиты
TELEGRAM_LIMITS = {
    'messages_per_second': 30,  # Telegram: 30 msg/sec globally
    'messages_per_chat_per_second': 1,  # 1 msg/sec per chat
    'bulk_delay_ms': 50,  # задержка между сообщениями при массовой рассылке
}

# Emoji для ролей
ROLE_EMOJI = {
    'student': '🎓',
    'teacher': '👨‍🏫',
    'admin': '⚙️',
}

ROLE_NAMES = {
    'student': 'Ученик',
    'teacher': 'Преподаватель',
    'admin': 'Администратор',
}

# Статусы ДЗ
HW_STATUS_EMOJI = {
    'not_submitted': '⏳',
    'submitted': '🟡',
    'graded': '✅',
    'overdue': '🔴',
}

HW_STATUS_NAMES = {
    'not_submitted': 'Не сдано',
    'submitted': 'На проверке',
    'graded': 'Проверено',
    'overdue': 'Просрочено',
}
