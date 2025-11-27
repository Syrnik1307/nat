from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ZoomAccountViewSet

router = DefaultRouter()
router.register(r'zoom-accounts', ZoomAccountViewSet, basename='zoom-account')

urlpatterns = [
    path('', include(router.urls)),
]
