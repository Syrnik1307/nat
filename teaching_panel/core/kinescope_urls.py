from django.urls import path
from .kinescope_webhook import kinescope_webhook

urlpatterns = [
    path('', kinescope_webhook, name='kinescope-webhook'),
]
