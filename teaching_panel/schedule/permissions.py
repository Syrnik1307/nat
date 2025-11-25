from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsTeacherOrReadOnly(BasePermission):
    """Только преподаватель может изменять, остальные только читать"""
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_authenticated and getattr(request.user, 'role', None) == 'teacher'


class IsLessonOwnerOrReadOnly(BasePermission):
    """Только преподаватель данного урока может его изменять"""
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_authenticated and obj.teacher_id == request.user.id

    def has_permission(self, request, view):
        # Для создания нового урока требуется быть преподавателем
        if view.action == 'create':
            return request.user.is_authenticated and getattr(request.user, 'role', None) == 'teacher'
        return True


class IsGroupOwnerOrReadOnly(BasePermission):
    """Только преподаватель-владелец группы может изменять её"""
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_authenticated and obj.teacher_id == request.user.id

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_authenticated and getattr(request.user, 'role', None) == 'teacher'