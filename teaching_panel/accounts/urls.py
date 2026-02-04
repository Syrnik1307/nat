from django.urls import path, include
from django.contrib.auth import views as auth_views
from rest_framework.routers import DefaultRouter
from . import views
from .admin_views import (
    AdminStatsView, 
    AdminGrowthOverviewView,
    AdminCreateTeacherView,
    AdminCreateStudentView,
    AdminTeachersListView,
    AdminTeacherDetailView,
    AdminTeacherSubscriptionView,
    AdminTeacherStorageView,
    AdminUpdateTeacherZoomView,
    AdminDeleteTeacherView,
    AdminTeachersBulkActionView,
    AdminChangeTeacherPasswordView,
    AdminStudentsListView,
    AdminUpdateStudentView,
    AdminDeleteStudentView,
    AdminChangeStudentPasswordView,
    AdminStatusMessagesView,
    SystemSettingsView,
    AdminAlertsView,
    AdminChurnRetentionView,
    AdminCohortRetentionView,
    AdminTeachersActivityView,
    AdminSystemHealthView,
    AdminActivityLogView,
    AdminQuickActionsView,
    AdminBusinessMetricsView,
    AdminSystemErrorsView,
    AdminSystemErrorsCountsView,
    AdminDashboardDataView,
    AdminTeacherAnalyticsView,
)
from .chat_views import ChatViewSet, MessageViewSet, UserSearchViewSet
from .email_views import (
    send_verification_email,
    resend_verification_email,
    verify_email_code,
    verify_email_token,
    check_verification_status
)
from .password_reset_views import (
    password_reset_request,
    password_reset_confirm,
    password_reset_validate_token,
    request_reset_code,
    verify_code,
    set_new_password
)
from .api_views import (
    MeView, 
    users_list, 
    change_password,
    change_email,
    link_telegram,
    unlink_telegram,
    request_password_reset,
    reset_password_with_token,
    check_telegram_status,
    generate_telegram_code,
    verify_telegram,
    notification_settings_view,
    notification_mutes_view,
    notification_mute_delete_view,
)
from .simple_reset_views import simple_password_reset


app_name = 'accounts'

# Router для API чатов
router = DefaultRouter()
router.register(r'chats', ChatViewSet, basename='chat')
router.register(r'messages', MessageViewSet, basename='message')
router.register(r'users/search', UserSearchViewSet, basename='user-search')

urlpatterns = [
    # Основной flow аутентификации
    path('role/', views.role_selection_view, name='role_selection'),
    path('auth/', views.login_register_view, name='login_register'),
    
    # Профиль
    path('profile/', views.profile_view, name='profile'),
    
    # Logout
    path('logout/', auth_views.LogoutView.as_view(next_page='accounts:role_selection'), name='logout'),
    
    # OAuth заглушки (для будущей интеграции)
    path('oauth/vk/', views.oauth_vk_login, name='oauth_vk'),
    path('oauth/yandex/', views.oauth_yandex_login, name='oauth_yandex'),
    path('oauth/university/', views.oauth_university_login, name='oauth_university'),
    # API registration endpoint
    path('jwt/register/', views.register_user, name='register'),
    
    # Admin API endpoints
    path('api/admin/stats/', AdminStatsView.as_view(), name='admin_stats'),
    path('api/admin/growth/overview/', AdminGrowthOverviewView.as_view(), name='admin_growth_overview'),
    path('api/admin/create-teacher/', AdminCreateTeacherView.as_view(), name='admin_create_teacher'),
    path('api/admin/create-student/', AdminCreateStudentView.as_view(), name='admin_create_student'),
    path('api/admin/teachers/', AdminTeachersListView.as_view(), name='admin_teachers_list'),
    path('api/admin/teachers/<int:teacher_id>/profile/', AdminTeacherDetailView.as_view(), name='admin_teacher_profile'),
    path('api/admin/teachers/<int:teacher_id>/analytics/', AdminTeacherAnalyticsView.as_view(), name='admin_teacher_analytics'),
    path('api/admin/teachers/<int:teacher_id>/subscription/', AdminTeacherSubscriptionView.as_view(), name='admin_teacher_subscription'),
    path('api/admin/teachers/<int:teacher_id>/storage/', AdminTeacherStorageView.as_view(), name='admin_teacher_storage'),
    path('api/admin/teachers/<int:teacher_id>/zoom/', AdminUpdateTeacherZoomView.as_view(), name='admin_update_teacher_zoom'),
    path('api/admin/teachers/<int:teacher_id>/delete/', AdminDeleteTeacherView.as_view(), name='admin_delete_teacher'),
    path('api/admin/teachers/bulk/', AdminTeachersBulkActionView.as_view(), name='admin_teachers_bulk'),
    path('api/admin/teachers/<int:teacher_id>/change-password/', AdminChangeTeacherPasswordView.as_view(), name='admin_change_teacher_password'),
    path('api/admin/students/', AdminStudentsListView.as_view(), name='admin_students_list'),
    path('api/admin/students/<int:student_id>/update/', AdminUpdateStudentView.as_view(), name='admin_update_student'),
    path('api/admin/students/<int:student_id>/delete/', AdminDeleteStudentView.as_view(), name='admin_delete_student'),
    path('api/admin/students/<int:student_id>/change-password/', AdminChangeStudentPasswordView.as_view(), name='admin_change_student_password'),
    path('api/admin/status-messages/', AdminStatusMessagesView.as_view(), name='admin_status_messages'),
    path('api/admin/status-messages/<int:message_id>/', AdminStatusMessagesView.as_view(), name='admin_status_message_delete'),
    path('api/admin/settings/', SystemSettingsView.as_view(), name='admin_settings'),
    path('api/admin/alerts/', AdminAlertsView.as_view(), name='admin_alerts'),
    path('api/admin/churn-retention/', AdminChurnRetentionView.as_view(), name='admin_churn_retention'),
    path('api/admin/cohort-retention/', AdminCohortRetentionView.as_view(), name='admin_cohort_retention'),
    path('api/admin/teachers-activity/', AdminTeachersActivityView.as_view(), name='admin_teachers_activity'),
    path('api/admin/system-health/', AdminSystemHealthView.as_view(), name='admin_system_health'),
    path('api/admin/activity-log/', AdminActivityLogView.as_view(), name='admin_activity_log'),
    path('api/admin/errors/', AdminSystemErrorsView.as_view(), name='admin_system_errors'),
    path('api/admin/errors/counts/', AdminSystemErrorsCountsView.as_view(), name='admin_system_errors_counts'),
    path('api/admin/quick-actions/', AdminQuickActionsView.as_view(), name='admin_quick_actions'),
    path('api/admin/business-metrics/', AdminBusinessMetricsView.as_view(), name='admin_business_metrics'),
    path('api/admin/dashboard-data/', AdminDashboardDataView.as_view(), name='admin_dashboard_data'),
    
    # API для получения сообщений (для всех пользователей)
    path('api/status-messages/', AdminStatusMessagesView.as_view(), name='status_messages'),
    
    # API для Email верификации
    path('api/email/send-verification/', send_verification_email, name='email_send_verification'),
    path('api/email/resend-verification/', resend_verification_email, name='email_resend_verification'),
    path('api/email/verify-code/', verify_email_code, name='email_verify_code'),
    path('api/email/verify-token/<uuid:token>/', verify_email_token, name='email_verify_token'),
    path('api/email/check-status/', check_verification_status, name='email_check_status'),
    
    # API для сброса пароля
    path('api/password-reset/request/', password_reset_request, name='password_reset_request'),
    path('api/password-reset/confirm/', password_reset_confirm, name='password_reset_confirm'),
    path('api/password-reset/validate/<str:uid>/<str:token>/', password_reset_validate_token, name='password_reset_validate'),
    
    # API для восстановления пароля через Telegram/WhatsApp
    path('api/password-reset/request-code/', request_reset_code, name='request_reset_code'),
    path('api/password-reset/verify-code/', verify_code, name='verify_reset_code'),
    path('api/password-reset/set-password/', set_new_password, name='set_new_password'),
    
    # API для пользователей
    path('api/users/', users_list, name='users_list'),
    path('api/me/', MeView.as_view(), name='me'),
    path('api/change-password/', change_password, name='change_password'),
    path('api/change-email/', change_email, name='change_email'),
    
    # API для Telegram и восстановления пароля
    path('api/telegram/link/', link_telegram, name='link_telegram'),
    path('api/telegram/unlink/', unlink_telegram, name='unlink_telegram'),
    path('api/telegram/status/', check_telegram_status, name='check_telegram_status'),
    path('api/accounts/generate-telegram-code/', generate_telegram_code, name='generate_telegram_code'),
    path('api/accounts/verify-telegram/', verify_telegram, name='verify_telegram'),
    path('api/password-reset-telegram/request/', request_password_reset, name='request_password_reset_telegram'),
    path('api/password-reset-telegram/confirm/', reset_password_with_token, name='reset_password_with_token'),
    path('api/notifications/settings/', notification_settings_view, name='notification_settings'),
    path('api/notifications/mutes/', notification_mutes_view, name='notification_mutes'),
    path('api/notifications/mutes/<int:pk>/', notification_mute_delete_view, name='notification_mute_delete'),
    
    # API для чатов
    path('api/', include(router.urls)),
    
    # Password reset (стандартные Django views)
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='accounts/password_reset.html'
         ), 
         name='password_reset'),
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='accounts/password_reset_done.html'
         ), 
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='accounts/password_reset_confirm.html'
         ), 
         name='password_reset_confirm'),
    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='accounts/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
    
    # ============================================
    # SIMPLE PASSWORD RESET (добавлено 2026-02-01)
    # Изолированный endpoint, не трогает существующий код
    # ============================================
    path('api/simple-reset/', simple_password_reset, name='simple_password_reset'),
]
