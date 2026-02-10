from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'exam-types', views.ExamTypeViewSet, basename='exam-types')
router.register(r'subjects', views.SubjectViewSet, basename='subjects')
router.register(r'topics', views.TopicViewSet, basename='topics')
router.register(r'assignments', views.StudentExamAssignmentViewSet, basename='assignments')
router.register(r'progress', views.KnowledgeMapViewSet, basename='progress')

urlpatterns = [
    path('', include(router.urls)),
]
