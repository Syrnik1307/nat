"""
Tenant mixins — переиспользуемые компоненты для tenant-scoped моделей и ViewSets.
"""
from django.db import models
from rest_framework.exceptions import PermissionDenied

from .context import get_current_tenant


# ═══════════════════════════════════════════════════════════════
# MODEL MIXINS
# ═══════════════════════════════════════════════════════════════

class TenantModelMixin(models.Model):
    """
    Абстрактный mixin — добавляет FK tenant к модели.

    Использование:
        class MyModel(TenantModelMixin, models.Model):
            name = models.CharField(...)
    """
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='%(app_label)s_%(class)ss',
        verbose_name='Тенант',
        null=True,        # Временно nullable для миграции существующих данных
        blank=True,
        db_index=True,
    )

    class Meta:
        abstract = True


class TenantQuerySet(models.QuerySet):
    """QuerySet, который автоматически фильтрует по текущему tenant."""

    def for_tenant(self, tenant):
        """Явно отфильтровать по tenant."""
        if tenant is None:
            return self
        return self.filter(tenant=tenant)

    def for_current_tenant(self):
        """Фильтр по tenant из thread-local."""
        tenant = get_current_tenant()
        return self.for_tenant(tenant)


class TenantManager(models.Manager):
    """Manager, который возвращает TenantQuerySet."""

    def get_queryset(self):
        return TenantQuerySet(self.model, using=self._db)

    def for_tenant(self, tenant):
        return self.get_queryset().for_tenant(tenant)

    def for_current_tenant(self):
        return self.get_queryset().for_current_tenant()


# ═══════════════════════════════════════════════════════════════
# VIEWSET / VIEW MIXINS
# ═══════════════════════════════════════════════════════════════

class TenantViewSetMixin:
    """
    Mixin для DRF ViewSets — автоматически фильтрует queryset по request.tenant
    и устанавливает tenant при создании объектов.

    Использование:
        class MyViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
            queryset = MyModel.objects.all()
            serializer_class = MySerializer
    """

    tenant_field = 'tenant'           # Имя FK-поля на модели
    tenant_required = True            # Запрещать доступ если tenant не определён

    def get_queryset(self):
        qs = super().get_queryset()
        tenant = getattr(self.request, 'tenant', None)

        if tenant is not None and self.tenant_required:
            qs = qs.filter(**{self.tenant_field: tenant})
        elif tenant is None and self.tenant_required:
            return qs.none()

        return qs

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None)
        if self.tenant_required and tenant is None:
            raise PermissionDenied('Tenant не определён. Невозможно создать объект.')
        # Для дочерних моделей (tenant_field='lesson__tenant') не устанавливаем
        # tenant напрямую — связь идёт через родительскую модель.
        model = getattr(getattr(serializer, 'Meta', None), 'model', None)
        if model and hasattr(model, 'tenant'):
            serializer.save(tenant=tenant)
        else:
            serializer.save()

    def perform_update(self, serializer):
        # При обновлении не меняем tenant
        serializer.save()


class TenantAPIViewMixin:
    """
    Mixin для APIView (не ViewSet) — проверяет наличие tenant.

    Использование:
        class MyView(TenantAPIViewMixin, APIView):
            def get(self, request):
                tenant = request.tenant
                ...
    """

    tenant_required = True

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if self.tenant_required and getattr(request, 'tenant', None) is None:
            raise PermissionDenied('Организация не определена.')
