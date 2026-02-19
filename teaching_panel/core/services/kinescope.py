"""
Kinescope API v1 клиент для загрузки и управления видео.

Документация: https://kinescope.io/dev/api/video
API Base: https://api.kinescope.io/v1

Используется для тенантов с настройкой video_provider='kinescope'.
"""
import logging
import requests
from dataclasses import dataclass
from typing import Optional
from django.conf import settings

logger = logging.getLogger(__name__)

KINESCOPE_API_BASE = 'https://api.kinescope.io/v1'


@dataclass
class KinescopeVideo:
    """Результат операции с видео в Kinescope."""
    video_id: str
    embed_link: str
    status: str  # 'uploading', 'processing', 'done', 'error'
    title: str = ''
    duration: float = 0.0
    play_link: str = ''


class KinescopeAPIError(Exception):
    """Ошибка при работе с Kinescope API."""

    def __init__(self, message: str, status_code: int = 0, response_data: dict = None):
        self.status_code = status_code
        self.response_data = response_data or {}
        super().__init__(message)


class KinescopeClient:
    """
    Клиент Kinescope API v1.

    Использование:
        client = KinescopeClient(api_token='Bearer xxx', project_id='abc123')
        video = client.upload_video(file, title='Урок 1')
        info = client.get_video(video.video_id)
        client.delete_video(video.video_id)
    """

    def __init__(self, api_token: str, project_id: str, workspace_id: str = ''):
        self.api_token = api_token
        self.project_id = project_id
        self.workspace_id = workspace_id
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_token}',
        })

    def _url(self, path: str) -> str:
        return f'{KINESCOPE_API_BASE}{path}'

    def _handle_response(self, response: requests.Response, operation: str) -> dict:
        """Обработка ответа API с логированием."""
        try:
            data = response.json()
        except ValueError:
            data = {}

        if response.status_code >= 400:
            error_msg = data.get('error', {}).get('message', response.text)
            logger.error(
                'Kinescope API error [%s]: %s (HTTP %d)',
                operation, error_msg, response.status_code
            )
            raise KinescopeAPIError(
                f'Kinescope {operation} failed: {error_msg}',
                status_code=response.status_code,
                response_data=data
            )

        return data

    # ── Загрузка видео ────────────────────────────────────────

    def upload_video(
        self,
        file,
        title: str,
        description: str = '',
        folder_id: str = '',
    ) -> KinescopeVideo:
        """
        Загрузить видео в Kinescope.

        Args:
            file: Файл-объект (Django UploadedFile / file-like)
            title: Название видео
            description: Описание
            folder_id: ID папки в проекте (опционально)

        Returns:
            KinescopeVideo с данными загруженного видео
        """
        logger.info('Kinescope: uploading video "%s" to project %s', title, self.project_id)

        # Шаг 1: Создаём видео через API
        payload = {
            'project_id': self.project_id,
            'title': title,
            'description': description,
        }
        if folder_id:
            payload['folder_id'] = folder_id

        create_resp = self.session.post(
            self._url('/videos'),
            json=payload,
        )
        create_data = self._handle_response(create_resp, 'create_video')
        video_data = create_data.get('data', {})
        video_id = video_data.get('id', '')

        if not video_id:
            raise KinescopeAPIError('No video_id returned from Kinescope create')

        # Шаг 2: Загружаем файл
        upload_url = video_data.get('upload_url', '')

        if upload_url:
            # Используем resumable upload URL от Kinescope
            file.seek(0)
            upload_resp = requests.put(
                upload_url,
                data=file,
                headers={
                    'Content-Type': 'application/octet-stream',
                },
            )
            if upload_resp.status_code >= 400:
                logger.error('Kinescope upload failed: HTTP %d', upload_resp.status_code)
                raise KinescopeAPIError(
                    f'Upload to Kinescope failed: HTTP {upload_resp.status_code}',
                    status_code=upload_resp.status_code,
                )
        else:
            # Fallback: загрузка через multipart
            file.seek(0)
            upload_resp = self.session.post(
                self._url(f'/videos/{video_id}/upload'),
                files={'file': (title, file, 'video/mp4')},
            )
            self._handle_response(upload_resp, 'upload_file')

        embed_link = video_data.get('embed_link', f'https://kinescope.io/embed/{video_id}')
        play_link = video_data.get('play_link', '')

        logger.info('Kinescope: video uploaded, id=%s, embed=%s', video_id, embed_link)

        return KinescopeVideo(
            video_id=video_id,
            embed_link=embed_link,
            status='processing',
            title=title,
            play_link=play_link,
        )

    # ── Получение информации о видео ─────────────────────────

    def get_video(self, video_id: str) -> KinescopeVideo:
        """Получить информацию о видео по ID."""
        resp = self.session.get(self._url(f'/videos/{video_id}'))
        data = self._handle_response(resp, 'get_video')
        video = data.get('data', {})

        status_map = {
            'done': 'ready',
            'error': 'error',
            'awaiting': 'processing',
            'processing': 'processing',
        }
        ks_status = video.get('status', 'processing')

        return KinescopeVideo(
            video_id=video_id,
            embed_link=video.get('embed_link', f'https://kinescope.io/embed/{video_id}'),
            status=status_map.get(ks_status, 'processing'),
            title=video.get('title', ''),
            duration=video.get('duration', 0.0),
            play_link=video.get('play_link', ''),
        )

    # ── Удаление видео ────────────────────────────────────────

    def delete_video(self, video_id: str) -> bool:
        """Удалить видео из Kinescope."""
        logger.info('Kinescope: deleting video %s', video_id)
        resp = self.session.delete(self._url(f'/videos/{video_id}'))
        if resp.status_code == 204 or resp.status_code == 200:
            return True
        self._handle_response(resp, 'delete_video')
        return False

    # ── Список видео в проекте ────────────────────────────────

    def list_videos(self, page: int = 1, per_page: int = 25) -> dict:
        """Получить список видео в проекте."""
        resp = self.session.get(
            self._url('/videos'),
            params={
                'project_id': self.project_id,
                'page': page,
                'per_page': per_page,
            }
        )
        return self._handle_response(resp, 'list_videos')

    # ── Обновление видео ──────────────────────────────────────

    def update_video(self, video_id: str, title: str = None, description: str = None) -> dict:
        """Обновить метаданные видео."""
        payload = {}
        if title is not None:
            payload['title'] = title
        if description is not None:
            payload['description'] = description

        if not payload:
            return {}

        resp = self.session.patch(
            self._url(f'/videos/{video_id}'),
            json=payload,
        )
        return self._handle_response(resp, 'update_video')


def get_kinescope_client(tenant) -> Optional[KinescopeClient]:
    """
    Получить Kinescope клиент для тенанта. Возвращает None если Kinescope не настроен.

    Args:
        tenant: Tenant instance

    Returns:
        KinescopeClient или None
    """
    try:
        video_settings = tenant.video_settings
    except Exception:
        return None

    if not video_settings.is_kinescope or not video_settings.kinescope_configured:
        return None

    return KinescopeClient(
        api_token=video_settings.kinescope_api_token,
        project_id=video_settings.kinescope_project_id,
        workspace_id=video_settings.kinescope_workspace_id,
    )
