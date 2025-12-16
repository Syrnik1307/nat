from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'tickets', views.SupportTicketViewSet, basename='support-ticket')

urlpatterns = [
    path('', include(router.urls)),
    path('quick-responses/', views.get_quick_responses, name='quick-responses'),
    path('unread-count/', views.get_unread_count, name='unread-count'),
    path('telegram-link/', views.get_telegram_support_link, name='telegram-support-link'),
]
