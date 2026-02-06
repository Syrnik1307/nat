"""
Утилиты для работы с Redis - хранение состояний диалогов
"""
import json
import logging
from typing import Optional, Any, Dict
from django.core.cache import cache
from asgiref.sync import sync_to_async

from ..config import DIALOG_STATE_TTL, CACHE_TTL

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


# ===== Async-обёртки для использования в async хендлерах бота =====
# Синхронные cache.get/set блокируют event loop при использовании Redis.
# Эти обёртки корректно делегируют в thread pool через sync_to_async.

async def aget_dialog_state(telegram_id: int) -> Optional[Dict[str, Any]]:
    """Async-обёртка для get_dialog_state (безопасна для event loop)"""
    try:
        return await sync_to_async(get_dialog_state)(telegram_id)
    except Exception as e:
        logger.error(f"Async error getting dialog state for {telegram_id}: {e}")
        return None


async def aset_dialog_state(telegram_id: int, state: Dict[str, Any], ttl: int = None) -> bool:
    """Async-обёртка для set_dialog_state (безопасна для event loop)"""
    try:
        return await sync_to_async(set_dialog_state)(telegram_id, state, ttl)
    except Exception as e:
        logger.error(f"Async error setting dialog state for {telegram_id}: {e}")
        return False


async def aupdate_dialog_state(telegram_id: int, **updates) -> bool:
    """Async-обёртка для update_dialog_state"""
    try:
        return await sync_to_async(update_dialog_state)(telegram_id, **updates)
    except Exception as e:
        logger.error(f"Async error updating dialog state for {telegram_id}: {e}")
        return False


async def aclear_dialog_state(telegram_id: int) -> bool:
    """Async-обёртка для clear_dialog_state (безопасна для event loop)"""
    try:
        return await sync_to_async(clear_dialog_state)(telegram_id)
    except Exception as e:
        logger.error(f"Async error clearing dialog state for {telegram_id}: {e}")
        return False
