"""
API views для tenants.

SchoolConfigView — публичный endpoint, отдаёт конфиг школы для frontend.
Frontend при загрузке дёргает /api/school/config/ и получает:
  - Название школы
  - Цвета, логотип
  - Доступные фичи
  - Username Telegram бота
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.conf import settings as django_settings


class SchoolConfigView(APIView):
    """
    GET /api/school/config/
    
    Публичный endpoint — конфиг текущей школы для frontend.
    Не содержит секретов (ключи, пароли).
    Школа определяется TenantMiddleware по hostname.
    
    Ответ:
    {
        "id": "uuid",
        "slug": "anna",
        "name": "English with Anna",
        "logo_url": "https://...",
        "primary_color": "#4F46E5",
        "features": { "zoom": true, ... }
    }
    """
    permission_classes = [AllowAny]
    # Без throttle — этот endpoint дёргается при каждой загрузке страницы
    throttle_classes = []
    
    def get(self, request):
        school = getattr(request, 'school', None)
        
        if school:
            return Response(school.to_frontend_config())
        
        # Fallback: default platform config (до создания School)
        platform = django_settings.PLATFORM_CONFIG
        return Response({
            'id': None,
            'slug': 'lectiospace',
            'name': platform['name'],
            'logo_url': '',
            'favicon_url': '',
            'primary_color': '#4F46E5',
            'secondary_color': '#7C3AED',
            'custom_domain': None,
            'telegram_bot_username': platform['integrations']['telegram'].get('bot_username', ''),
            'currency': 'RUB',
            'features': platform.get('default_features', {}),
        })


class SchoolDetailView(APIView):
    """
    GET /api/school/detail/
    
    Детальная информация о школе (для owner/admin).
    Включает лимиты, статистику, revenue share.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        school = getattr(request, 'school', None)
        if not school:
            return Response({'detail': 'Школа не найдена'}, status=404)
        
        # Только owner видит детали
        if school.owner != request.user:
            return Response({'detail': 'Нет доступа'}, status=403)
        
        config = school.to_frontend_config()
        config.update({
            'owner_email': school.owner.email,
            'revenue_share_percent': school.revenue_share_percent,
            'limits': {
                'max_students': school.max_students,
                'max_groups': school.max_groups,
                'max_teachers': school.max_teachers,
                'max_storage_gb': school.max_storage_gb,
            },
            'stats': {
                'memberships_count': school.memberships.count(),
                'students_count': school.memberships.filter(role='student').count(),
                'teachers_count': school.memberships.filter(role='teacher').count(),
            },
            'is_active': school.is_active,
            'created_at': school.created_at.isoformat(),
        })
        return Response(config)
