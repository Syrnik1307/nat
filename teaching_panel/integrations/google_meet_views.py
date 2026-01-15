"""
Google Meet Integration Views

Handles OAuth2 callback and API endpoints for Google Meet integration.
"""

import logging
import secrets
from urllib.parse import urlencode

from django.conf import settings
from django.shortcuts import redirect
from django.http import HttpResponseRedirect
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .google_meet_service import (
    GoogleMeetService,
    GoogleMeetNotConfiguredError,
    GoogleMeetError,
    connect_google_meet,
    disconnect_google_meet,
)

logger = logging.getLogger(__name__)


class GoogleMeetAuthURLView(APIView):
    """
    GET /api/integrations/google-meet/auth-url/
    
    Returns the OAuth authorization URL for Google Meet.
    User should be redirected to this URL to start the OAuth flow.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Only teachers can connect Google Meet
        if getattr(request.user, 'role', '') != 'teacher':
            return Response(
                {'detail': 'Только учителя могут подключить Google Meet'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            service = GoogleMeetService()
            
            # Generate state token for CSRF protection
            state = secrets.token_urlsafe(32)
            
            # Store state in session for validation in callback
            request.session['google_meet_oauth_state'] = state
            request.session.modified = True
            
            auth_url = service.get_auth_url(state=state)
            
            return Response({
                'auth_url': auth_url,
            })
            
        except GoogleMeetNotConfiguredError as e:
            logger.warning(f"Google Meet not configured: {e}")
            return Response(
                {'detail': 'Google Meet интеграция не настроена на сервере'},
                status=status.HTTP_501_NOT_IMPLEMENTED
            )
        except Exception as e:
            logger.exception(f"Error generating auth URL: {e}")
            return Response(
                {'detail': 'Ошибка при генерации ссылки авторизации'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GoogleMeetCallbackView(APIView):
    """
    GET /api/integrations/google-meet/callback/
    
    OAuth2 callback handler. Google redirects here after user consent.
    Exchanges authorization code for tokens and stores them.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Get query parameters
        code = request.GET.get('code')
        state = request.GET.get('state')
        error = request.GET.get('error')
        
        # Frontend URL to redirect to after completion
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        success_redirect = f"{frontend_url}/profile?tab=platforms&meet_connected=1"
        error_redirect = f"{frontend_url}/profile?tab=platforms&meet_error=1"
        
        # Handle error from Google
        if error:
            logger.warning(f"Google OAuth error: {error}")
            return HttpResponseRedirect(f"{error_redirect}&error={error}")
        
        # Validate code
        if not code:
            logger.warning("No authorization code in callback")
            return HttpResponseRedirect(f"{error_redirect}&error=no_code")
        
        # Validate state (CSRF protection)
        stored_state = request.session.get('google_meet_oauth_state')
        if state and stored_state and state != stored_state:
            logger.warning(f"State mismatch: expected {stored_state}, got {state}")
            return HttpResponseRedirect(f"{error_redirect}&error=state_mismatch")
        
        # Clear stored state
        if 'google_meet_oauth_state' in request.session:
            del request.session['google_meet_oauth_state']
            request.session.modified = True
        
        try:
            # Exchange code for tokens and connect
            result = connect_google_meet(request.user, code)
            
            logger.info(f"Google Meet connected for user {request.user.id}")
            return HttpResponseRedirect(success_redirect)
            
        except GoogleMeetError as e:
            logger.error(f"Google Meet connection error: {e}")
            return HttpResponseRedirect(f"{error_redirect}&error=connection_failed")
        except Exception as e:
            logger.exception(f"Unexpected error in Google Meet callback: {e}")
            return HttpResponseRedirect(f"{error_redirect}&error=unknown")


class GoogleMeetDisconnectView(APIView):
    """
    POST /api/integrations/google-meet/disconnect/
    
    Disconnects Google Meet from the user's account.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        if getattr(request.user, 'role', '') != 'teacher':
            return Response(
                {'detail': 'Только учителя могут управлять подключениями'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not request.user.google_meet_connected:
            return Response(
                {'detail': 'Google Meet не подключён'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            disconnect_google_meet(request.user)
            return Response({'detail': 'Google Meet успешно отключён'})
        except Exception as e:
            logger.exception(f"Error disconnecting Google Meet: {e}")
            return Response(
                {'detail': 'Ошибка при отключении Google Meet'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GoogleMeetStatusView(APIView):
    """
    GET /api/integrations/google-meet/status/
    
    Returns the current Google Meet connection status.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Check if feature is enabled and configured
        meet_enabled = getattr(settings, 'GOOGLE_MEET_ENABLED', False)
        meet_configured = bool(
            meet_enabled and
            getattr(settings, 'GOOGLE_MEET_CLIENT_ID', '') and
            getattr(settings, 'GOOGLE_MEET_CLIENT_SECRET', '')
        )
        
        return Response({
            'enabled': meet_enabled,
            'configured': meet_configured,  # True only if OAuth credentials are set
            'connected': user.is_google_meet_connected() if hasattr(user, 'is_google_meet_connected') else False,
            'email': getattr(user, 'google_meet_email', '') or '',
        })
