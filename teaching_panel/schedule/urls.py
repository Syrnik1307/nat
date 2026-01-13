from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import celery_metrics
from . import webhooks
from . import storage_views
from . import material_views
from . import calendar_views

app_name = 'schedule'

# DRF Router для API
router = DefaultRouter()
router.register(r'api/groups', views.GroupViewSet, basename='api-group')
router.register(r'api/lessons', views.LessonViewSet, basename='api-lesson')
router.register(r'api/attendance', views.AttendanceViewSet, basename='api-attendance')
router.register(r'api/zoom-accounts', views.ZoomAccountViewSet, basename='api-zoom-account')
router.register(r'api/recurring-lessons', views.RecurringLessonViewSet, basename='api-recurring-lesson')
router.register(r'api/lesson-materials', views.LessonMaterialViewSet, basename='api-lesson-material')

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
    path('api/recordings/<int:recording_id>/delete/', views.delete_recording, name='delete_recording'),
    path('api/lessons/<int:lesson_id>/recording/', views.lesson_recording, name='lesson_recording'),
    
    # API endpoints для управления квотами хранилища (только для админа)
    path('api/storage/quotas/', storage_views.storage_quotas_list, name='storage_quotas_list'),
    path('api/storage/quotas/<int:quota_id>/', storage_views.storage_quota_detail, name='storage_quota_detail'),
    path('api/storage/quotas/<int:quota_id>/increase/', storage_views.increase_quota, name='increase_quota'),
    path('api/storage/quotas/<int:quota_id>/reset-warnings/', storage_views.reset_quota_warnings, name='reset_quota_warnings'),
    path('api/storage/statistics/', storage_views.storage_statistics, name='storage_statistics'),
    path('api/storage/teachers/<int:teacher_id>/recordings/', storage_views.teacher_recordings_list, name='admin_teacher_recordings'),
    path('api/storage/quotas/create/', storage_views.create_teacher_quota, name='create_teacher_quota'),
    
    # Google Drive Storage Stats
    path('api/storage/gdrive-stats/all/', storage_views.gdrive_stats_all_teachers, name='gdrive_stats_all_teachers'),
    path('api/storage/gdrive-stats/my/', storage_views.gdrive_stats_my_storage, name='gdrive_stats_my_storage'),
    
    # API endpoints для учебных материалов
    path('api/lessons/<int:lesson_id>/materials/upload/', material_views.upload_material, name='upload_material'),
    path('api/lessons/<int:lesson_id>/materials/', material_views.list_materials, name='list_materials'),
    path('api/lessons/<int:lesson_id>/materials/statistics/', material_views.get_lesson_materials_statistics, name='lesson_materials_statistics'),
    path('api/materials/<int:material_id>/', material_views.get_material_detail, name='material_detail'),
    path('api/materials/<int:material_id>/view/', material_views.track_material_view, name='track_material_view'),
    path('api/materials/<int:material_id>/views/', material_views.get_material_views, name='material_views'),
    path('api/materials/<int:material_id>/delete/', material_views.delete_material, name='delete_material'),
    
    # Miro Integration API
    path('api/miro/add-board/', views.miro_add_board, name='miro_add_board'),
    path('api/miro/create-board/', views.miro_create_board, name='miro_create_board'),
    path('api/miro/status/', views.miro_status, name='miro_status'),
    
    # Notes & Documents API
    path('api/materials/add-notes/', views.add_notes, name='add_notes'),
    path('api/materials/add-document/', views.add_document, name='add_document'),    
    # Calendar export / subscription (iCal) для Google, Яндекс, Apple Calendar
    path('api/calendar/export/ics/', calendar_views.export_calendar_ics, name='calendar_export_ics'),
    path('api/calendar/feed/<int:user_id>/<str:token>/', calendar_views.calendar_feed, name='calendar_feed'),
    path('api/calendar/lesson/<int:lesson_id>/ics/', calendar_views.lesson_ics, name='calendar_lesson_ics'),
    path('api/calendar/subscribe-links/', calendar_views.subscribe_links, name='calendar_subscribe_links'),
    path('api/calendar/regenerate-token/', calendar_views.regenerate_calendar_token, name='calendar_regenerate_token'),
    
    # API endpoints
    path('', include(router.urls)),
]