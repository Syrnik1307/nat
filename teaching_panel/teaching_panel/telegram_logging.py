"""
Telegram Error Handler для Django.
Отправляет 500 ошибки в Telegram в реальном времени.

Добавить в settings.py:
    LOGGING['handlers']['telegram'] = {...}
    LOGGING['loggers']['django.request']['handlers'].append('telegram')
"""
import logging
import requests
import traceback
from django.conf import settings


class TelegramErrorHandler(logging.Handler):
    """
    Отправляет ошибки Django (500) напрямую в Telegram.
    Антиспам: одинаковые ошибки не чаще раз в 5 минут.
    """
    
    _recent_errors = {}  # {error_hash: timestamp}
    COOLDOWN = 300  # 5 минут
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot_token = getattr(settings, 'ERRORS_BOT_TOKEN', '') or getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
        self.chat_id = getattr(settings, 'ERRORS_CHAT_ID', '') or getattr(settings, 'ADMIN_TELEGRAM_CHAT_ID', '')
    
    def emit(self, record):
        if not self.bot_token or not self.chat_id:
            return
        
        try:
            # Антиспам: проверяем не отправляли ли недавно
            import time
            error_hash = hash(f"{record.pathname}:{record.lineno}:{record.msg[:100]}")
            now = time.time()
            
            if error_hash in self._recent_errors:
                if now - self._recent_errors[error_hash] < self.COOLDOWN:
                    return  # Пропускаем
            
            self._recent_errors[error_hash] = now
            
            # Формируем сообщение
            message = self._format_message(record)
            
            # Отправляем
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            requests.post(url, data={
                'chat_id': self.chat_id,
                'text': message[:4000],  # Telegram limit
                'parse_mode': 'HTML',
            }, timeout=5)
            
        except Exception:
            pass  # Не падаем если Telegram недоступен
    
    def _format_message(self, record):
        """Форматирует ошибку для Telegram."""
        exc_info = record.exc_info
        tb = ""
        if exc_info:
            tb = ''.join(traceback.format_exception(*exc_info))[-1500:]
        
        request_info = ""
        if hasattr(record, 'request'):
            req = record.request
            request_info = f"""
<b>Request:</b>
  Method: {req.method}
  Path: {req.path}
  User: {getattr(req, 'user', 'Anonymous')}"""
        
        return f"""🚨 <b>DJANGO ERROR 500</b>

<b>Message:</b> {record.getMessage()[:500]}

<b>Location:</b> {record.pathname}:{record.lineno}
{request_info}

<b>Traceback:</b>
<pre>{tb}</pre>

🕐 {record.asctime if hasattr(record, 'asctime') else 'now'}
"""

# ============================================================
# SLOW REQUEST ALERTER
# ============================================================

class SlowRequestAlerter:
    """
    Отправляет алерты о медленных запросах в Telegram.
    Антиспам: не чаще раза в 15 минут на один endpoint.
    """
    
    _recent_alerts = {}  # {path: timestamp}
    COOLDOWN = 900  # 15 минут
    SLOW_THRESHOLD = 2.0  # секунды
    CRITICAL_THRESHOLD = 5.0  # секунды
    
    @classmethod
    def alert(cls, method, path, duration, user_id):
        """
        Отправляет алерт если запрос медленный.
        
        Args:
            method: HTTP метод
            path: URL путь
            duration: время в секундах
            user_id: ID пользователя или 'anonymous'
        """
        if duration < cls.SLOW_THRESHOLD:
            return
            
        bot_token = getattr(settings, 'ERRORS_BOT_TOKEN', '') or getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
        chat_id = getattr(settings, 'ERRORS_CHAT_ID', '') or getattr(settings, 'ADMIN_TELEGRAM_CHAT_ID', '')
        
        if not bot_token or not chat_id:
            return
        
        try:
            import time
            now = time.time()
            
            # Антиспам: проверяем не отправляли ли недавно для этого endpoint
            cache_key = f"{method}:{path}"
            if cache_key in cls._recent_alerts:
                if now - cls._recent_alerts[cache_key] < cls.COOLDOWN:
                    return
            
            cls._recent_alerts[cache_key] = now
            
            # Определяем уровень критичности
            if duration >= cls.CRITICAL_THRESHOLD:
                emoji = "🚨"
                level = "КРИТИЧЕСКИЙ"
            else:
                emoji = "⚠️"
                level = "МЕДЛЕННЫЙ"
            
            message = f"""{emoji} <b>SLOW REQUEST ALERT</b>

<b>Уровень:</b> {level}
<b>Время ответа:</b> {duration:.2f}s
<b>Endpoint:</b> {method} {path}
<b>User ID:</b> {user_id}

<i>Порог: >{cls.SLOW_THRESHOLD}s (критический: >{cls.CRITICAL_THRESHOLD}s)</i>
<i>Повтор алерта через: {cls.COOLDOWN // 60} мин</i>

🕐 {time.strftime('%Y-%m-%d %H:%M:%S')}"""
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            requests.post(url, data={
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'HTML',
            }, timeout=5)
            
        except Exception:
            pass  # Не падаем если Telegram недоступен


# Глобальный инстанс для использования из middleware
slow_request_alerter = SlowRequestAlerter()