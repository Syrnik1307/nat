"""
Role-Based Access Control (RBAC) permission classes.

Используйте эти классы вместо голого IsAuthenticated для защиты endpoints:

    from accounts.permissions import IsTeacher, IsTeacherOrAdmin

    class MyView(APIView):
        permission_classes = [IsAuthenticated, IsTeacher]

Доступные классы:
- IsStudent: только ученики
- IsTeacher: только учителя
- IsAdmin: только администраторы (role='admin')
- IsTeacherOrAdmin: учителя или администраторы
- IsSameUserOrAdmin: владелец ресурса или админ
- IsGroupOwner: владелец группы (через group_id в query/data)
- IsLessonOwner: владелец урока (через lesson_id/pk)
"""

from rest_framework.permissions import BasePermission
import logging

logger = logging.getLogger(__name__)


class IsStudent(BasePermission):
    """Доступ только для учеников (role='student')"""
    message = 'Доступно только для учеников'
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role == 'student'


class IsTeacher(BasePermission):
    """Доступ только для учителей (role='teacher')"""
    message = 'Доступно только для учителей'
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role == 'teacher'


class IsAdmin(BasePermission):
    """Доступ только для администраторов (role='admin')"""
    message = 'Доступно только для администраторов'
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role == 'admin' or request.user.is_superuser


class IsTeacherOrAdmin(BasePermission):
    """Доступ для учителей и администраторов"""
    message = 'Доступно только для учителей и администраторов'
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role in ('teacher', 'admin') or request.user.is_superuser


class IsStudentOrTeacher(BasePermission):
    """Доступ для учеников и учителей (не админов-только)"""
    message = 'Доступно для учеников и учителей'
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role in ('student', 'teacher')


class IsSameUserOrAdmin(BasePermission):
    """
    Доступ только для владельца ресурса или администратора.
    
    Ожидает user_id в URL kwargs или объект с атрибутом user/user_id.
    """
    message = 'Доступно только владельцу или администратору'
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Админы имеют доступ ко всему
        if request.user.role == 'admin' or request.user.is_superuser:
            return True
        
        # Проверяем user_id в URL
        user_id = view.kwargs.get('user_id') or view.kwargs.get('pk')
        if user_id:
            return str(request.user.id) == str(user_id)
        
        return True  # Проверка на уровне has_object_permission
    
    def has_object_permission(self, request, view, obj):
        if request.user.role == 'admin' or request.user.is_superuser:
            return True
        
        # Проверяем владельца объекта
        if hasattr(obj, 'user_id'):
            return obj.user_id == request.user.id
        if hasattr(obj, 'user'):
            return obj.user == request.user
        if hasattr(obj, 'teacher_id'):
            return obj.teacher_id == request.user.id
        if hasattr(obj, 'teacher'):
            return obj.teacher == request.user
        
        return False


class IsGroupOwner(BasePermission):
    """
    Проверяет что пользователь является владельцем группы.
    
    Ищет group_id в query_params, data, или URL kwargs.
    Пропускает проверку если group_id не указан (проверяется в view).
    """
    message = 'Вы не являетесь владельцем этой группы'
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Админы имеют доступ ко всему
        if request.user.role == 'admin' or request.user.is_superuser:
            return True
        
        # Ищем group_id
        group_id = (
            request.query_params.get('group_id') or 
            request.data.get('group_id') or
            view.kwargs.get('group_id') or
            view.kwargs.get('pk')
        )
        
        if not group_id:
            return True  # Нет group_id - проверка в view
        
        # Проверяем владение
        from schedule.models import Group
        try:
            return Group.objects.filter(id=group_id, teacher=request.user).exists()
        except Exception as e:
            logger.warning(f"IsGroupOwner check failed: {e}")
            return False


class IsLessonOwner(BasePermission):
    """
    Проверяет что пользователь является владельцем урока (через группу).
    
    Ищет lesson_id/pk в URL kwargs.
    """
    message = 'Вы не являетесь владельцем этого урока'
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Админы имеют доступ ко всему
        if request.user.role == 'admin' or request.user.is_superuser:
            return True
        
        # Ищем lesson_id
        lesson_id = view.kwargs.get('lesson_id') or view.kwargs.get('pk')
        
        if not lesson_id:
            return True  # Нет lesson_id - проверка в view
        
        # Проверяем владение через группу
        from schedule.models import Lesson
        try:
            lesson = Lesson.objects.select_related('group').filter(id=lesson_id).first()
            if not lesson:
                return False
            return lesson.group.teacher_id == request.user.id
        except Exception as e:
            logger.warning(f"IsLessonOwner check failed: {e}")
            return False
    
    def has_object_permission(self, request, view, obj):
        if request.user.role == 'admin' or request.user.is_superuser:
            return True
        
        # obj - это Lesson
        if hasattr(obj, 'group'):
            return obj.group.teacher_id == request.user.id
        
        return False


class IsSubscriptionOwner(BasePermission):
    """
    Проверяет что подписка принадлежит текущему пользователю.
    """
    message = 'Эта подписка вам не принадлежит'
    
    def has_object_permission(self, request, view, obj):
        if request.user.role == 'admin' or request.user.is_superuser:
            return True
        
        if hasattr(obj, 'user_id'):
            return obj.user_id == request.user.id
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        return False
