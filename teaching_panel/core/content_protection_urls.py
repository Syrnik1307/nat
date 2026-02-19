from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .content_protection_views import (
    ContentPlaybackRedirectView,
    ContentSessionEndView,
    ContentSessionEventView,
    ContentSessionHeartbeatView,
    ContentProtectionIncidentsView,
    ContentSessionPlaybackUrlView,
    ContentSessionStartView,
    ContentSessionStatusView,
    ProtectedContentViewSet,
)

router = DefaultRouter()
router.register(r'contents', ProtectedContentViewSet, basename='protected-content')

urlpatterns = [
    path('', include(router.urls)),
    path('sessions/start/', ContentSessionStartView.as_view(), name='content-session-start'),
    path('sessions/heartbeat/', ContentSessionHeartbeatView.as_view(), name='content-session-heartbeat'),
    path('sessions/event/', ContentSessionEventView.as_view(), name='content-session-event'),
    path('sessions/playback-url/', ContentSessionPlaybackUrlView.as_view(), name='content-session-playback-url'),
    path('incidents/', ContentProtectionIncidentsView.as_view(), name='content-protection-incidents'),
    path('sessions/<uuid:session_token>/status/', ContentSessionStatusView.as_view(), name='content-session-status'),
    path('sessions/<uuid:session_token>/end/', ContentSessionEndView.as_view(), name='content-session-end'),
    path('playback/<path:signed_token>/', ContentPlaybackRedirectView.as_view(), name='content-playback-redirect'),
]
