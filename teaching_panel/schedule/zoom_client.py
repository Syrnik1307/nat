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
    
    def __init__(self, account_id=None, client_id=None, client_secret=None):
        """
        Инициализация клиента.
        Если credentials не переданы, используются из settings (глобальные).
        """
        self.account_id = account_id or settings.ZOOM_ACCOUNT_ID
        self.client_id = client_id or settings.ZOOM_CLIENT_ID
        self.client_secret = client_secret or settings.ZOOM_CLIENT_SECRET
    
    def _get_access_token(self):
        """
        Получить OAuth токен с кешированием.
        Токены Zoom действуют 1 час, кешируем на 50 минут.
        """
        # Уникальный ключ кеша для каждого аккаунта
        cache_key = f'zoom_oauth_token_{self.account_id}'
        cached_token = cache.get(cache_key)
        
        if cached_token:
            logger.debug(f"Using cached Zoom OAuth token for account {self.account_id}")
            return cached_token
        
        try:
            response = requests.post(
                self.TOKEN_URL,
                params={
                    'grant_type': 'account_credentials',
                    'account_id': self.account_id
                },
                auth=(self.client_id, self.client_secret),
                timeout=10
            )
            
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
            
            # Кешируем на 50 минут (токен действует 60 минут)
            cache.set(cache_key, access_token, 3000)
            logger.info("Generated new Zoom OAuth token")
            
            return access_token
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get Zoom OAuth token: {e}")
            raise Exception(f"Zoom authentication failed: {str(e)}")
    
    def create_meeting(self, user_id='me', topic='Meeting', start_time=None, duration=60):
        """
        Создание встречи Zoom
        
        Args:
            user_id: ID пользователя Zoom (по умолчанию 'me' - текущий аккаунт)
            topic: Тема встречи
            start_time: Время начала (datetime или str ISO)
            duration: Длительность в минутах
        
        Returns:
            dict: {
                'id': meeting_id,
                'start_url': url для хоста,
                'join_url': url для участников,
                'password': пароль встречи
            }
        """
        try:
            access_token = self._get_access_token()
            
            # Форматируем время начала
            if isinstance(start_time, datetime):
                start_time_str = start_time.strftime('%Y-%m-%dT%H:%M:%S')
            elif isinstance(start_time, str):
                start_time_str = start_time
            else:
                start_time_str = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
            
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
                    'auto_recording': 'none'
                }
            }
            
            # Создаем встречу
            response = requests.post(
                f'{self.BASE_URL}/users/{user_id}/meetings',
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                },
                json=meeting_data,
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
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


# Глобальный экземпляр для использования в views
my_zoom_api_client = ZoomAPIClient()

