"""
Tenant-aware permissions для DRF.
"""
from rest_framework.permissions import BasePermission


class IsTenantMember(BasePermission):
    """Пользователь должен быть активным участником текущего tenant'а."""

    message = 'Вы не являетесь участником этой организации.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        tenant = getattr(request, 'tenant', None)
        if tenant is None:
            return True  # Если tenant не определён — пропускаем (другие проверки)
        membership = getattr(request, 'tenant_membership', None)
        return membership is not None


class IsTenantAdmin(BasePermission):
    """Пользователь должен быть admin/owner в текущем tenant'е."""

    message = 'Необходима роль администратора организации.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        membership = getattr(request, 'tenant_membership', None)
        if membership is None:
            return False
        return membership.role in ('owner', 'admin')


class IsTenantOwner(BasePermission):
    """Пользователь должен быть owner текущего tenant'а."""

    message = 'Необходима роль владельца организации.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        membership = getattr(request, 'tenant_membership', None)
        if membership is None:
            return False
        return membership.role == 'owner'


class IsTenantTeacher(BasePermission):
    """Пользователь должен быть teacher/admin/owner в текущем tenant'е."""

    message = 'Необходима роль преподавателя.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        membership = getattr(request, 'tenant_membership', None)
        if membership is None:
            return False
        return membership.role in ('owner', 'admin', 'teacher')


class IsTenantTeacherOrReadOnly(BasePermission):
    """Teacher/admin/owner — полный доступ; остальные — только чтение."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        membership = getattr(request, 'tenant_membership', None)
        if membership is None:
            return False
        return membership.role in ('owner', 'admin', 'teacher')
