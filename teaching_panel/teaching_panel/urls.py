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
from django.urls import path, include
from django.http import JsonResponse
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter
from core import views as core_views
from schedule import views as schedule_views
from homework.views import HomeworkViewSet, StudentSubmissionViewSet, HomeworkFileProxyView
from analytics.views import GradebookViewSet
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from accounts.jwt_views import LogoutView, RegisterView, CaseInsensitiveTokenObtainPairView, DirectTokenView
from accounts.api_views import MeView
from accounts.attendance_views import (
    AttendanceRecordViewSet,
    UserRatingViewSet,
    IndividualStudentViewSet,
    GroupAttendanceLogViewSet,
    GroupRatingViewSet,
    GroupReportViewSet,
    StudentCardViewSet,
    AttendanceAlertsViewSet,
)
from accounts.subscriptions_views import (
    SubscriptionMeView,
    SubscriptionCancelView,
    SubscriptionCreatePaymentView,
    SubscriptionAddStorageView,
    SubscriptionCreateZoomAddonPaymentView,
    SubscriptionZoomAddonSetupView,
    SubscriptionStorageView,
    AdminSubscriptionsListView,
    AdminSubscriptionExtendTrialView,
    AdminSubscriptionCancelView,
    AdminSubscriptionActivateView,
    AdminSubscriptionConfirmStoragePaymentView,
    SubscriptionEnableAutoRenewView,
    SubscriptionPaymentStatusView,
    SyncPendingPaymentsView,
)
from accounts.payments_views import yookassa_webhook, tbank_webhook
from schedule.views import zoom_webhook_receiver
from accounts.debug_views import debug_env  # Debug endpoint
from django.conf import settings
from django.conf.urls.static import static
from accounts.referrals_views import MyReferralLinkView, MyReferralStatsView
from accounts.referrals_admin_views import (
    AdminReferralLinksListView,
    AdminReferralLinkDetailView,
    AdminReferralPayoutView,
    AdminReferralCommissionsView,
    AdminReferralStatsView,
    ReferralClickTrackView,
)

# Create a router and register our viewsets with it.
router = DefaultRouter()
# Core app routes (активные)
router.register(r'courses', core_views.CourseViewSet)

# Schedule app routes (новые)
router.register(r'groups', schedule_views.GroupViewSet)
router.register(r'schedule/lessons', schedule_views.LessonViewSet, basename='schedule-lesson')
router.register(r'attendance', schedule_views.AttendanceViewSet)
router.register(r'recurring-lessons', schedule_views.RecurringLessonViewSet, basename='recurring-lessons')
router.register(r'individual-invite-codes', schedule_views.IndividualInviteCodeViewSet, basename='individual-invite-code')
router.register(r'homework', HomeworkViewSet, basename='homework')
router.register(r'submissions', StudentSubmissionViewSet, basename='homework-submission')

# Attendance & Rating routes (новые для системы посещений)
router.register(r'attendance-records', AttendanceRecordViewSet, basename='attendance-record')
router.register(r'ratings', UserRatingViewSet, basename='user-rating')
router.register(r'individual-students', IndividualStudentViewSet, basename='individual-student')

def health(request):
    return JsonResponse({
        'status': 'ok',
        'service': 'teaching_panel_backend',
        'message': 'Backend running. React frontend is on port 3000.',
    })

def health_check(request):
    """Deep healthcheck with DB validation for monitoring."""
    import time
    from django.db import connection
    
    start = time.time()
    checks = {'database': False, 'response_time_ms': 0}
    status = 'ok'
    http_status = 200
    
    # Check database connection
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            checks['database'] = True
    except Exception as e:
        checks['database'] = False
        checks['database_error'] = str(e)
        status = 'unhealthy'
        http_status = 503
    
    checks['response_time_ms'] = round((time.time() - start) * 1000, 2)
    
    return JsonResponse({
        'status': status,
        'service': 'teaching_panel',
        'checks': checks,
    }, status=http_status)

# Prometheus metrics endpoint
from .prometheus_metrics import metrics_view

urlpatterns = [
    path('', health, name='root'),
    path('api/health/', health_check, name='health-check'),
    path('metrics/', metrics_view, name='prometheus-metrics'),
    path('admin/', admin.site.urls),  # Django admin для управления БД
    
    # Debug endpoint (remove in production)
    path('api/debug/env/', debug_env, name='debug-env'),
    
    # Test page for email verification
    path('test-verification/', TemplateView.as_view(template_name='test_verification.html'), name='test-verification'),
    
    # Accounts (authentication)
    path('accounts/', include('accounts.urls')),
    path('', include(('accounts.urls', 'accounts'), namespace='accounts-root')),  # Include accounts at root for /api/* paths
    
    # Schedule (web UI + API)
    path('schedule/', include('schedule.urls')),

    # Recording video stream alias (served behind /api/* nginx proxy)
    path('api/schedule/recordings/<int:recording_id>/stream/', schedule_views.stream_recording, name='stream_recording_api_alias'),
    
    # Zoom Pool API
    path('api/zoom-pool/', include('zoom_pool.urls')),
    
    # Homework file proxy (быстрый доступ к файлам)
    path('api/homework/file/<str:file_id>/', HomeworkFileProxyView.as_view(), name='homework-file-proxy'),
    
    # Integrations API (Google Meet, etc.)
    path('api/integrations/', include('integrations.urls')),
    
    # Support API
    path('api/support/', include('support.urls')),
    
    # Market API (digital products: Zoom accounts, etc.)
    path('api/market/', include('market.urls')),
    
    # Finance API (student lesson balances)
    path('api/finance/', include('finance.urls')),
    
    # Analytics API
    path('api/', include('analytics.urls')),
    
    # API (DRF router)
    path('api/', include(router.urls)),
    
    # Nested Group endpoints для системы посещаемости
    path('api/groups/<int:group_id>/attendance-log/', 
         GroupAttendanceLogViewSet.as_view({'get': 'list'}), 
         name='group-attendance-log'),
    path('api/groups/<int:group_id>/attendance-log/update/', 
         GroupAttendanceLogViewSet.as_view({'post': 'update'}), 
         name='group-attendance-log-update'),
    path('api/groups/<int:group_id>/rating/', 
         GroupRatingViewSet.as_view({'get': 'list'}), 
         name='group-rating'),
        path('api/groups/<int:group_id>/report/', 
            GroupReportViewSet.as_view({'get': 'list'}), 
            name='group-report'),
        
        # Attendance alerts
        path('api/attendance-alerts/',
            AttendanceAlertsViewSet.as_view({'get': 'list'}),
            name='attendance-alerts'),
        path('api/attendance-alerts/mark-read/',
            AttendanceAlertsViewSet.as_view({'post': 'mark_read'}),
            name='attendance-alerts-mark-read'),
        path('api/groups/<int:group_id>/attendance-alerts/',
            AttendanceAlertsViewSet.as_view({'get': 'list'}),
            name='group-attendance-alerts'),

        # Student card endpoints
        path('api/students/<int:pk>/card/', 
            StudentCardViewSet.as_view({'get': 'retrieve'}), 
            name='student-card'),
        path('api/students/<int:pk>/individual-card/', 
            StudentCardViewSet.as_view({'get': 'individual_card'}), 
            name='student-individual-card'),
        path('api/students/individual/', 
            StudentCardViewSet.as_view({'get': 'individual'}), 
            name='students-individual-list'),
    
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

    # Referral API
    path('api/referrals/link/', MyReferralLinkView.as_view(), name='referral-link'),
    path('api/referrals/stats/', MyReferralStatsView.as_view(), name='referral-stats'),
    path('api/referrals/track/', ReferralClickTrackView.as_view(), name='referral-track'),
    
    # Admin Referrals API
    path('api/admin/referrals/', AdminReferralLinksListView.as_view(), name='admin-referral-links'),
    path('api/admin/referrals/<int:link_id>/', AdminReferralLinkDetailView.as_view(), name='admin-referral-link-detail'),
    path('api/admin/referrals/<int:link_id>/payout/', AdminReferralPayoutView.as_view(), name='admin-referral-payout'),
    path('api/admin/referrals/commissions/', AdminReferralCommissionsView.as_view(), name='admin-referral-commissions'),
    path('api/admin/referrals/stats/', AdminReferralStatsView.as_view(), name='admin-referral-stats'),
    
    # Subscription API
    path('api/subscription/', SubscriptionMeView.as_view(), name='subscription_me'),
    path('api/subscription/storage/', SubscriptionStorageView.as_view(), name='subscription_storage'),
    path('api/subscription/cancel/', SubscriptionCancelView.as_view(), name='subscription_cancel'),
    path('api/subscription/enable-auto-renew/', SubscriptionEnableAutoRenewView.as_view(), name='subscription_enable_auto_renew'),
    path('api/subscription/payment-status/<str:payment_id>/', SubscriptionPaymentStatusView.as_view(), name='subscription_payment_status'),
    path('api/subscription/create-payment/', SubscriptionCreatePaymentView.as_view(), name='subscription_create_payment'),
    path('api/subscription/add-storage/', SubscriptionAddStorageView.as_view(), name='subscription_add_storage'),
    path('api/subscription/zoom/create-payment/', SubscriptionCreateZoomAddonPaymentView.as_view(), name='subscription_zoom_create_payment'),
    path('api/subscription/zoom/setup/', SubscriptionZoomAddonSetupView.as_view(), name='subscription_zoom_setup'),
    path('api/subscription/sync-payments/', SyncPendingPaymentsView.as_view(), name='subscription_sync_payments'),

    # Admin Subscriptions API
    path('api/admin/subscriptions/', AdminSubscriptionsListView.as_view(), name='admin_subscriptions_list'),
    path('api/admin/subscriptions/<int:sub_id>/extend-trial/', AdminSubscriptionExtendTrialView.as_view(), name='admin_subscription_extend_trial'),
    path('api/admin/subscriptions/<int:sub_id>/cancel/', AdminSubscriptionCancelView.as_view(), name='admin_subscription_cancel'),
    path('api/admin/subscriptions/<int:sub_id>/activate/', AdminSubscriptionActivateView.as_view(), name='admin_subscription_activate'),
    path('api/admin/subscriptions/storage/confirm/<str:payment_id>/', AdminSubscriptionConfirmStoragePaymentView.as_view(), name='admin_subscription_confirm_storage'),
    
    # Payment webhooks
    path('api/payments/yookassa/webhook/', yookassa_webhook, name='yookassa_webhook'),
    path('api/payments/tbank/webhook/', tbank_webhook, name='tbank_webhook'),
    # Zoom webhooks
    path('schedule/webhook/zoom/', zoom_webhook_receiver, name='zoom_webhook'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
