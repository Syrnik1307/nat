"""
Zoom API Client для создания встреч
Использует Server-to-Server OAuth (рекомендуемый метод)
"""
import requests
import time
import logging
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class ZoomAPIClient:
    """Клиент для работы с Zoom API через Server-to-Server OAuth"""
    
    BASE_URL = 'https://api.zoom.us/v2'
    TOKEN_URL = 'https://zoom.us/oauth/token'
    
    def __init__(self, account_id, client_id, client_secret):
        """
        Инициализация клиента.
        
        ВАЖНО: Все credentials ОБЯЗАТЕЛЬНЫ. Глобальные fallback убраны.
        Каждый учитель должен иметь свои Zoom credentials.
        
        Args:
            account_id: Zoom Account ID (обязательный)
            client_id: Zoom Client ID (обязательный)
            client_secret: Zoom Client Secret (обязательный)
        
        Raises:
            ValueError: если любой из credentials не передан
        """
        if not account_id or not client_id or not client_secret:
            raise ValueError(
                'Zoom credentials не настроены. '
                'Укажите zoom_account_id, zoom_client_id и zoom_client_secret в профиле учителя.'
            )
        self.account_id = account_id
        self.client_id = client_id
        self.client_secret = client_secret
    
    def _get_access_token(self):
        """
        Получить OAuth токен с кешированием.
        Токены Zoom действуют 1 час, кешируем на 50 минут.
        """
        import time as _time
        start = _time.time()
        
        # Уникальный ключ кеша для каждого аккаунта
        cache_key = f'zoom_oauth_token_{self.account_id}'
        logger.info(f"[ZOOM_PERF] Checking cache with key: {cache_key}")
        
        cached_token = cache.get(cache_key)
        cache_check_time = _time.time() - start
        logger.info(f"[ZOOM_PERF] Cache check took {cache_check_time:.3f}s, found: {bool(cached_token)}")
        
        if cached_token:
            logger.info(f"[ZOOM_PERF] Using cached Zoom OAuth token for account {self.account_id}")
            return cached_token
        
        try:
            oauth_start = _time.time()
            response = requests.post(
                self.TOKEN_URL,
                params={
                    'grant_type': 'account_credentials',
                    'account_id': self.account_id
                },
                auth=(self.client_id, self.client_secret),
                timeout=10
            )
            oauth_time = _time.time() - oauth_start
            logger.info(f"[ZOOM_PERF] OAuth request took {oauth_time:.3f}s")
            
            # Подробное логирование для отладки
            logger.info(f"Zoom OAuth request: POST {self.TOKEN_URL}")
            logger.info(f"Account ID: {self.account_id}")
            logger.info(f"Client ID: {self.client_id}")
            logger.info(f"Response status: {response.status_code}")
            
            if not response.ok:
                logger.error(f"Response body: {response.text}")
            
            response.raise_for_status()
            
            data = response.json()
            access_token = data['access_token']
            
            # Кешируем на 58 минут (токен действует 60 минут)
            # Максимум чтобы токен почти никогда не истекал между запросами
            cache.set(cache_key, access_token, 3480)
            logger.info(f"[ZOOM_PERF] Cached new Zoom OAuth token for 58 minutes")
            
            return access_token
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get Zoom OAuth token: {e}")
            raise Exception(f"Zoom authentication failed: {str(e)}")
    
    def create_meeting(self, user_id='me', topic='Meeting', start_time=None, duration=60, auto_record=False):
        """
        Создание встречи Zoom
        
        Args:
            user_id: ID пользователя Zoom (по умолчанию 'me' - текущий аккаунт)
            topic: Тема встречи
            start_time: Время начала (datetime или str ISO)
            duration: Длительность в минутах
            auto_record: Автоматически записывать встречу (True/False)
        
        Returns:
            dict: {
                'id': meeting_id,
                'start_url': url для хоста,
                'join_url': url для участников,
                'password': пароль встречи
            }
        """
        import time as _time
        total_start = _time.time()
        logger.info("[ZOOM_PERF] Starting create_meeting")
        
        try:
            token_start = _time.time()
            access_token = self._get_access_token()
            token_time = _time.time() - token_start
            logger.info(f"[ZOOM_PERF] Token acquisition took {token_time:.3f}s")
            
            # Форматируем время начала
            if isinstance(start_time, datetime):
                start_time_str = start_time.strftime('%Y-%m-%dT%H:%M:%S')
            elif isinstance(start_time, str):
                start_time_str = start_time
            else:
                start_time_str = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
            
            # Определяем настройку записи
            # 'none' - не записывать
            # 'cloud' - записывать в облако Zoom (требуется Pro+ аккаунт)
            # 'local' - записывать локально на компьютер хоста
            recording_type = 'cloud' if auto_record else 'none'
            
            # Данные встречи
            meeting_data = {
                'topic': topic,
                'type': 2,  # Scheduled meeting
                'start_time': start_time_str,
                'duration': duration,
                'timezone': 'UTC',
                'settings': {
                    'host_video': True,
                    'participant_video': True,
                    'join_before_host': False,
                    'mute_upon_entry': True,
                    'waiting_room': False,
                    'audio': 'both',
                    'auto_recording': recording_type  # 'cloud' если auto_record=True
                }
            }
            
            # Создаем встречу
            api_start = _time.time()
            response = requests.post(
                f'{self.BASE_URL}/users/{user_id}/meetings',
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                },
                json=meeting_data,
                timeout=30
            )
            api_time = _time.time() - api_start
            logger.info(f"[ZOOM_PERF] API request took {api_time:.3f}s")
            
            response.raise_for_status()
            result = response.json()
            
            total_time = _time.time() - total_start
            logger.info(f"[ZOOM_PERF] create_meeting total time: {total_time:.3f}s")
            logger.info(f"Created Zoom meeting: {result['id']}")
            
            return {
                'id': str(result['id']),
                'start_url': result['start_url'],
                'join_url': result['join_url'],
                'password': result.get('password', '')
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create Zoom meeting: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise Exception(f"Failed to create Zoom meeting: {str(e)}")
    
    def end_meeting(self, meeting_id):
        """Завершение встречи"""
        try:
            access_token = self._get_access_token()
            
            response = requests.put(
                f'{self.BASE_URL}/meetings/{meeting_id}/status',
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                },
                json={'action': 'end'},
                timeout=30
            )
            
            response.raise_for_status()
            logger.info(f"Ended Zoom meeting: {meeting_id}")
            
            return {'status': 'ended', 'id': meeting_id}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to end Zoom meeting: {e}")
            raise Exception(f"Failed to end meeting: {str(e)}")

    def list_user_recordings(self, user_id='me', from_date=None, to_date=None, page_size=50):
        """Возвращает облачные записи Zoom для пользователя за указанный период."""
        try:
            access_token = self._get_access_token()

            # По умолчанию берем последние 3 дня, чтобы поймать свежие уроки
            now = datetime.utcnow()
            default_from = (now - timedelta(days=3)).date().isoformat()
            default_to = now.date().isoformat()

            params = {
                'from': from_date or default_from,
                'to': to_date or default_to,
                'page_size': page_size,
            }

            response = requests.get(
                f'{self.BASE_URL}/users/{user_id}/recordings',
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                },
                params=params,
                timeout=30
            )

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to list Zoom recordings: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise Exception(f"Failed to list Zoom recordings: {str(e)}")


# Глобальный экземпляр убран - каждый учитель использует свои credentials
# my_zoom_api_client = ZoomAPIClient()  # УДАЛЕНО: нет глобальных credentials

