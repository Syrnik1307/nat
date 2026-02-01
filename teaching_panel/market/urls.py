"""
Market URL configuration.
"""
from django.urls import path
from .views import ProductListView, MyOrdersView, CreateOrderView, MarketWebhookView

urlpatterns = [
    path('products/', ProductListView.as_view(), name='market-products'),
    path('my-orders/', MyOrdersView.as_view(), name='market-my-orders'),
    path('buy/', CreateOrderView.as_view(), name='market-buy'),
    path('webhook/', MarketWebhookView.as_view(), name='market-webhook'),
]
