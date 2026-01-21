"""
Google Meet Integration Service

Handles OAuth2 flow and meeting creation via Google Calendar API.
Meetings created with Google Meet conferencing attached.

Required Google Cloud Console setup:
1. Enable Google Calendar API
2. Create OAuth 2.0 Client ID (Web application)
3. Add redirect URI: {BACKEND_URL}/api/integrations/google-meet/callback/
4. Required scopes:
   - https://www.googleapis.com/auth/calendar.events
   - https://www.googleapis.com/auth/userinfo.email
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from urllib.parse import urlencode

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class GoogleMeetError(Exception):
    """Base exception for Google Meet integration errors"""
    pass


class GoogleMeetNotConfiguredError(GoogleMeetError):
    """Raised when Google Meet integration is not configured"""
    pass


class GoogleMeetAuthError(GoogleMeetError):
    """Raised when OAuth authentication fails"""
    pass


class GoogleMeetService:
    """
    Service for Google Meet integration via Google Calendar API.
    
    OAuth2 flow:
    1. get_auth_url() -> redirect user to Google consent screen
    2. handle_callback(code) -> exchange code for tokens, store in user profile
    3. create_meeting() -> create calendar event with Meet conferencing
    """
    
    SCOPES = [
        'https://www.googleapis.com/auth/calendar.events',
        'https://www.googleapis.com/auth/userinfo.email',
        'openid',
    ]
    
    GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
    GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
    GOOGLE_USERINFO_URL = 'https://www.googleapis.com/oauth2/v2/userinfo'
    GOOGLE_CALENDAR_API = 'https://www.googleapis.com/calendar/v3'
    
    def __init__(self, user=None, client_id: str = None, client_secret: str = None):
        """
        Initialize service with user's personal credentials.
        
        Args:
            user: Django user model instance (for token-based operations)
            client_id: Optional override for client_id (used during initial setup)
            client_secret: Optional override for client_secret (used during initial setup)
        """
        self.user = user
        self._client_id = client_id
        self._client_secret = client_secret
        self._validate_config()
    
    def _validate_config(self):
        """Check that Google Meet credentials are available"""
        # If explicit credentials provided, use them
        if self._client_id and self._client_secret:
            return
        
        # If user has personal credentials, use them
        if self.user:
            if self.user.google_meet_client_id and self.user.google_meet_client_secret:
                return
        
        # No credentials available
        raise GoogleMeetNotConfiguredError(
            'Google Meet credentials not configured. Teacher needs to add Client ID and Client Secret.'
        )
    
    @property
    def client_id(self) -> str:
        if self._client_id:
            return self._client_id
        if self.user and self.user.google_meet_client_id:
            return self.user.google_meet_client_id
        return ''
    
    @property
    def client_secret(self) -> str:
        if self._client_secret:
            return self._client_secret
        if self.user and self.user.google_meet_client_secret:
            return self.user.google_meet_client_secret
        return ''
    
    @property
    def redirect_uri(self) -> str:
        uri = getattr(
            settings,
            'GOOGLE_MEET_REDIRECT_URI',
            'https://lectio.tw1.ru/api/integrations/google-meet/callback/',
        )

        # Safety net for production misconfiguration.
        # If prod accidentally has localhost redirect URI, Google OAuth will fail with redirect_uri_mismatch.
        if not getattr(settings, 'DEBUG', False):
            bad_prefixes = ('http://localhost', 'http://127.0.0.1', 'http://0.0.0.0')
            if isinstance(uri, str) and uri.startswith(bad_prefixes):
                return 'https://lectio.tw1.ru/api/integrations/google-meet/callback/'

        return uri
    
    def get_auth_url(self, state: Optional[str] = None) -> str:
        """
        Generate Google OAuth2 authorization URL.
        
        Args:
            state: Optional state parameter for CSRF protection
            
        Returns:
            Authorization URL to redirect user to
        """
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(self.SCOPES),
            'access_type': 'offline',  # Required for refresh token
            'prompt': 'consent',  # Force consent to get refresh token
        }
        
        if state:
            params['state'] = state
        
        return f"{self.GOOGLE_AUTH_URL}?{urlencode(params)}"
    
    def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access and refresh tokens.
        
        Args:
            code: Authorization code from OAuth callback
            
        Returns:
            Dict with access_token, refresh_token, expires_in, etc.
        """
        import requests
        
        response = requests.post(self.GOOGLE_TOKEN_URL, data={
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': self.redirect_uri,
        }, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"Token exchange failed: {response.text}")
            raise GoogleMeetAuthError(f"Failed to exchange code: {response.text}")
        
        return response.json()
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh expired access token using refresh token.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            Dict with new access_token, expires_in, etc.
        """
        import requests
        
        response = requests.post(self.GOOGLE_TOKEN_URL, data={
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token',
        }, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"Token refresh failed: {response.text}")
            raise GoogleMeetAuthError(f"Failed to refresh token: {response.text}")
        
        return response.json()
    
    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Get user info (email) from Google.
        
        Args:
            access_token: Valid access token
            
        Returns:
            Dict with email, name, etc.
        """
        import requests
        
        response = requests.get(
            self.GOOGLE_USERINFO_URL,
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=30
        )
        
        if response.status_code != 200:
            logger.error(f"User info request failed: {response.text}")
            raise GoogleMeetAuthError(f"Failed to get user info: {response.text}")
        
        return response.json()
    
    def _get_valid_access_token(self) -> str:
        """
        Get valid access token for the user, refreshing if needed.
        
        Returns:
            Valid access token string
        """
        if not self.user:
            raise GoogleMeetAuthError("No user provided for authenticated operation")
        
        if not self.user.google_meet_refresh_token:
            raise GoogleMeetAuthError("User has not connected Google Meet")
        
        # Check if token is expired
        now = timezone.now()
        if (self.user.google_meet_token_expires_at and 
            self.user.google_meet_token_expires_at > now + timedelta(minutes=5)):
            # Token is still valid
            return self.user.google_meet_access_token
        
        # Refresh the token
        logger.info(f"Refreshing Google Meet token for user {self.user.id}")
        token_data = self.refresh_access_token(self.user.google_meet_refresh_token)
        
        # Update user tokens
        self.user.google_meet_access_token = token_data['access_token']
        self.user.google_meet_token_expires_at = now + timedelta(
            seconds=token_data.get('expires_in', 3600)
        )
        self.user.save(update_fields=[
            'google_meet_access_token',
            'google_meet_token_expires_at'
        ])
        
        return token_data['access_token']
    
    def create_meeting(
        self,
        title: str,
        start_time: datetime,
        duration_minutes: int = 60,
        description: str = '',
    ) -> Dict[str, Any]:
        """
        Create a Google Calendar event with Meet conferencing.
        
        Args:
            title: Meeting title
            start_time: Meeting start time (timezone-aware)
            duration_minutes: Duration in minutes (default 60)
            description: Optional meeting description
            
        Returns:
            Dict with:
                - meet_link: Google Meet join URL
                - event_id: Calendar event ID
                - start_time: Event start time (ISO format)
                - end_time: Event end time (ISO format)
        """
        import requests
        
        access_token = self._get_valid_access_token()
        
        # Prepare event times
        if timezone.is_naive(start_time):
            start_time = timezone.make_aware(start_time)
        
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        # Create calendar event with Meet conferencing
        event_body = {
            'summary': title,
            'description': description,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': str(timezone.get_current_timezone()),
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': str(timezone.get_current_timezone()),
            },
            'conferenceData': {
                'createRequest': {
                    'requestId': f"lesson-{self.user.id}-{start_time.timestamp()}",
                    'conferenceSolutionKey': {
                        'type': 'hangoutsMeet'
                    }
                }
            },
        }
        
        # Create event with conference data
        response = requests.post(
            f"{self.GOOGLE_CALENDAR_API}/calendars/primary/events",
            params={'conferenceDataVersion': 1},
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
            },
            json=event_body,
            timeout=30
        )
        
        if response.status_code not in (200, 201):
            # Log raw response for diagnostics, but return a clean error to UI.
            logger.error(
                "Meeting creation failed: status=%s body=%s",
                response.status_code,
                response.text,
            )

            body_text = response.text or ''
            try:
                body_json = response.json()
            except Exception:
                body_json = None

            # Common Google API errors
            if response.status_code in (401,):
                raise GoogleMeetAuthError(
                    'Авторизация Google истекла. Переподключите Google Meet в профиле.'
                )

            if response.status_code in (403,):
                # Insufficient scopes / permissions.
                if (
                    'ACCESS_TOKEN_SCOPE_INSUFFICIENT' in body_text
                    or 'insufficient authentication scopes' in body_text
                    or 'insufficientPermissions' in body_text
                ):
                    raise GoogleMeetAuthError(
                        'Недостаточно прав Google OAuth для создания встречи. '
                        'Переподключите Google Meet в профиле и согласитесь на доступ к Google Calendar.'
                    )

                # Calendar API not enabled for the project.
                if 'accessNotConfigured' in body_text:
                    raise GoogleMeetAuthError(
                        'Google Calendar API не включён в вашем Google Cloud проекте. '
                        'Включите Calendar API и переподключите Google Meet.'
                    )

            # Fallback: try to surface a short message from JSON
            short_message = None
            if isinstance(body_json, dict):
                short_message = (
                    body_json.get('error', {})
                    .get('message')
                    if isinstance(body_json.get('error'), dict)
                    else None
                )

            raise GoogleMeetError(
                f"Ошибка Google Calendar API: {short_message or 'не удалось создать встречу'}"
            )
        
        event_data = response.json()
        
        # Extract Meet link
        conference_data = event_data.get('conferenceData', {})
        entry_points = conference_data.get('entryPoints', [])
        
        meet_link = None
        for ep in entry_points:
            if ep.get('entryPointType') == 'video':
                meet_link = ep.get('uri')
                break
        
        if not meet_link:
            logger.warning(f"No Meet link in event response: {event_data}")
            # Sometimes Meet link takes a moment to generate
            meet_link = event_data.get('hangoutLink', '')
        
        return {
            'meet_link': meet_link,
            'event_id': event_data.get('id'),
            'start_time': event_data.get('start', {}).get('dateTime'),
            'end_time': event_data.get('end', {}).get('dateTime'),
            'html_link': event_data.get('htmlLink'),
        }
    
    def delete_meeting(self, event_id: str) -> bool:
        """
        Delete a calendar event (and its Meet link).
        
        Args:
            event_id: Google Calendar event ID
            
        Returns:
            True if deleted successfully
        """
        import requests
        
        access_token = self._get_valid_access_token()
        
        response = requests.delete(
            f"{self.GOOGLE_CALENDAR_API}/calendars/primary/events/{event_id}",
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=30
        )
        
        if response.status_code == 204:
            return True
        elif response.status_code == 404:
            logger.warning(f"Event {event_id} not found for deletion")
            return True  # Already deleted
        else:
            logger.error(f"Event deletion failed: {response.text}")
            return False


def connect_google_meet(user, code: str) -> Dict[str, Any]:
    """
    Complete OAuth flow and connect Google Meet for a user.
    Uses user's personal Google OAuth credentials.
    
    Args:
        user: Django user model instance
        code: Authorization code from OAuth callback
        
    Returns:
        Dict with connected email
    """
    # Use user's personal credentials
    service = GoogleMeetService(user=user)
    
    # Exchange code for tokens
    token_data = service.exchange_code_for_tokens(code)
    
    # Get user email
    user_info = service.get_user_info(token_data['access_token'])
    
    # Store tokens in user profile
    user.google_meet_connected = True
    user.google_meet_access_token = token_data['access_token']
    user.google_meet_refresh_token = token_data.get('refresh_token', '')
    user.google_meet_token_expires_at = timezone.now() + timedelta(
        seconds=token_data.get('expires_in', 3600)
    )
    user.google_meet_email = user_info.get('email', '')
    user.save(update_fields=[
        'google_meet_connected',
        'google_meet_access_token',
        'google_meet_refresh_token',
        'google_meet_token_expires_at',
        'google_meet_email',
    ])
    
    logger.info(f"Connected Google Meet for user {user.id}: {user.google_meet_email}")
    
    return {
        'email': user.google_meet_email,
        'connected': True,
    }


def disconnect_google_meet(user) -> bool:
    """
    Disconnect Google Meet from user account.
    
    Args:
        user: Django user model instance
        
    Returns:
        True if disconnected successfully
    """
    user.google_meet_connected = False
    user.google_meet_access_token = ''
    user.google_meet_refresh_token = ''
    user.google_meet_token_expires_at = None
    user.google_meet_email = ''
    user.save(update_fields=[
        'google_meet_connected',
        'google_meet_access_token',
        'google_meet_refresh_token',
        'google_meet_token_expires_at',
        'google_meet_email',
    ])
    
    logger.info(f"Disconnected Google Meet for user {user.id}")
    return True
