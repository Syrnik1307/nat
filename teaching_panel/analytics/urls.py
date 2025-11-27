from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ControlPointViewSet, ControlPointResultViewSet, GradebookViewSet, TeacherStatsViewSet

router = DefaultRouter()
router.register(r'control-points', ControlPointViewSet, basename='control-point')
router.register(r'control-point-results', ControlPointResultViewSet, basename='control-point-result')
router.register(r'gradebook', GradebookViewSet, basename='gradebook')
router.register(r'teacher-stats', TeacherStatsViewSet, basename='teacher-stats')

urlpatterns = [
    path('', include(router.urls)),
]
