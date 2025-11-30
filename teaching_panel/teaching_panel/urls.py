"""
URL configuration for teaching_panel project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
print("[URLDebug] teaching_panel.urls loaded (token-ci + direct endpoints present)")
from django.urls import path, include
from django.http import JsonResponse
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter
from core import views as core_views
from schedule import views as schedule_views
from homework.views import HomeworkViewSet, StudentSubmissionViewSet
from analytics.views import GradebookViewSet
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from accounts.jwt_views import LogoutView, RegisterView, CaseInsensitiveTokenObtainPairView, DirectTokenView
from accounts.api_views import MeView
from accounts.subscriptions_views import (
    SubscriptionMeView,
    SubscriptionCancelView,
    SubscriptionCreatePaymentView,
    SubscriptionAddStorageView,
    AdminSubscriptionsListView,
    AdminSubscriptionExtendTrialView,
    AdminSubscriptionCancelView,
    AdminSubscriptionActivateView,
    AdminSubscriptionConfirmStoragePaymentView,
)
from accounts.payments_views import yookassa_webhook

# Create a router and register our viewsets with it.
router = DefaultRouter()
# Core app routes (активные)
router.register(r'courses', core_views.CourseViewSet)

# Schedule app routes (новые)
router.register(r'groups', schedule_views.GroupViewSet)
router.register(r'schedule/lessons', schedule_views.LessonViewSet, basename='schedule-lesson')
router.register(r'attendance', schedule_views.AttendanceViewSet)
router.register(r'recurring-lessons', schedule_views.RecurringLessonViewSet, basename='recurring-lessons')
router.register(r'homework', HomeworkViewSet, basename='homework')
router.register(r'submissions', StudentSubmissionViewSet, basename='homework-submission')

def health(request):
    return JsonResponse({
        'status': 'ok',
        'service': 'teaching_panel_backend',
        'message': 'Backend running. React frontend is on port 3000.',
    })

urlpatterns = [
    path('', health, name='root'),
    path('admin/', admin.site.urls),  # Django admin для управления БД
    
    # Test page for email verification
    path('test-verification/', TemplateView.as_view(template_name='test_verification.html'), name='test-verification'),
    
    # Accounts (authentication)
    path('accounts/', include('accounts.urls')),
    
    # Schedule (web UI + API)
    path('schedule/', include('schedule.urls')),
    
    # Zoom Pool API
    path('api/zoom-pool/', include('zoom_pool.urls')),
    
    # Support API
    path('api/support/', include('support.urls')),
    
    # Analytics API
    path('api/', include('analytics.urls')),
    
    # API (DRF router)
    path('api/', include(router.urls)),
    path('api/gradebook/', GradebookViewSet.as_view({'get': 'group'}), name='gradebook-group'),
    path('api/me/', MeView.as_view(), name='api-me'),
    path('api/jwt/token/', CaseInsensitiveTokenObtainPairView.as_view(), name='jwt-obtain-pair'),
    # Temporary CI endpoint to bypass potential routing conflicts
    path('api/jwt/token-ci/', CaseInsensitiveTokenObtainPairView.as_view(), name='jwt-obtain-pair-ci'),
    # Direct diagnostic endpoint (manual password check)
    path('api/jwt/token-direct/', DirectTokenView.as_view(), name='jwt-obtain-direct'),
    path('api/jwt/refresh/', TokenRefreshView.as_view(), name='jwt-refresh'),
    path('api/jwt/verify/', TokenVerifyView.as_view(), name='jwt-verify'),
    path('api/jwt/logout/', LogoutView.as_view(), name='jwt-logout'),
    path('api/jwt/register/', RegisterView.as_view(), name='jwt-register'),
    
    # Subscription API
    path('api/subscription/', SubscriptionMeView.as_view(), name='subscription_me'),
    path('api/subscription/cancel/', SubscriptionCancelView.as_view(), name='subscription_cancel'),
    path('api/subscription/enable-auto-renew/', SubscriptionEnableAutoRenewView.as_view(), name='subscription_enable_auto_renew'),
    path('api/subscription/create-payment/', SubscriptionCreatePaymentView.as_view(), name='subscription_create_payment'),
    path('api/subscription/add-storage/', SubscriptionAddStorageView.as_view(), name='subscription_add_storage'),

    # Admin Subscriptions API
    path('api/admin/subscriptions/', AdminSubscriptionsListView.as_view(), name='admin_subscriptions_list'),
    path('api/admin/subscriptions/<int:sub_id>/extend-trial/', AdminSubscriptionExtendTrialView.as_view(), name='admin_subscription_extend_trial'),
    path('api/admin/subscriptions/<int:sub_id>/cancel/', AdminSubscriptionCancelView.as_view(), name='admin_subscription_cancel'),
    path('api/admin/subscriptions/<int:sub_id>/activate/', AdminSubscriptionActivateView.as_view(), name='admin_subscription_activate'),
    path('api/admin/subscriptions/storage/confirm/<str:payment_id>/', AdminSubscriptionConfirmStoragePaymentView.as_view(), name='admin_subscription_confirm_storage'),
    
    # Payment webhooks
    path('api/payments/yookassa/webhook/', yookassa_webhook, name='yookassa_webhook'),
]
