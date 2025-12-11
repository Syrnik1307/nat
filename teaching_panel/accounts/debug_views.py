"""
Debug API endpoint to check environment variables
ВНИМАНИЕ: Только для разработки! В production должен быть отключен.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from django.conf import settings


@api_view(['GET'])
@permission_classes([IsAdminUser])  # БЕЗОПАСНОСТЬ: Только для админов
def debug_env(request):
    """Return current FRONTEND_URL for debugging - ADMIN ONLY"""
    if not settings.DEBUG:
        return Response({'error': 'Debug endpoints disabled in production'}, status=403)
    
    return Response({
        'FRONTEND_URL': settings.FRONTEND_URL,
        'DEBUG': settings.DEBUG,
    })
