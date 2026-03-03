from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'exam-types', views.ExamTypeViewSet, basename='exam-type')
router.register(r'subjects', views.SubjectViewSet, basename='subject')
router.register(r'topics', views.TopicViewSet, basename='topic')
router.register(r'assignments', views.ExamAssignmentViewSet, basename='exam-assignment')
router.register(r'progress', views.ProgressViewSet, basename='progress')

urlpatterns = [
    path('', include(router.urls)),
]
