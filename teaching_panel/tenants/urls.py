from django.urls import path
from . import views

urlpatterns = [
    path('config/', views.SchoolConfigView.as_view(), name='school-config'),
    path('detail/', views.SchoolDetailView.as_view(), name='school-detail'),
]
