"""
Permission classes for finance API.
"""
from rest_framework import permissions


class IsTeacher(permissions.BasePermission):
    """Разрешение только для учителей."""
    
    message = 'Доступ только для учителей'
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'teacher'
        )


class IsStudent(permissions.BasePermission):
    """Разрешение только для учеников."""
    
    message = 'Доступ только для учеников'
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == 'student'
        )


class IsTeacherOrStudent(permissions.BasePermission):
    """Разрешение для учителей и учеников."""
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in ('teacher', 'student')
        )
