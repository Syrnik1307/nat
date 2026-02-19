from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Course, CourseModule, CourseLesson
from .serializers import CourseSerializer, CourseModuleSerializer, CourseLessonSerializer


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


class CourseModuleViewSet(viewsets.ModelViewSet):
    serializer_class = CourseModuleSerializer

    def get_queryset(self):
        qs = CourseModule.objects.all()
        course_id = self.request.query_params.get('course')
        if course_id:
            qs = qs.filter(course_id=course_id)
        return qs


class CourseLessonViewSet(viewsets.ModelViewSet):
    serializer_class = CourseLessonSerializer

    def get_queryset(self):
        qs = CourseLesson.objects.all()
        course_id = self.request.query_params.get('course')
        module_id = self.request.query_params.get('module')
        if course_id:
            qs = qs.filter(course_id=course_id)
        if module_id:
            qs = qs.filter(module_id=module_id)
        return qs
