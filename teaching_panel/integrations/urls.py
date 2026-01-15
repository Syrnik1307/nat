"""
Integrations URL Configuration

URL patterns for third-party integrations (Zoom, Google Meet, etc.)
"""

from django.urls import path
from .google_meet_views import (
    GoogleMeetAuthURLView,
    GoogleMeetCallbackView,
    GoogleMeetDisconnectView,
    GoogleMeetStatusView,
)
from .zoom_views import (
    ZoomAuthURLView,
    ZoomCallbackView,
    ZoomDisconnectView,
    ZoomStatusView,
    PlatformsAvailabilityView,
)

app_name = 'integrations'

urlpatterns = [
    # Общий статус платформ
    path('platforms/', PlatformsAvailabilityView.as_view(), name='platforms-availability'),
    
    # Zoom OAuth
    path('zoom/auth-url/', ZoomAuthURLView.as_view(), name='zoom-auth-url'),
    path('zoom/callback/', ZoomCallbackView.as_view(), name='zoom-callback'),
    path('zoom/disconnect/', ZoomDisconnectView.as_view(), name='zoom-disconnect'),
    path('zoom/status/', ZoomStatusView.as_view(), name='zoom-status'),
    
    # Google Meet OAuth
    path('google-meet/auth-url/', GoogleMeetAuthURLView.as_view(), name='google-meet-auth-url'),
    path('google-meet/callback/', GoogleMeetCallbackView.as_view(), name='google-meet-callback'),
    path('google-meet/disconnect/', GoogleMeetDisconnectView.as_view(), name='google-meet-disconnect'),
    path('google-meet/status/', GoogleMeetStatusView.as_view(), name='google-meet-status'),
]
