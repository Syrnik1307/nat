"""
ПРИМЕР: Как использовать feature flags в ViewSet
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from core.feature_flags import FeatureFlags, require_feature, region_specific


class LessonViewSet(viewsets.ModelViewSet):
    """
    Уроки с поддержкой offline режима для Африки
    """
    
    # Существующий метод - работает для всех
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Старт урока (работает и в России, и в Африке)"""
        lesson = self.get_object()
        # Обычная логика
        return Response({'status': 'started'})
    
    # НОВЫЙ метод - только для Африки с включенным PWA
    @action(detail=True, methods=['post'])
    @require_feature('PWA_OFFLINE')  # Включается только если флаг True
    def download_for_offline(self, request, pk=None):
        """
        Скачать урок для offline просмотра
        Доступно ТОЛЬКО если FEATURE_PWA_OFFLINE=True
        """
        lesson = self.get_object()
        
        # Генерируем пакет для offline
        offline_package = {
            'lesson_id': lesson.id,
            'title': lesson.title,
            'video_url_360p': lesson.get_low_quality_video(),  # для Африки
            'materials': lesson.get_materials(),
            'homework': lesson.get_homework(),
        }
        
        return Response(offline_package)
    
    # НОВЫЙ метод - только для африканского региона
    @action(detail=False, methods=['post'])
    @region_specific(['africa'])  # Доступно только на teachpanel.com
    def mobile_money_payment(self, request):
        """
        Оплата через Mobile Money (M-Pesa, MTN)
        Доступно ТОЛЬКО для африканского домена
        """
        if not FeatureFlags.is_enabled('MOBILE_MONEY'):
            return Response(
                {'detail': 'Mobile Money not available'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Логика оплаты через Flutterwave
        amount = request.data.get('amount')
        phone = request.data.get('phone')
        
        # ... код оплаты ...
        
        return Response({'status': 'payment_initiated'})
    
    # Метод работает по-разному в зависимости от региона
    @action(detail=True, methods=['get'])
    def get_video_quality(self, request, pk=None):
        """
        Возвращает доступные качества видео
        Для Африки - приоритет на низкое качество
        """
        lesson = self.get_object()
        
        if FeatureFlags.is_africa_region(request):
            # Африка: 360p по умолчанию, экономим трафик
            qualities = [
                {'quality': '360p', 'size_mb': 20, 'recommended': True},
                {'quality': '480p', 'size_mb': 40, 'recommended': False},
                {'quality': '720p', 'size_mb': 80, 'recommended': False},
            ]
        else:
            # Россия: 720p по умолчанию
            qualities = [
                {'quality': '360p', 'size_mb': 20, 'recommended': False},
                {'quality': '720p', 'size_mb': 80, 'recommended': True},
                {'quality': '1080p', 'size_mb': 150, 'recommended': False},
            ]
        
        return Response({'qualities': qualities})
