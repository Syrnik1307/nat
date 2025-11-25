from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Course
from .serializers import CourseSerializer


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_authenticated:
            if getattr(user, 'role', None) == 'teacher':
                return qs.filter(teacher=user) | qs.filter(students=user)
            elif getattr(user, 'role', None) == 'student':
                return qs.filter(students=user)
        return qs.none()

    @action(detail=True, methods=['post'])
    def add_student(self, request, pk=None):
        course = self.get_object()
        student_id = request.data.get('student_id')
        if student_id:
            course.students.add(student_id)
            return Response({'status': 'student added'})
        return Response({'error': 'student_id required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def remove_student(self, request, pk=None):
        course = self.get_object()
        student_id = request.data.get('student_id')
        if student_id:
            course.students.remove(student_id)
            return Response({'status': 'student removed'})
        return Response({'error': 'student_id required'}, status=status.HTTP_400_BAD_REQUEST)
