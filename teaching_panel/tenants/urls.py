from django.urls import path
from . import views

urlpatterns = [
    path('config/', views.TenantConfigView.as_view(), name='tenant-config'),
    path('my/', views.MyTenantsView.as_view(), name='tenant-my'),
    path('detail/', views.TenantDetailView.as_view(), name='tenant-detail'),
    path('public/<slug:slug>/branding/', views.PublicBrandingView.as_view(), name='tenant-public-branding'),
]
