"""
Debug API endpoint to check environment variables
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.conf import settings


@api_view(['GET'])
def debug_env(request):
    """Return current FRONTEND_URL for debugging"""
    return Response({
        'FRONTEND_URL': settings.FRONTEND_URL,
        'DEBUG': settings.DEBUG,
    })
