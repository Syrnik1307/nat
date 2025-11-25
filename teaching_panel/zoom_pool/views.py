from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import F
from .models import ZoomAccount, ZoomPoolUsageMetrics
from .serializers import ZoomAccountSerializer


class IsAdminRole(IsAuthenticated):
    """Доступ только администраторам/суперпользователям"""
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        user = request.user
        return getattr(user, 'role', None) == 'admin' or user.is_staff or user.is_superuser


class ZoomAccountViewSet(viewsets.ModelViewSet):
    queryset = ZoomAccount.objects.all().order_by('email')
    serializer_class = ZoomAccountSerializer
    permission_classes = [IsAdminRole]
    
    @action(detail=True, methods=['post'])
    def release(self, request, pk=None):
        """Освободить аккаунт вручную"""
        account = self.get_object()
        account.release()
        return Response({
            'detail': 'Аккаунт освобожден',
            'current_meetings': account.current_meetings
        })
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Включить/выключить аккаунт"""
        account = self.get_object()
        account.is_active = not account.is_active
        account.save()
        return Response({
            'detail': 'Статус изменен',
            'is_active': account.is_active
        })
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Статистика пула Zoom аккаунтов"""
        metrics = ZoomPoolUsageMetrics.refresh_usage()
        total_accounts = ZoomAccount.objects.count()
        active_accounts = ZoomAccount.objects.filter(is_active=True).count()
        available_accounts = ZoomAccount.objects.filter(
            is_active=True,
            current_meetings__lt=F('max_concurrent_meetings')
        ).count()
        
        return Response({
            'total_accounts': total_accounts,
            'active_accounts': active_accounts,
            'available_accounts': available_accounts,
            'currently_in_use': metrics.current_in_use,
            'peak_in_use': metrics.peak_in_use,
            'current_sessions': metrics.current_sessions,
            'peak_sessions': metrics.peak_sessions,
            'updated_at': metrics.updated_at,
        })
