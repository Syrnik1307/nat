from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import celery_metrics
from . import webhooks
from . import storage_views

app_name = 'schedule'

# DRF Router для API
router = DefaultRouter()
router.register(r'api/groups', views.GroupViewSet, basename='api-group')
router.register(r'api/lessons', views.LessonViewSet, basename='api-lesson')
router.register(r'api/attendance', views.AttendanceViewSet, basename='api-attendance')
router.register(r'api/zoom-accounts', views.ZoomAccountViewSet, basename='api-zoom-account')
router.register(r'api/recurring-lessons', views.RecurringLessonViewSet, basename='api-recurring-lesson')

urlpatterns = [
    # Web UI для преподавателей и студентов
    path('teacher/', views.teacher_schedule_view, name='teacher_schedule'),
    path('student/', views.student_dashboard_view, name='student_dashboard'),
    
    # Запуск урока теперь через DRF action: /api/lessons/<id>/start/
    
    # Webhook для событий Zoom (старый)
    path('webhook/zoom/', views.zoom_webhook_receiver, name='zoom_webhook'),
    
    # Новый webhook для записей уроков Zoom
    path('api/zoom/webhook/', webhooks.zoom_webhook, name='zoom_recording_webhook'),
    
    # Celery metrics endpoints
    path('api/celery/metrics/', celery_metrics.celery_metrics, name='celery_metrics'),
    path('api/celery/trigger/<str:task_name>/', celery_metrics.trigger_task, name='trigger_task'),
    path('api/celery/status/<str:task_id>/', celery_metrics.task_status, name='task_status'),
    
    # API endpoints для записей уроков
    path('api/recordings/', views.student_recordings_list, name='student_recordings_list'),
    path('api/recordings/teacher/', views.teacher_recordings_list, name='teacher_recordings_list'),
    path('api/recordings/<int:recording_id>/', views.recording_detail, name='recording_detail'),
    path('api/recordings/<int:recording_id>/view/', views.recording_track_view, name='recording_track_view'),
    path('api/lessons/<int:lesson_id>/recording/', views.lesson_recording, name='lesson_recording'),
    
    # API endpoints для управления квотами хранилища (только для админа)
    path('api/storage/quotas/', storage_views.storage_quotas_list, name='storage_quotas_list'),
    path('api/storage/quotas/<int:quota_id>/', storage_views.storage_quota_detail, name='storage_quota_detail'),
    path('api/storage/quotas/<int:quota_id>/increase/', storage_views.increase_quota, name='increase_quota'),
    path('api/storage/quotas/<int:quota_id>/reset-warnings/', storage_views.reset_quota_warnings, name='reset_quota_warnings'),
    path('api/storage/statistics/', storage_views.storage_statistics, name='storage_statistics'),
    path('api/storage/teachers/<int:teacher_id>/recordings/', storage_views.teacher_recordings_list, name='admin_teacher_recordings'),
    path('api/storage/quotas/create/', storage_views.create_teacher_quota, name='create_teacher_quota'),
    
    # API endpoints
    path('', include(router.urls)),
]

