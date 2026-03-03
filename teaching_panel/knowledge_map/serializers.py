from rest_framework import serializers
from .models import ExamType, Subject, Topic, ExamAssignment, StudentTopicScore


class TopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = ['id', 'number', 'title', 'max_points', 'description', 'order']


class SubjectListSerializer(serializers.ModelSerializer):
    exam_type_name = serializers.CharField(source='exam_type.name', read_only=True)
    topics_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Subject
        fields = ['id', 'name', 'slug', 'icon', 'order', 'exam_type', 'exam_type_name', 'topics_count']


class SubjectDetailSerializer(serializers.ModelSerializer):
    exam_type_name = serializers.CharField(source='exam_type.name', read_only=True)
    topics = TopicSerializer(many=True, read_only=True)

    class Meta:
        model = Subject
        fields = ['id', 'name', 'slug', 'icon', 'order', 'exam_type', 'exam_type_name', 'topics']


class ExamTypeSerializer(serializers.ModelSerializer):
    subjects_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ExamType
        fields = ['id', 'slug', 'name', 'description', 'is_preset', 'subjects_count']


class ExamAssignmentSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    exam_type_name = serializers.CharField(source='subject.exam_type.name', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True, default=None)
    student_email = serializers.CharField(source='student.email', read_only=True, default=None)

    class Meta:
        model = ExamAssignment
        fields = [
            'id', 'subject', 'subject_name', 'exam_type_name',
            'group', 'group_name', 'student', 'student_email', 'created_at',
        ]
        read_only_fields = ['teacher']


class StudentTopicScoreSerializer(serializers.ModelSerializer):
    topic_number = serializers.IntegerField(source='topic.number', read_only=True)
    topic_title = serializers.CharField(source='topic.title', read_only=True)
    topic_max_points = serializers.IntegerField(source='topic.max_points', read_only=True)

    class Meta:
        model = StudentTopicScore
        fields = [
            'id', 'topic', 'topic_number', 'topic_title', 'topic_max_points',
            'score_percent', 'attempts_count', 'trend',
            'total_points_earned', 'total_points_possible',
            'last_attempt_at', 'updated_at',
        ]


class StudentProgressSerializer(serializers.Serializer):
    """Radar-ready формат прогресса ученика по предмету."""
    subject = SubjectDetailSerializer()
    scores = StudentTopicScoreSerializer(many=True)
    overall_percent = serializers.FloatField()
    total_attempts = serializers.IntegerField()


class StudentSummaryItemSerializer(serializers.Serializer):
    """Одна запись в сводке по всем предметам."""
    subject_id = serializers.IntegerField()
    subject_name = serializers.CharField()
    exam_type_name = serializers.CharField()
    icon = serializers.CharField()
    overall_percent = serializers.FloatField()
    topics_count = serializers.IntegerField()
    topics_with_data = serializers.IntegerField()
    total_attempts = serializers.IntegerField()
