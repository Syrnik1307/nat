"""
Finance app URL configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('wallets', views.WalletViewSet, basename='wallet')

urlpatterns = [
    path('', include(router.urls)),
    path('my-balance/', views.StudentBalanceView.as_view(), name='my-balance'),
    path('dashboard/', views.FinanceDashboardView.as_view(), name='finance-dashboard'),
]
