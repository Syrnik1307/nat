from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsTeacherOrReadOnly(BasePermission):
    """Только преподаватель может изменять, остальные только читать"""
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_authenticated and getattr(request.user, 'role', None) == 'teacher'


class IsLessonOwnerOrReadOnly(BasePermission):
    """
    Проверяет доступ к уроку:
    - Мутации (POST/PUT/DELETE): только преподаватель урока
    - Чтение (GET): преподаватель урока, студент из группы урока, или админ
    
    БЕЗОПАСНОСТЬ: Предотвращает IDOR - студент не может просматривать чужие уроки.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user.is_authenticated:
            return False
        
        role = getattr(user, 'role', None)
        
        # Админ имеет полный доступ
        if role == 'admin':
            return True
        
        # Для мутаций - только учитель урока
        if request.method not in SAFE_METHODS:
            return role == 'teacher' and obj.teacher_id == user.id
        
        # Для чтения:
        # 1. Учитель видит свои уроки
        if role == 'teacher':
            return obj.teacher_id == user.id
        
        # 2. Студент видит только уроки групп, в которых он состоит
        if role == 'student':
            return obj.group.students.filter(id=user.id).exists()
        
        # Другие роли - нет доступа
        return False

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