"""URL configuration для модуля экзаменов."""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'blueprints', views.ExamBlueprintViewSet, basename='exam-blueprint')
router.register(r'tasks', views.ExamTaskViewSet, basename='exam-task')
router.register(r'variants', views.ExamVariantViewSet, basename='exam-variant')
router.register(r'attempts', views.ExamAttemptViewSet, basename='exam-attempt')

urlpatterns = [
    path('', include(router.urls)),
]
