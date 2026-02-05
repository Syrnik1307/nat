"""
URL маршруты для Lectio Concierge API
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ConversationViewSet,
    available_actions,
    execute_action,
    message_stream,
    telegram_webhook,
    reindex_knowledge_base,
)

router = DefaultRouter()
router.register('conversations', ConversationViewSet, basename='conversation')

urlpatterns = [
    # REST API
    path('', include(router.urls)),
    
    # Actions
    path('conversations/<int:conversation_id>/actions/', available_actions, name='available-actions'),
    path('conversations/<int:conversation_id>/actions/<str:action_name>/execute/', execute_action, name='execute-action'),
    
    # Real-time (SSE)
    path('conversations/<int:conversation_id>/stream/', message_stream, name='message-stream'),
    
    # Telegram webhook
    path('telegram/webhook/', telegram_webhook, name='telegram-webhook'),
    
    # Admin
    path('knowledge/reindex/', reindex_knowledge_base, name='reindex-knowledge'),
]
