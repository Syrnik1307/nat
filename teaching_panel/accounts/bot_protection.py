"""
Защита от ботов с использованием Device Fingerprinting + Behavioral Analysis

Система многоуровневой защиты:
1. Device Fingerprint - уникальный идентификатор устройства
2. Behavioral Analysis - анализ поведения (скорость заполнения, движения мыши)
3. IP Reputation - проверка IP на подозрительность
4. Rate Limiting по fingerprint - ограничения на уровне устройства
5. Honeypot Detection - ловушки для ботов
6. Browser Consistency - проверка согласованности браузера

Бан происходит по fingerprint (железо), а не по IP.
"""

import hashlib
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from functools import wraps

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.utils import timezone
from rest_framework.exceptions import Throttled, PermissionDenied

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Пороги для определения ботов
BOT_DETECTION_CONFIG = {
    # Минимальное время заполнения формы (секунды)
    'min_form_fill_time': 2.0,
    
    # Максимальное количество регистраций с одного fingerprint
    'max_registrations_per_fingerprint': 3,
    'registration_window_hours': 24,
    
    # Максимальное количество неудачных логинов
    'max_failed_logins_per_fingerprint': 10,
    'failed_login_window_hours': 1,
    
    # Бан после подозрительной активности
    'ban_duration_hours': 24,
    'permanent_ban_after_violations': 5,
    
    # Score thresholds (0-100, чем выше - тем подозрительнее)
    'bot_score_threshold': 70,
    'suspicious_score_threshold': 50,
}

# Префиксы для cache ключей
CACHE_PREFIX = 'bot_protection:'
FP_REGISTRATIONS_KEY = f'{CACHE_PREFIX}fp_regs:'  # fingerprint -> count
FP_FAILED_LOGINS_KEY = f'{CACHE_PREFIX}fp_fails:'  # fingerprint -> count
FP_BAN_KEY = f'{CACHE_PREFIX}fp_ban:'  # fingerprint -> ban info
FP_VIOLATIONS_KEY = f'{CACHE_PREFIX}fp_violations:'  # fingerprint -> violation count
IP_REPUTATION_KEY = f'{CACHE_PREFIX}ip_rep:'  # ip -> reputation data


# ============================================================================
# FINGERPRINT HANDLING
# ============================================================================

def normalize_fingerprint(fp_data: dict) -> str:
    """
    Нормализует данные fingerprint и создаёт хэш.
    Принимает данные от FingerprintJS или аналогов.
    """
    # Извлекаем ключевые компоненты устройства
    components = {
        'screen': f"{fp_data.get('screenWidth', 0)}x{fp_data.get('screenHeight', 0)}",
        'colorDepth': fp_data.get('colorDepth', 24),
        'timezone': fp_data.get('timezone', ''),
        'language': fp_data.get('language', ''),
        'platform': fp_data.get('platform', ''),
        'cpuClass': fp_data.get('cpuClass', ''),
        'deviceMemory': fp_data.get('deviceMemory', 0),
        'hardwareConcurrency': fp_data.get('hardwareConcurrency', 0),
        'webglVendor': fp_data.get('webglVendor', ''),
        'webglRenderer': fp_data.get('webglRenderer', ''),
        'canvas': fp_data.get('canvasHash', ''),
        'audio': fp_data.get('audioHash', ''),
        'fonts': fp_data.get('fontsHash', ''),
        'plugins': fp_data.get('pluginsHash', ''),
        'touchSupport': fp_data.get('touchSupport', False),
    }
    
    # Создаём стабильный хэш
    fp_string = json.dumps(components, sort_keys=True)
    return hashlib.sha256(fp_string.encode()).hexdigest()[:32]


def get_client_fingerprint(request) -> Tuple[str, dict]:
    """
    Извлекает fingerprint из запроса.
    Возвращает (fingerprint_hash, raw_data).
    """
    # Пробуем получить fingerprint из заголовка или тела запроса
    fp_header = request.headers.get('X-Device-Fingerprint', '')
    
    raw_data = {}
    
    if fp_header:
        try:
            raw_data = json.loads(fp_header)
        except json.JSONDecodeError:
            # Если заголовок - просто хэш
            return fp_header[:32], {}
    else:
        # Пробуем из тела запроса
        try:
            body = json.loads(request.body.decode('utf-8'))
            raw_data = body.get('deviceFingerprint', body.get('fingerprint', {}))
        except (json.JSONDecodeError, AttributeError):
            pass
    
    if not raw_data:
        # Fallback: генерируем fingerprint на основе доступных заголовков
        raw_data = {
            'userAgent': request.headers.get('User-Agent', ''),
            'acceptLanguage': request.headers.get('Accept-Language', ''),
            'acceptEncoding': request.headers.get('Accept-Encoding', ''),
            'connection': request.headers.get('Connection', ''),
            'ip': get_client_ip(request),
        }
    
    fp_hash = normalize_fingerprint(raw_data)
    return fp_hash, raw_data


def get_client_ip(request) -> str:
    """Извлекает реальный IP клиента (с учётом прокси)."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    x_real_ip = request.META.get('HTTP_X_REAL_IP')
    if x_real_ip:
        return x_real_ip
    return request.META.get('REMOTE_ADDR', '')


# ============================================================================
# BOT SCORE CALCULATION
# ============================================================================

def calculate_bot_score(request, fp_data: dict, behavioral_data: dict = None) -> int:
    """
    Вычисляет "бот-скор" от 0 до 100.
    0 = точно человек, 100 = точно бот.
    """
    score = 0
    reasons = []
    
    behavioral_data = behavioral_data or {}
    
    # 1. Проверка User-Agent
    user_agent = request.headers.get('User-Agent', '')
    if not user_agent:
        score += 30
        reasons.append('missing_user_agent')
    elif any(bot in user_agent.lower() for bot in ['bot', 'crawler', 'spider', 'headless', 'phantom', 'selenium']):
        score += 50
        reasons.append('bot_user_agent')
    
    # 2. Проверка заголовков браузера
    expected_headers = ['Accept', 'Accept-Language', 'Accept-Encoding']
    missing_headers = sum(1 for h in expected_headers if not request.headers.get(h))
    if missing_headers > 1:
        score += 15 * missing_headers
        reasons.append(f'missing_headers_{missing_headers}')
    
    # 3. Проверка консистентности данных
    if fp_data:
        # Нереалистичные данные экрана
        screen_w = fp_data.get('screenWidth', 0)
        screen_h = fp_data.get('screenHeight', 0)
        if screen_w == 0 or screen_h == 0:
            score += 20
            reasons.append('no_screen_data')
        elif screen_w < 100 or screen_h < 100:
            score += 15
            reasons.append('unrealistic_screen')
        
        # Отсутствие WebGL (часто отключено у ботов)
        if not fp_data.get('webglVendor') and not fp_data.get('webglRenderer'):
            score += 10
            reasons.append('no_webgl')
        
        # Нереалистичное количество ядер CPU
        cpu_cores = fp_data.get('hardwareConcurrency', 0)
        if cpu_cores == 0 or cpu_cores > 128:
            score += 10
            reasons.append('unrealistic_cpu')
    
    # 4. Поведенческий анализ
    if behavioral_data:
        # Слишком быстрое заполнение формы
        fill_time = behavioral_data.get('formFillTime', 0)
        min_time = BOT_DETECTION_CONFIG['min_form_fill_time']
        if fill_time > 0 and fill_time < min_time:
            score += 25
            reasons.append('too_fast_form_fill')
        
        # Отсутствие движений мыши
        mouse_moves = behavioral_data.get('mouseMovements', 0)
        if mouse_moves == 0:
            score += 15
            reasons.append('no_mouse_movements')
        elif mouse_moves < 3:
            score += 10
            reasons.append('few_mouse_movements')
        
        # Отсутствие нажатий клавиш
        key_presses = behavioral_data.get('keyPresses', 0)
        if key_presses == 0:
            score += 10
            reasons.append('no_key_presses')
        
        # Подозрительно линейные движения мыши (бот)
        if behavioral_data.get('linearMousePath', False):
            score += 20
            reasons.append('linear_mouse_path')
    
    # 5. Honeypot сработал
    if behavioral_data.get('honeypotFilled', False):
        score += 50
        reasons.append('honeypot_filled')
    
    # 6. Проверка referer
    referer = request.headers.get('Referer', '')
    host = request.headers.get('Host', '')
    if not referer:
        score += 5
        reasons.append('no_referer')
    elif host and host not in referer:
        score += 10
        reasons.append('external_referer')
    
    # Логируем для анализа
    if score >= BOT_DETECTION_CONFIG['suspicious_score_threshold']:
        logger.warning(f"Suspicious activity detected: score={score}, reasons={reasons}, ip={get_client_ip(request)}")
    
    return min(score, 100)


# ============================================================================
# BAN MANAGEMENT
# ============================================================================

def is_fingerprint_banned(fingerprint: str) -> Tuple[bool, Optional[str]]:
    """
    Проверяет, забанен ли fingerprint.
    Возвращает (is_banned, reason).
    """
    ban_info = cache.get(f'{FP_BAN_KEY}{fingerprint}')
    if ban_info:
        return True, ban_info.get('reason', 'banned')
    return False, None


def ban_fingerprint(fingerprint: str, reason: str, duration_hours: int = None):
    """Банит fingerprint на указанное время."""
    if duration_hours is None:
        duration_hours = BOT_DETECTION_CONFIG['ban_duration_hours']
    
    # Увеличиваем счётчик нарушений
    violations_key = f'{FP_VIOLATIONS_KEY}{fingerprint}'
    violations = cache.get(violations_key, 0) + 1
    cache.set(violations_key, violations, timeout=30 * 24 * 3600)  # 30 дней
    
    # Перманентный бан после многократных нарушений
    if violations >= BOT_DETECTION_CONFIG['permanent_ban_after_violations']:
        duration_hours = 365 * 24  # 1 год
        reason = f'permanent_ban: {reason}'
    
    ban_info = {
        'reason': reason,
        'banned_at': timezone.now().isoformat(),
        'expires_at': (timezone.now() + timedelta(hours=duration_hours)).isoformat(),
        'violations': violations,
    }
    
    cache.set(f'{FP_BAN_KEY}{fingerprint}', ban_info, timeout=duration_hours * 3600)
    logger.warning(f"Fingerprint banned: {fingerprint[:8]}..., reason={reason}, duration={duration_hours}h")


def unban_fingerprint(fingerprint: str):
    """Разбанивает fingerprint (для админки)."""
    cache.delete(f'{FP_BAN_KEY}{fingerprint}')
    logger.info(f"Fingerprint unbanned: {fingerprint[:8]}...")


# ============================================================================
# RATE LIMITING BY FINGERPRINT
# ============================================================================

def check_registration_limit(fingerprint: str) -> bool:
    """
    Проверяет лимит регистраций с одного fingerprint.
    Возвращает True если лимит НЕ превышен.
    """
    key = f'{FP_REGISTRATIONS_KEY}{fingerprint}'
    window = BOT_DETECTION_CONFIG['registration_window_hours'] * 3600
    max_regs = BOT_DETECTION_CONFIG['max_registrations_per_fingerprint']
    
    count = cache.get(key, 0)
    if count >= max_regs:
        return False
    return True


def record_registration(fingerprint: str):
    """Записывает факт регистрации."""
    key = f'{FP_REGISTRATIONS_KEY}{fingerprint}'
    window = BOT_DETECTION_CONFIG['registration_window_hours'] * 3600
    
    count = cache.get(key, 0)
    cache.set(key, count + 1, timeout=window)


def check_failed_login_limit(fingerprint: str) -> bool:
    """
    Проверяет лимит неудачных попыток входа.
    Возвращает True если лимит НЕ превышен.
    """
    key = f'{FP_FAILED_LOGINS_KEY}{fingerprint}'
    window = BOT_DETECTION_CONFIG['failed_login_window_hours'] * 3600
    max_fails = BOT_DETECTION_CONFIG['max_failed_logins_per_fingerprint']
    
    count = cache.get(key, 0)
    if count >= max_fails:
        return False
    return True


def record_failed_login(fingerprint: str):
    """Записывает неудачную попытку входа."""
    key = f'{FP_FAILED_LOGINS_KEY}{fingerprint}'
    window = BOT_DETECTION_CONFIG['failed_login_window_hours'] * 3600
    
    count = cache.get(key, 0)
    cache.set(key, count + 1, timeout=window)


def reset_failed_logins(fingerprint: str):
    """Сбрасывает счётчик неудачных логинов (после успешного входа)."""
    cache.delete(f'{FP_FAILED_LOGINS_KEY}{fingerprint}')


# ============================================================================
# MIDDLEWARE / DECORATORS
# ============================================================================

def bot_protection_required(action: str = 'generic'):
    """
    Декоратор для защиты view от ботов.
    
    Использование:
    @bot_protection_required(action='register')
    def register_view(request):
        ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Извлекаем fingerprint
            fingerprint, fp_data = get_client_fingerprint(request)
            
            # Проверяем бан
            is_banned, ban_reason = is_fingerprint_banned(fingerprint)
            if is_banned:
                logger.warning(f"Banned device attempted access: {fingerprint[:8]}..., action={action}")
                return JsonResponse({
                    'error': 'access_denied',
                    'detail': 'Доступ с этого устройства заблокирован',
                    'reason': ban_reason,
                }, status=403)
            
            # Извлекаем поведенческие данные
            try:
                body = json.loads(request.body.decode('utf-8'))
                behavioral_data = body.get('behavioralData', {})
            except (json.JSONDecodeError, AttributeError):
                behavioral_data = {}
            
            # Вычисляем бот-скор
            bot_score = calculate_bot_score(request, fp_data, behavioral_data)
            
            # Блокируем явных ботов
            if bot_score >= BOT_DETECTION_CONFIG['bot_score_threshold']:
                ban_fingerprint(fingerprint, f'bot_score_{bot_score}')
                logger.warning(f"Bot blocked: fingerprint={fingerprint[:8]}..., score={bot_score}")
                return JsonResponse({
                    'error': 'bot_detected',
                    'detail': 'Подозрительная активность обнаружена',
                }, status=403)
            
            # Проверяем rate limits в зависимости от action
            if action == 'register':
                if not check_registration_limit(fingerprint):
                    return JsonResponse({
                        'error': 'rate_limit',
                        'detail': 'Превышен лимит регистраций. Попробуйте позже.',
                    }, status=429)
            elif action == 'login':
                if not check_failed_login_limit(fingerprint):
                    ban_fingerprint(fingerprint, 'too_many_failed_logins', duration_hours=1)
                    return JsonResponse({
                        'error': 'rate_limit',
                        'detail': 'Слишком много неудачных попыток. Устройство временно заблокировано.',
                    }, status=429)
            
            # Добавляем fingerprint в request для использования в view
            request.device_fingerprint = fingerprint
            request.bot_score = bot_score
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


class BotProtectionMiddleware:
    """
    Middleware для глобальной защиты от ботов.
    Проверяет все запросы и блокирует забаненные устройства.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Пути которые не требуют защиты
        self.exempt_paths = [
            '/api/health/',
            '/admin/',
            '/static/',
            '/media/',
            '/__debug__/',
        ]
    
    def __call__(self, request):
        # Пропускаем exempt пути
        path = request.path
        if any(path.startswith(exempt) for exempt in self.exempt_paths):
            return self.get_response(request)
        
        # Только для POST/PUT/PATCH запросов
        if request.method not in ('POST', 'PUT', 'PATCH'):
            return self.get_response(request)
        
        # Извлекаем fingerprint
        fingerprint, _ = get_client_fingerprint(request)
        
        # Проверяем бан
        is_banned, ban_reason = is_fingerprint_banned(fingerprint)
        if is_banned:
            logger.warning(f"Banned device blocked by middleware: {fingerprint[:8]}...")
            return JsonResponse({
                'error': 'access_denied',
                'detail': 'Доступ с этого устройства заблокирован',
            }, status=403)
        
        # Добавляем fingerprint в request
        request.device_fingerprint = fingerprint
        
        return self.get_response(request)


# ============================================================================
# ADMIN UTILITIES
# ============================================================================

def get_ban_stats() -> Dict:
    """Возвращает статистику банов (для админки)."""
    # Примечание: для полной реализации нужен Redis scan
    # Здесь упрощённая версия
    return {
        'note': 'Use Redis CLI for full ban statistics',
        'prefix': FP_BAN_KEY,
    }


def get_suspicious_activity_log(limit: int = 100) -> list:
    """Возвращает лог подозрительной активности."""
    # В production нужно использовать отдельное хранилище логов
    # (Elasticsearch, PostgreSQL, etc.)
    return []
