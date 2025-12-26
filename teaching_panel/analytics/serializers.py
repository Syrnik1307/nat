from rest_framework import serializers
from .models import ControlPoint, ControlPointResult, StudentAIReport, StudentBehaviorReport

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

# ===== ПОВЕДЕНЧЕСКИЕ ОТЧЁТЫ =====

class StudentBehaviorReportSerializer(serializers.ModelSerializer):
    """Полный сериализатор поведенческого отчёта"""
    student_name = serializers.SerializerMethodField()
    student_email = serializers.EmailField(source='student.email', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True, allow_null=True)
    risk_level_display = serializers.CharField(source='get_risk_level_display', read_only=True)
    score_trend_display = serializers.CharField(source='get_score_trend_display', read_only=True)
    
    class Meta:
        model = StudentBehaviorReport
        fields = [
            'id', 'student', 'student_name', 'student_email',
            'teacher', 'group', 'group_name',
            'status', 'period_start', 'period_end',
            # Посещаемость
            'total_lessons', 'attended_lessons', 'missed_lessons',
            'late_arrivals', 'attendance_rate',
            # ДЗ
            'total_homework', 'submitted_on_time', 'submitted_late',
            'not_submitted', 'homework_rate',
            # Оценки
            'avg_score', 'score_trend', 'score_trend_display',
            'control_points_count', 'control_points_avg',
            # AI анализ
            'risk_level', 'risk_level_display', 'reliability_score',
            'ai_analysis', 'ai_provider', 'ai_confidence',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'status',
            'total_lessons', 'attended_lessons', 'missed_lessons',
            'late_arrivals', 'attendance_rate',
            'total_homework', 'submitted_on_time', 'submitted_late',
            'not_submitted', 'homework_rate',
            'avg_score', 'score_trend', 'control_points_count', 'control_points_avg',
            'risk_level', 'reliability_score',
            'ai_analysis', 'ai_confidence',
            'created_at', 'updated_at'
        ]
    
    def get_student_name(self, obj):
        return obj.student.get_full_name() or obj.student.email


class StudentBehaviorReportListSerializer(serializers.ModelSerializer):
    """Краткий сериализатор для списка"""
    student_name = serializers.SerializerMethodField()
    student_email = serializers.EmailField(source='student.email', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True, allow_null=True)
    risk_level_display = serializers.CharField(source='get_risk_level_display', read_only=True)
    profile_type = serializers.SerializerMethodField()
    summary = serializers.SerializerMethodField()
    alerts_count = serializers.SerializerMethodField()
    
    class Meta:
        model = StudentBehaviorReport
        fields = [
            'id', 'student', 'student_name', 'student_email',
            'group', 'group_name', 'status',
            'attendance_rate', 'homework_rate',
            'risk_level', 'risk_level_display', 'reliability_score',
            'profile_type', 'summary', 'alerts_count',
            'created_at'
        ]
    
    def get_student_name(self, obj):
        return obj.student.get_full_name() or obj.student.email
    
    def get_profile_type(self, obj):
        return obj.ai_analysis.get('profile_type', 'needs_attention') if obj.ai_analysis else 'needs_attention'
    
    def get_summary(self, obj):
        return obj.ai_analysis.get('summary', '') if obj.ai_analysis else ''
    
    def get_alerts_count(self, obj):
        alerts = obj.ai_analysis.get('alerts', []) if obj.ai_analysis else []
        return len(alerts)