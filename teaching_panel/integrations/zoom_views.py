"""
Zoom OAuth Views

Заглушки для Zoom OAuth.
В будущем: реализация полноценного OAuth для индивидуальных Zoom аккаунтов.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


class ZoomSaveCredentialsView(APIView):
    """
    POST /api/integrations/zoom/save-credentials/
    
    Сохраняет Zoom Server-to-Server OAuth credentials учителя.
    Каждый учитель создаёт своё приложение в Zoom Marketplace.
    
    Body:
    {
        "account_id": "xxx",
        "client_id": "xxx",
        "client_secret": "xxx"
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        account_id = request.data.get('account_id', '').strip()
        client_id = request.data.get('client_id', '').strip()
        client_secret = request.data.get('client_secret', '').strip()
        
        # Валидация
        if not account_id:
            return Response(
                {'detail': 'Account ID обязателен'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not client_id:
            return Response(
                {'detail': 'Client ID обязателен'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not client_secret:
            return Response(
                {'detail': 'Client Secret обязателен'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = request.user
        
        # Сохраняем credentials
        user.zoom_account_id = account_id
        user.zoom_client_id = client_id
        user.zoom_client_secret = client_secret
        user.save(update_fields=['zoom_account_id', 'zoom_client_id', 'zoom_client_secret'])
        
        logger.info(f"User {user.email} saved Zoom S2S credentials")
        
        return Response({
            'success': True,
            'detail': 'Zoom credentials сохранены'
        })


class ZoomAuthURLView(APIView):
    """Получение URL для авторизации Zoom OAuth."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # TODO: Реализовать Zoom OAuth когда будут готовы ключи приложения
        return Response(
            {'detail': 'Zoom OAuth пока не настроен. Обратитесь к администратору.'},
            status=status.HTTP_501_NOT_IMPLEMENTED
        )


class ZoomCallbackView(APIView):
    """Callback после авторизации Zoom OAuth."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        return Response(
            {'detail': 'Zoom OAuth не реализован'},
            status=status.HTTP_501_NOT_IMPLEMENTED
        )


class ZoomDisconnectView(APIView):
    """Отключение Zoom аккаунта."""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        
        # Очищаем все Zoom данные
        fields_to_clear = []
        
        # S2S OAuth credentials
        if hasattr(user, 'zoom_account_id'):
            user.zoom_account_id = ''
            fields_to_clear.append('zoom_account_id')
        if hasattr(user, 'zoom_client_id'):
            user.zoom_client_id = ''
            fields_to_clear.append('zoom_client_id')
        if hasattr(user, 'zoom_client_secret'):
            user.zoom_client_secret = ''
            fields_to_clear.append('zoom_client_secret')
        
        # Legacy OAuth fields
        if hasattr(user, 'zoom_email'):
            user.zoom_email = ''
            fields_to_clear.append('zoom_email')
        if hasattr(user, 'zoom_user_id'):
            user.zoom_user_id = ''
            fields_to_clear.append('zoom_user_id')
        if hasattr(user, 'zoom_access_token'):
            user.zoom_access_token = ''
            fields_to_clear.append('zoom_access_token')
        if hasattr(user, 'zoom_refresh_token'):
            user.zoom_refresh_token = ''
            fields_to_clear.append('zoom_refresh_token')
        
        if fields_to_clear:
            user.save(update_fields=fields_to_clear)
            
        return Response({'detail': 'Zoom отключён'})


class ZoomStatusView(APIView):
    """Проверка статуса подключения Zoom."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        from django.conf import settings
        
        user = request.user
        # Zoom через личные credentials учителя
        personal_connected = user.is_zoom_connected() if hasattr(user, 'is_zoom_connected') else False
        
        # Проверяем настроен ли Zoom OAuth на сервере
        zoom_oauth_configured = bool(
            getattr(settings, 'ZOOM_ACCOUNT_ID', '') and
            getattr(settings, 'ZOOM_CLIENT_ID', '') and
            getattr(settings, 'ZOOM_CLIENT_SECRET', '')
        )
        
        return Response({
            'configured': zoom_oauth_configured,  # Серверный пул настроен
            'connected': personal_connected,
            'email': getattr(user, 'zoom_user_id', '') or ''
        })


class PlatformsAvailabilityView(APIView):
    """
    GET /api/integrations/platforms/
    
    Returns availability status of all video platforms.
    Used by frontend to show/hide platform options.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        from django.conf import settings
        
        user = request.user
        
        # Zoom pool (server-level S2S OAuth)
        zoom_pool_configured = bool(
            getattr(settings, 'ZOOM_ACCOUNT_ID', '') and
            getattr(settings, 'ZOOM_CLIENT_ID', '') and
            getattr(settings, 'ZOOM_CLIENT_SECRET', '')
        )
        
        # Google Meet - теперь всегда доступен, т.к. каждый учитель вводит свои credentials
        # Проверяем, ввёл ли учитель свои credentials
        has_google_credentials = bool(
            getattr(user, 'google_meet_client_id', '') and
            getattr(user, 'google_meet_client_secret', '')
        )
        
        # User connection status
        zoom_personal_connected = user.is_zoom_connected() if hasattr(user, 'is_zoom_connected') else False
        google_meet_connected = user.is_google_meet_connected() if hasattr(user, 'is_google_meet_connected') else False
        
        return Response({
            'platforms': {
                'zoom_pool': {
                    'available': zoom_pool_configured,
                    'name': 'Zoom (пул платформы)',
                    'description': 'Общий пул Zoom аккаунтов платформы',
                },
                'zoom_personal': {
                    'available': True,  # Учитель всегда может настроить свои credentials
                    'configured': zoom_personal_connected,
                    'name': 'Zoom (личный)',
                    'email': getattr(user, 'zoom_user_id', '') or '',
                },
                'google_meet': {
                    'available': True,  # Всегда доступен - учитель вводит свои OAuth credentials
                    'configured': google_meet_connected,
                    'has_credentials': has_google_credentials,  # Указывает, ввёл ли учитель credentials
                    'name': 'Google Meet',
                    'email': getattr(user, 'google_meet_email', '') or '',
                },
            }
        })
