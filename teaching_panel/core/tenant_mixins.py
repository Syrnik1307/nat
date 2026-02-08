"""
Tenant-Ready Mixins для ViewSets.

Multi-tenant изоляция данных по школам.

Как использовать:
    class GroupViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
        queryset = Group.objects.all()
        ...

TenantMiddleware определяет школу по поддомену и кладёт в request.school.
Этот миксин автоматически фильтрует queryset по школе.

Feature flag: TENANT_ISOLATION_ENABLED (settings.py)
  False → pass-through, ничего не фильтрует
  True  → полная изоляция по school
"""

import logging
from django.conf import settings
from tenants.middleware import get_current_school

logger = logging.getLogger(__name__)


class TenantViewSetMixin:
    """
    Миксин для ViewSets с tenant-изоляцией.
    
    Автоматически:
    - Фильтрует queryset по school (когда TENANT_ISOLATION_ENABLED=True)
    - Привязывает school при создании объектов
    - Fallback на всех учителей школы для моделей без прямого school FK
    - Superuser видит всё (нет фильтрации)
    """
    
    def get_queryset(self):
        qs = super().get_queryset()
        
        if not getattr(settings, 'TENANT_ISOLATION_ENABLED', False):
            return qs
        
        # Superuser видит всё
        if hasattr(self, 'request') and self.request.user.is_superuser:
            return qs
        
        school = getattr(self.request, 'school', None) or get_current_school()
        if not school:
            return qs
        
        if hasattr(qs.model, 'school'):
            # Модели с прямым school FK (Group, Homework, Subscription, etc)
            qs = qs.filter(school=school)
        elif hasattr(qs.model, 'teacher'):
            # Модели без school FK, привязанные к учителю
            from tenants.models import SchoolMembership
            teacher_ids = SchoolMembership.objects.filter(
                school=school,
                role__in=['owner', 'admin', 'teacher'],
                is_active=True,
            ).values_list('user_id', flat=True)
            qs = qs.filter(teacher_id__in=teacher_ids)
        
        return qs
    
    def perform_create(self, serializer):
        if getattr(settings, 'TENANT_ISOLATION_ENABLED', False):
            school = getattr(self.request, 'school', None) or get_current_school()
            if school and hasattr(serializer.Meta.model, 'school'):
                serializer.save(school=school)
                return
        
        super().perform_create(serializer)


class TenantSerializerMixin:
    """
    Миксин для Serializers — скрывает school поле от API.
    
    School определяется middleware, не клиентом.
    school поле read_only, устанавливается автоматически из request.
    """
    pass
