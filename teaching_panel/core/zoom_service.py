import requests
import jwt
import time
import logging
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# Custom Exceptions
class ZoomAPIError(Exception):
    """Базовая ошибка Zoom API"""
    pass

class ZoomRateLimitError(ZoomAPIError):
    """Превышен лимит запросов (429)"""
    pass

class ZoomAuthError(ZoomAPIError):
    """Ошибка аутентификации"""
    pass


def generate_zoom_jwt_token() -> str:
    """
    Генерирует JWT токен для аутентификации в Zoom API с кешированием.
    Требует settings.ZOOM_API_KEY и settings.ZOOM_API_SECRET
    
    Returns:
        str: JWT токен
    
    Raises:
        ZoomAuthError: При ошибке генерации токена
    """
    cache_key = 'zoom_jwt_token'
    
    # Проверяем кеш
    cached_token = cache.get(cache_key)
    if cached_token:
        logger.debug("Using cached Zoom JWT token")
        return cached_token
    
    try:
        # JWT payload
        payload = {
            'iss': settings.ZOOM_API_KEY,  # API Key
            'exp': datetime.utcnow() + timedelta(hours=1)  # Токен действителен 1 час
        }
        
        # Генерация токена
        token = jwt.encode(
            payload,
            settings.ZOOM_API_SECRET,
            algorithm='HS256'
        )
        
        # Кешируем на 50 минут (с запасом)
        cache.set(cache_key, token, 3000)
        logger.info("Generated new Zoom JWT token")
        
        return token
    except Exception as e:
        logger.error(f"Failed to generate JWT token: {e}")
        raise ZoomAuthError(f"Failed to generate JWT token: {str(e)}")


def _make_zoom_request(
    method: str,
    url: str,
    headers: Dict[str, str],
    data: Optional[Dict] = None,
    retry_count: int = 0,
    max_retries: int = 3
) -> requests.Response:
    """
    Выполняет HTTP запрос к Zoom API с exponential backoff retry
    
    Args:
        method: HTTP метод (GET, POST, PATCH, DELETE)
        url: Полный URL запроса
        headers: HTTP заголовки
        data: Данные для POST/PATCH
        retry_count: Текущая попытка
        max_retries: Максимальное количество попыток
    
    Returns:
        Response объект
    
    Raises:
        ZoomRateLimitError: При превышении лимита после всех попыток
        ZoomAPIError: При других ошибках
    """
    try:
        logger.info(f"Zoom API {method} {url} (attempt {retry_count + 1}/{max_retries + 1})")
        
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=data,
            timeout=30
        )
        
        # Обработка rate limit (429)
        if response.status_code == 429:
            if retry_count >= max_retries:
                logger.error(f"Max retries ({max_retries}) exceeded for rate limit")
                raise ZoomRateLimitError("Rate limit exceeded, max retries reached")
            
            # Exponential backoff: 1s, 2s, 4s
            retry_after = int(response.headers.get('Retry-After', 2 ** retry_count))
            logger.warning(f"Rate limit (429), retrying after {retry_after}s")
            
            time.sleep(retry_after)
            return _make_zoom_request(method, url, headers, data, retry_count + 1, max_retries)
        
        # Проверка других ошибок
        if not response.ok:
            logger.error(f"Zoom API error {response.status_code}: {response.text}")
            
        response.raise_for_status()
        return response
        
    except requests.exceptions.Timeout:
        logger.error(f"Request timeout for {url}")
        raise ZoomAPIError("Request timeout")
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        raise ZoomAPIError(f"Request failed: {e}")


def create_zoom_meeting(topic: str, start_time_iso: str, duration: int = 60) -> Tuple[str, str]:
    """
    Создает встречу в Zoom с retry логикой.
    
    Args:
        topic: Название встречи
        start_time_iso: Время начала в ISO формате (например: "2025-11-13T14:00:00Z")
        duration: Продолжительность в минутах (по умолчанию 60)
    
    Returns:
        tuple: (join_url, meeting_id)
    
    Raises:
        ZoomAuthError: При ошибке аутентификации
        ZoomRateLimitError: При превышении rate limit
        ZoomAPIError: При других ошибках API
    """
    
    if not settings.ZOOM_API_KEY or not settings.ZOOM_API_SECRET:
        raise ZoomAuthError("Zoom API credentials not configured. Please set ZOOM_API_KEY and ZOOM_API_SECRET in settings.")
    
    try:
        # 1. Генерируем JWT токен
        token = generate_zoom_jwt_token()
        
        # 2. Подготавливаем заголовки и данные для запроса
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        meeting_data = {
            'topic': topic,
            'type': 2,  # Scheduled meeting
            'start_time': start_time_iso,
            'duration': duration,
            'timezone': 'UTC',
            'settings': {
                'host_video': True,
                'participant_video': True,
                'join_before_host': False,
                'mute_upon_entry': True,
                'watermark': False,
                'audio': 'both',
                'auto_recording': 'none'
            }
        }
        
        # 3. Делаем POST-запрос к Zoom API с retry логикой
        response = _make_zoom_request(
            method='POST',
            url='https://api.zoom.us/v2/users/me/meetings',
            headers=headers,
            data=meeting_data
        )
        
        # 4. Извлекаем данные из ответа
        data = response.json()
        join_url = data.get('join_url')
        meeting_id = data.get('id')
        
        if not join_url or not meeting_id:
            raise ZoomAPIError("Invalid response from Zoom API: missing join_url or meeting_id")
        
        logger.info(f"Created Zoom meeting: {meeting_id} - {topic}")
        return join_url, str(meeting_id)
    
    except ZoomAPIError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating Zoom meeting: {e}")
        raise ZoomAPIError(f"Error creating Zoom meeting: {str(e)}")


def delete_zoom_meeting(meeting_id: str) -> bool:
    """
    Удаляет встречу в Zoom с retry логикой.
    
    Args:
        meeting_id: ID встречи для удаления
    
    Returns:
        bool: True если успешно удалено
    
    Raises:
        ZoomAPIError: При ошибке удаления
    """
    try:
        token = generate_zoom_jwt_token()
        
        headers = {
            'Authorization': f'Bearer {token}',
        }
        
        _make_zoom_request(
            method='DELETE',
            url=f'https://api.zoom.us/v2/meetings/{meeting_id}',
            headers=headers
        )
        
        logger.info(f"Deleted Zoom meeting: {meeting_id}")
        return True
    
    except ZoomAPIError:
        raise
    except Exception as e:
        logger.error(f"Error deleting Zoom meeting {meeting_id}: {e}")
        raise ZoomAPIError(f"Failed to delete Zoom meeting: {str(e)}")


def get_zoom_meeting(meeting_id: str) -> Dict[str, Any]:
    """
    Получает информацию о встрече в Zoom с retry логикой.
    
    Args:
        meeting_id: ID встречи
    
    Returns:
        dict: Информация о встрече
    
    Raises:
        ZoomAPIError: При ошибке получения данных
    """
    try:
        token = generate_zoom_jwt_token()
        
        headers = {
            'Authorization': f'Bearer {token}',
        }
        
        response = _make_zoom_request(
            method='GET',
            url=f'https://api.zoom.us/v2/meetings/{meeting_id}',
            headers=headers
        )
        
        return response.json()
    
    except ZoomAPIError:
        raise
    except Exception as e:
        logger.error(f"Error getting Zoom meeting {meeting_id}: {e}")
        raise ZoomAPIError(f"Failed to get Zoom meeting: {str(e)}")
        
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to get Zoom meeting info: {str(e)}")
