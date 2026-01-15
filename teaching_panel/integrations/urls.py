"""
Integrations URL Configuration

URL patterns for third-party integrations (Google Meet, etc.)
"""

from django.urls import path
from .google_meet_views import (
    GoogleMeetAuthURLView,
    GoogleMeetCallbackView,
    GoogleMeetDisconnectView,
    GoogleMeetStatusView,
)

app_name = 'integrations'

urlpatterns = [
    # Google Meet OAuth
    path('google-meet/auth-url/', GoogleMeetAuthURLView.as_view(), name='google-meet-auth-url'),
    path('google-meet/callback/', GoogleMeetCallbackView.as_view(), name='google-meet-callback'),
    path('google-meet/disconnect/', GoogleMeetDisconnectView.as_view(), name='google-meet-disconnect'),
    path('google-meet/status/', GoogleMeetStatusView.as_view(), name='google-meet-status'),
]
