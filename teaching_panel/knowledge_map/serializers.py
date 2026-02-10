from rest_framework import serializers
from .models import (
    ExamType, Subject, Section, Topic,
    StudentExamAssignment, StudentTopicMastery,
)


class ExamTypeSerializer(serializers.ModelSerializer):
    subjects_count = serializers.SerializerMethodField()

    class Meta:
        model = ExamType
        fields = ['id', 'code', 'name', 'description', 'subjects_count']

    def get_subjects_count(self, obj):
        return obj.subjects.count()


class TopicSerializer(serializers.ModelSerializer):
    difficulty_display = serializers.CharField(
        source='get_difficulty_display', read_only=True
    )

    class Meta:
        model = Topic
        fields = [
            'id', 'code', 'name', 'description', 'task_number',
            'max_score', 'difficulty', 'difficulty_display',
            'fipi_code', 'keywords', 'order',
        ]


class TopicBriefSerializer(serializers.ModelSerializer):
    """Краткая версия для выпадающего списка в конструкторе ДЗ."""
    section_name = serializers.CharField(source='section.name', read_only=True)
    subject_name = serializers.CharField(source='section.subject.name', read_only=True)
    exam_type = serializers.CharField(source='section.subject.exam_type.code', read_only=True)

    class Meta:
        model = Topic
        fields = [
            'id', 'code', 'name', 'task_number', 'max_score',
            'difficulty', 'section_name', 'subject_name', 'exam_type',
        ]


class SectionSerializer(serializers.ModelSerializer):
    topics = TopicSerializer(many=True, read_only=True)
    topics_count = serializers.SerializerMethodField()

    class Meta:
        model = Section
        fields = ['id', 'code', 'name', 'description', 'order', 'topics', 'topics_count']

    def get_topics_count(self, obj):
        return obj.topics.count()


class SubjectSerializer(serializers.ModelSerializer):
    exam_type_code = serializers.CharField(source='exam_type.code', read_only=True)
    exam_type_name = serializers.CharField(source='exam_type.name', read_only=True)
    sections = SectionSerializer(many=True, read_only=True)

    class Meta:
        model = Subject
        fields = [
            'id', 'code', 'name', 'icon', 'color',
            'max_primary_score', 'total_tasks', 'order',
            'exam_type_code', 'exam_type_name', 'sections',
        ]


class SubjectBriefSerializer(serializers.ModelSerializer):
    """Для списков без вложенных секций."""
    exam_type_code = serializers.CharField(source='exam_type.code', read_only=True)
    exam_type_name = serializers.CharField(source='exam_type.name', read_only=True)

    class Meta:
        model = Subject
        fields = [
            'id', 'code', 'name', 'icon', 'color',
            'max_primary_score', 'total_tasks', 'order',
            'exam_type_code', 'exam_type_name',
        ]


class StudentExamAssignmentSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    exam_type = serializers.CharField(source='subject.exam_type.code', read_only=True)
    student_name = serializers.SerializerMethodField()

    class Meta:
        model = StudentExamAssignment
        fields = [
            'id', 'student', 'subject', 'subject_name',
            'exam_type', 'assigned_at', 'student_name',
        ]
        read_only_fields = ['assigned_at']

    def get_student_name(self, obj):
        u = obj.student
        return f'{u.last_name} {u.first_name}'.strip() or u.email


class TopicMasterySerializer(serializers.ModelSerializer):
    topic_name = serializers.CharField(source='topic.name', read_only=True)
    topic_code = serializers.CharField(source='topic.code', read_only=True)
    task_number = serializers.IntegerField(source='topic.task_number', read_only=True)
    difficulty = serializers.CharField(source='topic.difficulty', read_only=True)
    section_name = serializers.CharField(source='topic.section.name', read_only=True)
    trend_display = serializers.CharField(source='get_trend_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    success_rate = serializers.FloatField(read_only=True)
    avg_score_percent = serializers.FloatField(read_only=True)

    class Meta:
        model = StudentTopicMastery
        fields = [
            'id', 'topic', 'topic_name', 'topic_code', 'task_number',
            'difficulty', 'section_name',
            'mastery_level', 'stability', 'trend', 'trend_display',
            'status', 'status_display',
            'attempted_count', 'success_count', 'success_rate',
            'avg_score_percent', 'avg_time_seconds',
            'last_scores', 'first_attempt_at', 'last_attempt_at',
        ]


class StudentKnowledgeMapSerializer(serializers.Serializer):
    """
    Полная карта знаний ученика по предмету.
    Дерево: sections → topics → mastery.
    """
    subject = SubjectBriefSerializer()
    sections = serializers.SerializerMethodField()
    overall_mastery = serializers.FloatField()
    overall_stability = serializers.FloatField()
    topics_mastered = serializers.IntegerField()
    topics_total = serializers.IntegerField()
    topics_in_progress = serializers.IntegerField()
    topics_needs_review = serializers.IntegerField()

    def get_sections(self, obj):
        return obj.get('sections_data', [])


class GroupKnowledgeMapSerializer(serializers.Serializer):
    """Агрегированная карта знаний группы по предмету."""
    subject = SubjectBriefSerializer()
    students = serializers.ListField()
    sections = serializers.ListField()
    overall_mastery = serializers.FloatField()
