from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import celery_metrics

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
    
    # Webhook для событий Zoom
    path('webhook/zoom/', views.zoom_webhook_receiver, name='zoom_webhook'),
    
    # Celery metrics endpoints
    path('api/celery/metrics/', celery_metrics.celery_metrics, name='celery_metrics'),
    path('api/celery/trigger/<str:task_name>/', celery_metrics.trigger_task, name='trigger_task'),
    path('api/celery/status/<str:task_id>/', celery_metrics.task_status, name='task_status'),
    
    # API endpoints
    path('', include(router.urls)),
]
