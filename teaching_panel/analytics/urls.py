from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ControlPointViewSet, 
    ControlPointResultViewSet, 
    GradebookViewSet, 
    TeacherStatsViewSet, 
    StudentStatsViewSet,
    StudentAIReportViewSet,
    StudentBehaviorReportViewSet,
    AnalyticsDashboardViewSet
)

router = DefaultRouter()
router.register(r'dashboard', AnalyticsDashboardViewSet, basename='analytics-dashboard')
router.register(r'control-points', ControlPointViewSet, basename='control-point')
router.register(r'control-point-results', ControlPointResultViewSet, basename='control-point-result')
router.register(r'gradebook', GradebookViewSet, basename='gradebook')
router.register(r'teacher-stats', TeacherStatsViewSet, basename='teacher-stats')
router.register(r'student-stats', StudentStatsViewSet, basename='student-stats')
router.register(r'ai-reports', StudentAIReportViewSet, basename='ai-reports')
router.register(r'behavior-reports', StudentBehaviorReportViewSet, basename='behavior-reports')

urlpatterns = [
    path('', include(router.urls)),
]
