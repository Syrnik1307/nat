"""
Telegram Error Alerting System для Django.

Продвинутая система уведомлений об ошибках с:
- Структурированными HTML-сообщениями
- Анти-спам механизмом (throttling через Redis)
- Асинхронной отправкой через Celery
- Подсчётом повторяющихся ошибок
- Безопасным fallback при недоступности Redis/Celery

Подключение в settings.py:
    LOGGING['handlers']['telegram'] = {
        'level': 'ERROR',
        'class': 'teaching_panel.telegram_logging.TelegramErrorHandler',
    }
"""
import hashlib
import logging
import time
import traceback
import threading
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

from django.conf import settings


# =============================================================================
# CONFIGURATION
# =============================================================================

class AlertConfig:
    """Конфигурация системы алертинга."""
    
    # Cooldown (секунды) для одинаковых ошибок
    DEDUP_WINDOW = 60  # Окно агрегации - 1 минута
    MIN_COOLDOWN = 30  # Минимальный интервал между алертами одной ошибки
    
    # Лимиты
    MAX_MESSAGE_LENGTH = 4000  # Telegram limit
    MAX_TRACEBACK_LINES = 5   # Последние N строк стека
    MAX_FULL_TB_LENGTH = 2000  # Полный трейсбек для документа
    
    # Эмодзи по уровням
    LEVEL_EMOJI = {
        'CRITICAL': '🔴',
        'ERROR': '🟠',
        'WARNING': '🟡',
        'INFO': '🔵',
    }
    
    # Redis ключи
    REDIS_PREFIX = 'tg_alert:'
    REDIS_TTL = 300  # 5 минут TTL для ключей
    
    # Пути, которые не алертим (healthcheck, etc)
    IGNORE_PATHS = (
        '/api/health/',
        '/favicon.ico',
        '/__debug__/',
    )


# =============================================================================
# ERROR AGGREGATOR (Anti-Spam)
# =============================================================================

class ErrorAggregator:
    """
    Агрегатор ошибок для анти-спам защиты.
    
    Использует Redis если доступен, иначе in-memory fallback.
    Считает количество повторений одной ошибки за окно.
    """
    
    # In-memory fallback storage
    _memory_store: Dict[str, Dict[str, Any]] = {}
    _memory_lock = threading.Lock()
    
    @classmethod
    def _get_redis(cls):
        """Получить Redis client если доступен."""
        try:
            from django_redis import get_redis_connection
            return get_redis_connection("default")
        except Exception:
            return None
    
    @classmethod
    def _get_error_hash(cls, pathname: str, lineno: int, exc_type: str, message: str) -> str:
        """Создаёт уникальный хэш для ошибки."""
        key = f"{pathname}:{lineno}:{exc_type}:{message[:100]}"
        return hashlib.md5(key.encode()).hexdigest()[:16]
    
    @classmethod
    def check_and_count(cls, pathname: str, lineno: int, exc_type: str, message: str) -> Tuple[bool, int]:
        """
        Проверяет ошибку и возвращает (should_send, repeat_count).
        
        Returns:
            (True, 0) - первое появление, отправить сразу
            (True, N) - прошло MIN_COOLDOWN, отправить с счётчиком N повторений
            (False, N) - ещё в cooldown, не отправлять
        """
        error_hash = cls._get_error_hash(pathname, lineno, exc_type, message)
        redis = cls._get_redis()
        
        if redis:
            return cls._check_redis(redis, error_hash)
        return cls._check_memory(error_hash)
    
    @classmethod
    def _check_redis(cls, redis, error_hash: str) -> Tuple[bool, int]:
        """Проверка через Redis."""
        try:
            key = f"{AlertConfig.REDIS_PREFIX}{error_hash}"
            now = time.time()
            
            pipe = redis.pipeline()
            pipe.get(f"{key}:ts")
            pipe.get(f"{key}:count")
            ts_raw, count_raw = pipe.execute()
            
            last_sent = float(ts_raw) if ts_raw else 0
            count = int(count_raw) if count_raw else 0
            
            if last_sent == 0:
                # Первое появление
                pipe = redis.pipeline()
                pipe.setex(f"{key}:ts", AlertConfig.REDIS_TTL, str(now))
                pipe.setex(f"{key}:count", AlertConfig.REDIS_TTL, "1")
                pipe.execute()
                return (True, 0)
            
            # Увеличиваем счётчик
            redis.incr(f"{key}:count")
            redis.expire(f"{key}:count", AlertConfig.REDIS_TTL)
            
            if now - last_sent >= AlertConfig.MIN_COOLDOWN:
                # Cooldown прошёл - отправляем с количеством повторений
                final_count = count + 1
                pipe = redis.pipeline()
                pipe.setex(f"{key}:ts", AlertConfig.REDIS_TTL, str(now))
                pipe.setex(f"{key}:count", AlertConfig.REDIS_TTL, "0")
                pipe.execute()
                return (True, final_count)
            
            return (False, count + 1)
            
        except Exception:
            # Redis сбоил - fallback на memory
            return cls._check_memory(error_hash)
    
    @classmethod
    def _check_memory(cls, error_hash: str) -> Tuple[bool, int]:
        """Проверка через in-memory storage."""
        now = time.time()
        
        with cls._memory_lock:
            if error_hash not in cls._memory_store:
                cls._memory_store[error_hash] = {'ts': now, 'count': 1}
                return (True, 0)
            
            entry = cls._memory_store[error_hash]
            entry['count'] += 1
            
            if now - entry['ts'] >= AlertConfig.MIN_COOLDOWN:
                repeat_count = entry['count'] - 1
                entry['ts'] = now
                entry['count'] = 0
                return (True, repeat_count)
            
            return (False, entry['count'])


# =============================================================================
# MESSAGE FORMATTER
# =============================================================================

class AlertMessageFormatter:
    """Форматирует сообщения об ошибках для Telegram."""
    
    @classmethod
    def format(
        cls,
        level: str,
        message: str,
        pathname: str,
        lineno: int,
        request_info: Optional[Dict[str, Any]] = None,
        exc_info: Optional[tuple] = None,
        repeat_count: int = 0,
    ) -> str:
        """Формирует HTML-сообщение для Telegram."""
        
        emoji = AlertConfig.LEVEL_EMOJI.get(level.upper(), '🔴')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Заголовок
        header = f"{emoji} <b>{level.upper()}</b>"
        if repeat_count > 0:
            header += f" <i>(повторилось {repeat_count}× за последние {AlertConfig.MIN_COOLDOWN}s)</i>"
        
        # Сообщение ошибки
        error_msg = cls._escape_html(message[:500])
        
        # Локация
        short_path = cls._shorten_path(pathname)
        location = f"<code>{short_path}:{lineno}</code>"
        
        # Request info
        request_block = ""
        if request_info:
            method = request_info.get('method', '?')
            path = request_info.get('path', '?')
            user = request_info.get('user', 'Anonymous')
            user_id = request_info.get('user_id', '-')
            
            request_block = f"""
<b>📍 Request:</b>
├ <code>{method} {path}</code>
└ User: {user} (ID: {user_id})"""
        
        # Traceback
        tb_block = ""
        if exc_info and exc_info[0]:
            short_tb = cls._format_short_traceback(exc_info)
            tb_block = f"""
<b>📋 Traceback:</b>
<pre>{short_tb}</pre>"""
        
        # Собираем сообщение
        parts = [
            header,
            "",
            f"<b>💬 Message:</b>",
            f"<code>{error_msg}</code>",
            "",
            f"<b>📁 Location:</b> {location}",
        ]
        
        if request_block:
            parts.append(request_block)
        
        if tb_block:
            parts.append(tb_block)
        
        parts.append("")
        parts.append(f"🕐 <i>{timestamp}</i>")
        
        result = "\n".join(parts)
        
        # Обрезаем если слишком длинное
        if len(result) > AlertConfig.MAX_MESSAGE_LENGTH:
            result = result[:AlertConfig.MAX_MESSAGE_LENGTH - 50] + "\n\n<i>... (обрезано)</i>"
        
        return result
    
    @classmethod
    def _escape_html(cls, text: str) -> str:
        """Экранирует HTML спецсимволы."""
        return (
            text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
        )
    
    @classmethod
    def _shorten_path(cls, pathname: str) -> str:
        """Сокращает путь до относительного от проекта."""
        markers = ('teaching_panel/', 'frontend/')
        for marker in markers:
            if marker in pathname:
                idx = pathname.find(marker)
                return pathname[idx:]
        return pathname.split('/')[-1] if '/' in pathname else pathname
    
    @classmethod
    def _format_short_traceback(cls, exc_info: tuple) -> str:
        """Форматирует краткий traceback (последние N строк)."""
        try:
            lines = traceback.format_exception(*exc_info)
            # Берём последние строки
            relevant = lines[-AlertConfig.MAX_TRACEBACK_LINES:]
            tb_text = ''.join(relevant)
            # Экранируем HTML
            tb_text = cls._escape_html(tb_text)
            # Ограничиваем длину
            if len(tb_text) > 1500:
                tb_text = tb_text[:1500] + "\n..."
            return tb_text.strip()
        except Exception:
            return "Unable to format traceback"
    
    @classmethod
    def format_full_traceback_document(cls, exc_info: tuple) -> Optional[str]:
        """Форматирует полный traceback для отправки файлом."""
        try:
            lines = traceback.format_exception(*exc_info)
            return ''.join(lines)
        except Exception:
            return None


# =============================================================================
# TELEGRAM SENDER
# =============================================================================

class TelegramAlertSender:
    """Отправляет сообщения в Telegram."""
    
    @classmethod
    def send_message(cls, message: str, as_document: bool = False, doc_content: str = None) -> bool:
        """
        Отправляет сообщение в Telegram.
        
        Args:
            message: HTML-текст сообщения
            as_document: отправить ли также файл с полным трейсбеком
            doc_content: содержимое файла
        
        Returns:
            True если успешно
        """
        bot_token = getattr(settings, 'ERRORS_BOT_TOKEN', '') or getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
        chat_id = getattr(settings, 'ERRORS_CHAT_ID', '') or getattr(settings, 'ADMIN_TELEGRAM_CHAT_ID', '')
        
        if not bot_token or not chat_id:
            return False
        
        try:
            import requests
            
            # Отправляем основное сообщение
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            resp = requests.post(url, data={
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True,
            }, timeout=10)
            
            if not resp.ok:
                return False
            
            # Если нужно - отправляем файл с полным трейсбеком
            if as_document and doc_content and len(doc_content) > AlertConfig.MAX_TRACEBACK_LINES * 100:
                cls._send_document(bot_token, chat_id, doc_content)
            
            return True
            
        except Exception:
            return False
    
    @classmethod
    def _send_document(cls, bot_token: str, chat_id: str, content: str):
        """Отправляет файл с трейсбеком."""
        try:
            import requests
            import io
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"traceback_{timestamp}.txt"
            
            url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
            files = {
                'document': (filename, io.BytesIO(content.encode('utf-8')), 'text/plain')
            }
            requests.post(url, data={
                'chat_id': chat_id,
                'caption': '📄 Полный traceback',
            }, files=files, timeout=15)
        except Exception:
            pass  # Не критично


# =============================================================================
# CELERY TASK для асинхронной отправки
# =============================================================================

def send_alert_async(
    level: str,
    message: str,
    pathname: str,
    lineno: int,
    request_info: Optional[Dict[str, Any]] = None,
    full_traceback: Optional[str] = None,
    repeat_count: int = 0,
):
    """
    Отправляет алерт асинхронно через Celery.
    
    Если Celery недоступен - отправляет синхронно в отдельном треде.
    """
    try:
        from teaching_panel.celery import app as celery_app
        
        # Проверяем что Celery работает
        if celery_app.control.ping(timeout=0.5):
            # Отправляем через Celery
            _send_telegram_alert_task.delay(
                level=level,
                message=message,
                pathname=pathname,
                lineno=lineno,
                request_info=request_info,
                full_traceback=full_traceback,
                repeat_count=repeat_count,
            )
            return
    except Exception:
        pass
    
    # Fallback: отправляем в отдельном треде чтобы не блокировать
    thread = threading.Thread(
        target=_send_alert_sync,
        args=(level, message, pathname, lineno, request_info, full_traceback, repeat_count),
        daemon=True,
    )
    thread.start()


def _send_alert_sync(
    level: str,
    message: str,
    pathname: str,
    lineno: int,
    request_info: Optional[Dict[str, Any]],
    full_traceback: Optional[str],
    repeat_count: int,
):
    """Синхронная отправка алерта."""
    try:
        formatted = AlertMessageFormatter.format(
            level=level,
            message=message,
            pathname=pathname,
            lineno=lineno,
            request_info=request_info,
            exc_info=None,  # Уже есть full_traceback
            repeat_count=repeat_count,
        )
        
        # Добавляем краткий traceback если есть
        if full_traceback:
            lines = full_traceback.strip().split('\n')
            short = '\n'.join(lines[-5:])
            formatted = formatted.replace(
                "</code>\n\n<b>📁",
                f"</code>\n\n<b>📋 Traceback:</b>\n<pre>{AlertMessageFormatter._escape_html(short)}</pre>\n\n<b>📁"
            )
        
        TelegramAlertSender.send_message(
            formatted,
            as_document=bool(full_traceback and len(full_traceback) > 500),
            doc_content=full_traceback,
        )
    except Exception:
        pass


# Регистрируем Celery task
try:
    from celery import shared_task
    
    @shared_task(
        name='teaching_panel.telegram_logging.send_telegram_alert',
        bind=True,
        max_retries=2,
        default_retry_delay=5,
        ignore_result=True,
        soft_time_limit=30,
        time_limit=60,
    )
    def _send_telegram_alert_task(
        self,
        level: str,
        message: str,
        pathname: str,
        lineno: int,
        request_info: Optional[Dict[str, Any]] = None,
        full_traceback: Optional[str] = None,
        repeat_count: int = 0,
    ):
        """Celery task для отправки алерта."""
        _send_alert_sync(level, message, pathname, lineno, request_info, full_traceback, repeat_count)
        
except ImportError:
    # Celery не установлен
    _send_telegram_alert_task = None


# =============================================================================
# MAIN HANDLER
# =============================================================================

class TelegramErrorHandler(logging.Handler):
    """
    Django Logging Handler для отправки ошибок в Telegram.
    
    Features:
    - Структурированные HTML-сообщения с эмодзи
    - Анти-спам: агрегация повторяющихся ошибок
    - Асинхронная отправка (Celery или thread)
    - Безопасный: не ломает основной поток при ошибках
    - Thread-safe
    
    Usage in settings.py LOGGING:
        'handlers': {
            'telegram': {
                'level': 'ERROR',
                'class': 'teaching_panel.telegram_logging.TelegramErrorHandler',
            },
        }
    """
    
    _emit_lock = threading.Lock()
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot_token = getattr(settings, 'ERRORS_BOT_TOKEN', '') or getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
        self.chat_id = getattr(settings, 'ERRORS_CHAT_ID', '') or getattr(settings, 'ADMIN_TELEGRAM_CHAT_ID', '')
    
    def emit(self, record: logging.LogRecord):
        """Обрабатывает log record."""
        if not self.bot_token or not self.chat_id:
            return
        
        # Non-blocking acquire для избежания deadlock
        acquired = self._emit_lock.acquire(blocking=False)
        if not acquired:
            return
        
        try:
            self._process_record(record)
        except Exception:
            # НИКОГДА не роняем основной поток
            pass
        finally:
            self._emit_lock.release()
    
    def _process_record(self, record: logging.LogRecord):
        """Обрабатывает запись лога."""
        
        # Извлекаем request info
        request_info = self._extract_request_info(record)
        
        # Проверяем ignored paths
        if request_info:
            path = request_info.get('path', '')
            if any(path.startswith(p) for p in AlertConfig.IGNORE_PATHS):
                return
        
        # Получаем данные об исключении
        exc_type = ""
        if record.exc_info and record.exc_info[0]:
            exc_type = record.exc_info[0].__name__
        
        message = record.getMessage()
        
        # Anti-spam проверка
        should_send, repeat_count = ErrorAggregator.check_and_count(
            pathname=record.pathname,
            lineno=record.lineno,
            exc_type=exc_type,
            message=message,
        )
        
        if not should_send:
            return
        
        # Получаем полный traceback
        full_traceback = None
        if record.exc_info:
            full_traceback = AlertMessageFormatter.format_full_traceback_document(record.exc_info)
        
        # Отправляем асинхронно
        send_alert_async(
            level=record.levelname,
            message=message,
            pathname=record.pathname,
            lineno=record.lineno,
            request_info=request_info,
            full_traceback=full_traceback,
            repeat_count=repeat_count,
        )
    
    def _extract_request_info(self, record: logging.LogRecord) -> Optional[Dict[str, Any]]:
        """Извлекает информацию о HTTP request."""
        if not hasattr(record, 'request'):
            return None
        
        try:
            req = record.request
            user = getattr(req, 'user', None)
            
            if user and hasattr(user, 'is_authenticated') and user.is_authenticated:
                user_str = getattr(user, 'email', None) or getattr(user, 'username', str(user))
                user_id = getattr(user, 'id', '-')
            else:
                user_str = 'Anonymous'
                user_id = '-'
            
            return {
                'method': getattr(req, 'method', '?'),
                'path': getattr(req, 'path', '?'),
                'user': user_str,
                'user_id': user_id,
            }
        except Exception:
            return None


# =============================================================================
# SLOW REQUEST ALERTER (Updated)
# =============================================================================

class SlowRequestAlerter:
    """
    Алерты о медленных запросах с анти-спам защитой.
    
    Features:
    - Красивое форматирование с эмодзи
    - Асинхронная отправка через Celery/thread
    - Нормализация путей для группировки
    - Настраиваемые пороги
    """
    
    # In-memory storage для anti-spam
    _recent_alerts: Dict[str, float] = {}
    _lock = threading.Lock()
    
    # Конфигурация
    COOLDOWN = 900  # 15 минут
    SLOW_THRESHOLD = 3.0  # секунды
    CRITICAL_THRESHOLD = 6.0  # секунды
    
    # Пути которые пропускаем или имеют повышенный порог
    SKIP_PATHS = (
        '/api/health/',
        '/favicon.ico',
    )
    
    RELAXED_PATHS = {
        '/schedule/api/recordings/': 10.0,  # Записи могут грузиться дольше
        '/api/zoom-pool/': 8.0,  # Zoom API медленный
        '/api/homework/submissions/': 8.0,  # Загрузка файлов
    }
    
    @classmethod
    def alert(cls, method: str, path: str, duration: float, user_id: str = 'anonymous'):
        """
        Отправляет алерт если запрос медленный.
        
        Args:
            method: HTTP метод
            path: URL путь
            duration: время в секундах
            user_id: ID пользователя
        """
        # Проверяем пропускаемые пути
        if any(path.startswith(p) for p in cls.SKIP_PATHS):
            return
        
        # Проверяем пути с повышенным порогом
        threshold = cls.SLOW_THRESHOLD
        for relaxed_path, relaxed_threshold in cls.RELAXED_PATHS.items():
            if path.startswith(relaxed_path):
                threshold = relaxed_threshold
                break
        
        if duration < threshold:
            return
        
        # Anti-spam проверка
        if not cls._check_cooldown(method, path):
            return
        
        # Отправляем в отдельном треде
        thread = threading.Thread(
            target=cls._send_alert,
            args=(method, path, duration, user_id, threshold),
            daemon=True,
        )
        thread.start()
    
    @classmethod
    def _check_cooldown(cls, method: str, path: str) -> bool:
        """Проверяет можно ли отправить алерт (anti-spam)."""
        import re
        
        # Нормализуем путь
        normalized = path
        normalized = re.sub(r'/\d+/', '/<id>/', normalized)
        normalized = re.sub(r'/[a-f0-9-]{36}/', '/<uuid>/', normalized)
        
        cache_key = f"{method}:{normalized}"
        now = time.time()
        
        with cls._lock:
            if cache_key in cls._recent_alerts:
                if now - cls._recent_alerts[cache_key] < cls.COOLDOWN:
                    return False
            cls._recent_alerts[cache_key] = now
            return True
    
    @classmethod
    def _send_alert(cls, method: str, path: str, duration: float, user_id: str, threshold: float):
        """Отправляет алерт о медленном запросе."""
        try:
            bot_token = getattr(settings, 'ERRORS_BOT_TOKEN', '') or getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
            chat_id = getattr(settings, 'ERRORS_CHAT_ID', '') or getattr(settings, 'ADMIN_TELEGRAM_CHAT_ID', '')
            
            if not bot_token or not chat_id:
                return
            
            # Определяем уровень
            if duration >= cls.CRITICAL_THRESHOLD:
                emoji = "🔴"
                level = "CRITICAL"
            elif duration >= threshold * 1.5:
                emoji = "🟠"
                level = "SLOW"
            else:
                emoji = "🟡"
                level = "WARNING"
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            message = f"""{emoji} <b>SLOW REQUEST: {level}</b>

<b>⏱ Response Time:</b> <code>{duration:.2f}s</code>
<b>📍 Endpoint:</b> <code>{method} {path}</code>
<b>👤 User ID:</b> {user_id}

<i>Threshold: {threshold:.1f}s | Critical: {cls.CRITICAL_THRESHOLD:.1f}s</i>
<i>Next alert for this endpoint: {cls.COOLDOWN // 60} min</i>

🕐 <i>{timestamp}</i>"""
            
            import requests
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            requests.post(url, data={
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True,
            }, timeout=10)
            
        except Exception:
            pass


# Глобальный инстанс
slow_request_alerter = SlowRequestAlerter()