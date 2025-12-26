from rest_framework import serializers
from .models import ControlPoint, ControlPointResult, StudentAIReport

class ControlPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = ControlPoint
        fields = ['id', 'title', 'teacher', 'group', 'lesson', 'max_points', 'date', 'created_at']

class ControlPointResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = ControlPointResult
        fields = ['id', 'control_point', 'student', 'points', 'created_at']


class StudentAIReportSerializer(serializers.ModelSerializer):
    """Сериализатор AI-отчёта по студенту"""
    student_name = serializers.SerializerMethodField()
    student_email = serializers.EmailField(source='student.email', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True, allow_null=True)
    
    class Meta:
        model = StudentAIReport
        fields = [
            'id', 'student', 'student_name', 'student_email',
            'teacher', 'group', 'group_name',
            'status', 'period_start', 'period_end',
            'total_submissions', 'avg_score_percent',
            'total_questions_answered', 'questions_needing_review',
            'ai_analysis', 'ai_provider', 'ai_confidence',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'status', 'total_submissions', 'avg_score_percent',
            'total_questions_answered', 'questions_needing_review',
            'ai_analysis', 'ai_confidence', 'created_at', 'updated_at'
        ]
    
    def get_student_name(self, obj):
        return obj.student.get_full_name() or obj.student.email


class StudentAIReportListSerializer(serializers.ModelSerializer):
    """Упрощённый сериализатор для списка отчётов"""
    student_name = serializers.SerializerMethodField()
    student_email = serializers.EmailField(source='student.email', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True, allow_null=True)
    progress_trend = serializers.SerializerMethodField()
    summary = serializers.SerializerMethodField()
    
    class Meta:
        model = StudentAIReport
        fields = [
            'id', 'student', 'student_name', 'student_email',
            'group', 'group_name', 'status',
            'avg_score_percent', 'total_submissions',
            'progress_trend', 'summary',
            'created_at'
        ]
    
    def get_student_name(self, obj):
        return obj.student.get_full_name() or obj.student.email
    
    def get_progress_trend(self, obj):
        return obj.ai_analysis.get('progress_trend', 'stable') if obj.ai_analysis else 'stable'
    
    def get_summary(self, obj):
        return obj.ai_analysis.get('summary', '') if obj.ai_analysis else ''
