"""
Zoom OAuth Views

Заглушки для Zoom OAuth.
В будущем: реализация полноценного OAuth для индивидуальных Zoom аккаунтов.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status


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
        
        # Очищаем Zoom данные (если поля существуют)
        if hasattr(user, 'zoom_email'):
            user.zoom_email = ''
            user.zoom_user_id = ''
            user.zoom_access_token = ''
            user.zoom_refresh_token = ''
            user.save(update_fields=['zoom_email', 'zoom_user_id', 
                                     'zoom_access_token', 'zoom_refresh_token'])
            
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
        
        # Google Meet OAuth
        google_meet_configured = bool(
            getattr(settings, 'GOOGLE_MEET_ENABLED', False) and
            getattr(settings, 'GOOGLE_MEET_CLIENT_ID', '') and
            getattr(settings, 'GOOGLE_MEET_CLIENT_SECRET', '')
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
                    'available': google_meet_configured,
                    'configured': google_meet_connected,
                    'name': 'Google Meet',
                    'email': getattr(user, 'google_meet_email', '') or '',
                },
            }
        })
