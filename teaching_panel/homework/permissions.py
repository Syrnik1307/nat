from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsTeacherHomework(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user.is_authenticated
        return request.user.is_authenticated and getattr(request.user, 'role', None) == 'teacher'

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return request.user.is_authenticated
        return obj.teacher_id == request.user.id


class IsStudentSubmission(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        user_role = getattr(request.user, 'role', None)
        # Студент видит только свои работы
        if user_role == 'student':
            return obj.student_id == request.user.id
        # Учитель видит работы по своим заданиям
        if user_role == 'teacher':
            return obj.homework.teacher_id == request.user.id
        # Админ видит всё
        if user_role == 'admin':
            return True
        return False