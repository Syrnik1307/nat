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
        user = request.user
        connected = bool(getattr(user, 'zoom_email', None))
        
        return Response({
            'connected': connected,
            'email': getattr(user, 'zoom_email', '') if connected else None
        })
