"""
Google Meet Integration Views

Handles OAuth2 callback and API endpoints for Google Meet integration.
"""

import logging
import secrets
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.http import HttpResponseRedirect
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
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


class GoogleMeetSaveCredentialsView(APIView):
    """
    POST /api/integrations/google-meet/save-credentials/
    
    Saves teacher's personal Google OAuth credentials (Client ID and Secret).
    After saving, returns the auth URL to start OAuth flow.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Only teachers can connect Google Meet
        if getattr(request.user, 'role', '') != 'teacher':
            return Response(
                {'detail': 'Только учителя могут подключить Google Meet'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        client_id = request.data.get('client_id', '').strip()
        client_secret = request.data.get('client_secret', '').strip()
        
        if not client_id or not client_secret:
            return Response(
                {'detail': 'Client ID и Client Secret обязательны'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate format (basic check)
        if not client_id.endswith('.apps.googleusercontent.com'):
            return Response(
                {'detail': 'Неверный формат Client ID. Должен заканчиваться на .apps.googleusercontent.com'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Save credentials to user
            request.user.google_meet_client_id = client_id
            request.user.google_meet_client_secret = client_secret
            request.user.save(update_fields=['google_meet_client_id', 'google_meet_client_secret'])
            
            # Generate auth URL with user's credentials
            service = GoogleMeetService(
                user=request.user,
                client_id=client_id,
                client_secret=client_secret
            )
            
            # Generate state token for CSRF protection
            state = secrets.token_urlsafe(32)
            
            # Store state in session for validation in callback
            request.session['google_meet_oauth_state'] = state
            request.session['google_meet_oauth_user_id'] = request.user.id
            request.session.modified = True
            
            auth_url = service.get_auth_url(state=state)
            
            logger.info(f"Saved Google Meet credentials for user {request.user.id}")
            
            return Response({
                'auth_url': auth_url,
                'message': 'Credentials сохранены. Перенаправляем на Google для авторизации.',
            })
            
        except Exception as e:
            logger.exception(f"Error saving credentials: {e}")
            return Response(
                {'detail': 'Ошибка сохранения credentials'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class GoogleMeetAuthURLView(APIView):
    """
    GET /api/integrations/google-meet/auth-url/
    
    Returns the OAuth authorization URL for Google Meet.
    User should be redirected to this URL to start the OAuth flow.
    Requires that credentials are already saved.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Only teachers can connect Google Meet
        if getattr(request.user, 'role', '') != 'teacher':
            return Response(
                {'detail': 'Только учителя могут подключить Google Meet'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if user has credentials
        if not request.user.google_meet_client_id or not request.user.google_meet_client_secret:
            return Response(
                {'detail': 'Сначала введите Client ID и Client Secret', 'need_credentials': True},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            service = GoogleMeetService(user=request.user)
            
            # Generate state token for CSRF protection
            state = secrets.token_urlsafe(32)
            
            # Store state in session for validation in callback
            request.session['google_meet_oauth_state'] = state
            request.session['google_meet_oauth_user_id'] = request.user.id
            request.session.modified = True
            
            auth_url = service.get_auth_url(state=state)
            
            return Response({
                'auth_url': auth_url,
            })
            
        except GoogleMeetNotConfiguredError as e:
            logger.warning(f"Google Meet not configured: {e}")
            return Response(
                {'detail': 'Введите Client ID и Client Secret для подключения Google Meet', 'need_credentials': True},
                status=status.HTTP_400_BAD_REQUEST
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
    # Google redirects the browser here without JWT headers.
    # We bind the callback to the user via server-side session.
    permission_classes = [AllowAny]
    
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
        if stored_state and state != stored_state:
            logger.warning(f"State mismatch: expected {stored_state}, got {state}")
            return HttpResponseRedirect(f"{error_redirect}&error=state_mismatch")

        user_id = request.session.get('google_meet_oauth_user_id')
        if not user_id:
            logger.warning("No user id in session for Google Meet callback")
            return HttpResponseRedirect(f"{error_redirect}&error=no_session")

        User = get_user_model()
        user = User.objects.filter(id=user_id).first()
        if not user:
            logger.warning(f"User not found for Google Meet callback: {user_id}")
            return HttpResponseRedirect(f"{error_redirect}&error=user_not_found")
        
        # Clear stored state
        for key in ('google_meet_oauth_state', 'google_meet_oauth_user_id'):
            if key in request.session:
                del request.session[key]
                request.session.modified = True
        
        try:
            # Exchange code for tokens and connect
            connect_google_meet(user, code)
            
            logger.info(f"Google Meet connected for user {user.id}")
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
