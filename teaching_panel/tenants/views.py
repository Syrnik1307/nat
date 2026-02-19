"""
API views для tenants.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import viewsets
from .models import Tenant, TenantMembership
from .serializers import (
    TenantSerializer, TenantPublicBrandingSerializer,
    TenantMembershipSerializer,
)


class TenantConfigView(APIView):
    """
    GET /api/tenants/config/

    Публичный endpoint — конфиг текущего tenant'а для frontend.
    """
    permission_classes = [AllowAny]
    throttle_classes = []

    def get(self, request):
        tenant = getattr(request, 'tenant', None)
        if tenant:
            return Response(TenantPublicBrandingSerializer(tenant).data)
        return Response({
            'name': 'LectioSpace',
            'slug': 'lectiospace',
            'logo_url': '',
            'email': '',
            'phone': '',
            'website': '',
            'metadata': {},
        })


class MyTenantsView(APIView):
    """
    GET /api/tenants/my/

    Список тенантов текущего пользователя с ролями.
    Используется фронтендом (TenantContext.js) при инициализации.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            memberships = TenantMembership.objects.filter(
                user=request.user, is_active=True
            ).select_related('tenant')

            result = []
            for m in memberships:
                result.append({
                    'tenant': TenantPublicBrandingSerializer(m.tenant).data,
                    'role': m.role,
                    'joined_at': m.joined_at.isoformat() if m.joined_at else None,
                })
            return Response(result)
        except Exception:
            # Таблица может не существовать (миграции не прошли)
            # Fallback: вернуть тенант из request.tenant
            tenant = getattr(request, 'tenant', None)
            if tenant:
                return Response([{
                    'tenant': TenantPublicBrandingSerializer(tenant).data,
                    'role': 'teacher',
                    'joined_at': None,
                }])
            return Response([])


class TenantDetailView(APIView):
    """
    GET /api/tenants/detail/

    Детальная информация о tenant'е (для owner/admin).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return Response({'detail': 'Тенант не найден'}, status=404)

        membership = getattr(request, 'tenant_membership', None)
        if not membership or membership.role not in ('owner', 'admin'):
            return Response({'detail': 'Нет доступа'}, status=403)

        data = TenantSerializer(tenant).data
        return Response(data)


class PublicBrandingView(APIView):
    """
    GET /api/tenants/public/<slug>/branding/

    Публичный брендинг по slug (без авторизации).
    """
    permission_classes = [AllowAny]
    throttle_classes = []

    def get(self, request, slug):
        try:
            tenant = Tenant.objects.get(slug=slug, status='active')
        except Tenant.DoesNotExist:
            return Response({'detail': 'Не найден'}, status=404)
        return Response(TenantPublicBrandingSerializer(tenant).data)
