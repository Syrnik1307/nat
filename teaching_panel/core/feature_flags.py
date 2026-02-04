"""
Feature Flags System для безопасной разработки новых фич
Позволяет включать/выключать функционал без деплоя
"""
from django.conf import settings
from functools import wraps
from rest_framework.response import Response
from rest_framework import status


class FeatureFlags:
    """
    Центральное место управления feature flags
    """
    
    # Флаги для африканской версии
    AFRICA_MARKET = getattr(settings, 'FEATURE_AFRICA_MARKET', False)
    PWA_OFFLINE = getattr(settings, 'FEATURE_PWA_OFFLINE', False)
    MOBILE_MONEY = getattr(settings, 'FEATURE_MOBILE_MONEY', False)
    SMS_NOTIFICATIONS = getattr(settings, 'FEATURE_SMS_NOTIFICATIONS', False)
    MULTILINGUAL = getattr(settings, 'FEATURE_MULTILINGUAL', False)
    ADAPTIVE_VIDEO = getattr(settings, 'FEATURE_ADAPTIVE_VIDEO', False)
    
    # Флаги для российского рынка
    YOOKASSA_PAYMENTS = getattr(settings, 'FEATURE_YOOKASSA_PAYMENTS', True)
    TELEGRAM_SUPPORT = getattr(settings, 'FEATURE_TELEGRAM_SUPPORT', True)
    
    @classmethod
    def is_enabled(cls, flag_name: str) -> bool:
        """Проверить, включен ли флаг"""
        return getattr(cls, flag_name, False)
    
    @classmethod
    def get_region(cls, request) -> str:
        """
        Определить регион пользователя по домену или заголовку
        """
        host = request.get_host()
        
        # Определяем по домену
        if 'lectiospace.ru' in host:
            return 'russia'
        elif 'teachpanel.com' in host or 'teachpanel.africa' in host:
            return 'africa'
        
        # Определяем по заголовку (для тестирования)
        region_header = request.headers.get('X-Region', 'russia')
        return region_header.lower()
    
    @classmethod
    def is_africa_region(cls, request) -> bool:
        """Проверить, африканский ли регион"""
        return cls.get_region(request) == 'africa'


def require_feature(flag_name: str):
    """
    Декоратор для защиты эндпоинтов feature flag'ом
    
    Usage:
        @require_feature('PWA_OFFLINE')
        def download_lesson_offline(self, request, pk=None):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            if not FeatureFlags.is_enabled(flag_name):
                return Response(
                    {'detail': f'Feature {flag_name} is not enabled'},
                    status=status.HTTP_404_NOT_FOUND
                )
            return view_func(self, request, *args, **kwargs)
        return wrapper
    return decorator


def region_specific(allowed_regions: list):
    """
    Декоратор для ограничения эндпоинтов по регионам
    
    Usage:
        @region_specific(['africa'])
        def mobile_money_payment(self, request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            region = FeatureFlags.get_region(request)
            if region not in allowed_regions:
                return Response(
                    {'detail': f'Not available in region: {region}'},
                    status=status.HTTP_403_FORBIDDEN
                )
            return view_func(self, request, *args, **kwargs)
        return wrapper
    return decorator
