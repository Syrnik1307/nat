from rest_framework import serializers
from accounts.models import CustomUser
from .models import Course, CourseModule, CourseLesson


class CourseSerializer(serializers.ModelSerializer):
    teacher_email = serializers.EmailField(source='teacher.email', read_only=True)
    student_count = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ['id', 'title', 'description', 'teacher', 'teacher_email', 'students', 'student_count', 'is_published', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def get_student_count(self, obj):
        return obj.students.count()


class CourseModuleSerializer(serializers.ModelSerializer):
    lessons_count = serializers.SerializerMethodField()

    class Meta:
        model = CourseModule
        fields = ['id', 'course', 'title', 'description', 'order', 'lessons_count', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def get_lessons_count(self, obj):
        return obj.lessons.count()


class CourseLessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseLesson
        fields = [
            'id', 'course', 'module', 'title', 'order',
            'video_url', 'content', 'duration', 'is_free_preview',
            'homework', 'video_provider', 'video_status',
            'kinescope_video_id', 'kinescope_embed_url',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']
