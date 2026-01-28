"""
Утилиты для работы с Redis - хранение состояний диалогов
"""
import json
import logging
from typing import Optional, Any, Dict
from django.core.cache import cache

from .config import DIALOG_STATE_TTL, CACHE_TTL

logger = logging.getLogger(__name__)


def _make_dialog_key(telegram_id: int) -> str:
    """Генерирует ключ для состояния диалога"""
    return f"bot:dialog:{telegram_id}"


def _make_cache_key(prefix: str, *args) -> str:
    """Генерирует ключ для кэша"""
    parts = [str(a) for a in args]
    return f"bot:{prefix}:{':'.join(parts)}"


def get_dialog_state(telegram_id: int) -> Optional[Dict[str, Any]]:
    """Получает текущее состояние диалога пользователя"""
    key = _make_dialog_key(telegram_id)
    try:
        data = cache.get(key)
        if data:
            return json.loads(data) if isinstance(data, str) else data
    except Exception as e:
        logger.error(f"Error getting dialog state for {telegram_id}: {e}")
    return None


def set_dialog_state(telegram_id: int, state: Dict[str, Any], ttl: int = None) -> bool:
    """Сохраняет состояние диалога"""
    key = _make_dialog_key(telegram_id)
    ttl = ttl or DIALOG_STATE_TTL
    try:
        cache.set(key, json.dumps(state, ensure_ascii=False, default=str), ttl)
        return True
    except Exception as e:
        logger.error(f"Error setting dialog state for {telegram_id}: {e}")
        return False


def update_dialog_state(telegram_id: int, **updates) -> bool:
    """Обновляет часть состояния диалога"""
    state = get_dialog_state(telegram_id) or {}
    state.update(updates)
    return set_dialog_state(telegram_id, state)


def clear_dialog_state(telegram_id: int) -> bool:
    """Очищает состояние диалога"""
    key = _make_dialog_key(telegram_id)
    try:
        cache.delete(key)
        return True
    except Exception as e:
        logger.error(f"Error clearing dialog state for {telegram_id}: {e}")
        return False


def get_cached_data(prefix: str, *args) -> Optional[Any]:
    """Получает кэшированные данные"""
    key = _make_cache_key(prefix, *args)
    try:
        data = cache.get(key)
        if data:
            return json.loads(data) if isinstance(data, str) else data
    except Exception as e:
        logger.error(f"Error getting cached data {key}: {e}")
    return None


def set_cached_data(prefix: str, *args, data: Any, ttl: int = None) -> bool:
    """Кэширует данные"""
    key = _make_cache_key(prefix, *args)
    ttl = ttl or CACHE_TTL
    try:
        cache.set(key, json.dumps(data, ensure_ascii=False, default=str), ttl)
        return True
    except Exception as e:
        logger.error(f"Error caching data {key}: {e}")
        return False


def invalidate_cache(prefix: str, *args) -> bool:
    """Инвалидирует кэш"""
    key = _make_cache_key(prefix, *args)
    try:
        cache.delete(key)
        return True
    except Exception as e:
        logger.error(f"Error invalidating cache {key}: {e}")
        return False
