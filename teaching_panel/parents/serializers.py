from rest_framework import serializers
from .models import ParentAccess, ParentAccessGrant, ParentComment


class ParentCommentSerializer(serializers.ModelSerializer):
    teacher_name = serializers.SerializerMethodField()

    class Meta:
        model = ParentComment
        fields = ['id', 'text', 'teacher_name', 'created_at']
        read_only_fields = ['id', 'teacher_name', 'created_at']

    def get_teacher_name(self, obj):
        return obj.teacher.get_full_name()


class ParentCommentCreateSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=2000)


class ParentAccessGrantSerializer(serializers.ModelSerializer):
    teacher_name = serializers.SerializerMethodField()
    group_name = serializers.CharField(source='group.name', read_only=True)
    comments = ParentCommentSerializer(many=True, read_only=True)

    class Meta:
        model = ParentAccessGrant
        fields = [
            'id', 'subject_label', 'teacher_name', 'group_name', 'group',
            'show_attendance', 'show_homework', 'show_grades',
            'show_knowledge_map', 'show_finance',
            'is_active', 'created_at', 'comments',
        ]
        read_only_fields = ['id', 'teacher_name', 'group_name', 'is_active', 'created_at', 'comments']

    def get_teacher_name(self, obj):
        return obj.teacher.get_full_name()


class ParentAccessSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    link = serializers.SerializerMethodField()
    grants = ParentAccessGrantSerializer(many=True, read_only=True)

    class Meta:
        model = ParentAccess
        fields = [
            'id', 'token', 'student_name', 'link',
            'parent_name', 'parent_contact',
            'telegram_connected', 'is_active',
            'view_count', 'last_viewed_at', 'created_at',
            'grants',
        ]
        read_only_fields = [
            'id', 'token', 'student_name', 'link',
            'telegram_connected', 'is_active',
            'view_count', 'last_viewed_at', 'created_at',
            'grants',
        ]

    def get_student_name(self, obj):
        return obj.student.get_full_name()

    def get_link(self, obj):
        request = self.context.get('request')
        if request:
            scheme = request.scheme
            host = request.get_host()
            return f"{scheme}://{host}/p/{obj.token}"
        return f"/p/{obj.token}"


class CreateParentAccessSerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    group_id = serializers.IntegerField()
    subject_label = serializers.CharField(max_length=200)
    parent_name = serializers.CharField(max_length=200, required=False, default='')
    parent_contact = serializers.CharField(max_length=200, required=False, default='')


class UpdateGrantSerializer(serializers.Serializer):
    subject_label = serializers.CharField(max_length=200, required=False)
    show_attendance = serializers.BooleanField(required=False)
    show_homework = serializers.BooleanField(required=False)
    show_grades = serializers.BooleanField(required=False)
    show_knowledge_map = serializers.BooleanField(required=False)
    show_finance = serializers.BooleanField(required=False)


# === Dashboard (для родителя, без auth) ===

class DashboardHomeworkItemSerializer(serializers.Serializer):
    title = serializers.CharField()
    assigned_date = serializers.DateField()
    deadline = serializers.DateTimeField(allow_null=True)
    submitted_date = serializers.DateTimeField(allow_null=True)
    score = serializers.FloatField(allow_null=True)
    max_score = serializers.FloatField(allow_null=True)
    status = serializers.CharField()  # done, overdue, pending, not_submitted


class DashboardControlPointSerializer(serializers.Serializer):
    title = serializers.CharField()
    date = serializers.DateField()
    points = serializers.IntegerField()
    max_points = serializers.IntegerField()


class DashboardChartPointSerializer(serializers.Serializer):
    month = serializers.CharField()
    avg_score = serializers.FloatField()
    done_pct = serializers.FloatField()


class DashboardSubjectSerializer(serializers.Serializer):
    grant_id = serializers.IntegerField()
    subject_label = serializers.CharField()
    teacher_name = serializers.CharField()

    # Summary cards
    total_lessons = serializers.IntegerField()
    attended_lessons = serializers.IntegerField()
    attendance_pct = serializers.FloatField()
    hw_total = serializers.IntegerField()
    hw_done = serializers.IntegerField()
    hw_avg_score = serializers.FloatField(allow_null=True)

    # Detailed data
    homework_list = DashboardHomeworkItemSerializer(many=True)
    control_points = DashboardControlPointSerializer(many=True)
    hw_chart_data = DashboardChartPointSerializer(many=True)

    # Teacher comments
    comments = ParentCommentSerializer(many=True)

    # Stubs
    knowledge_map = serializers.DictField(allow_null=True)
    finance = serializers.DictField(allow_null=True)


class ParentDashboardSerializer(serializers.Serializer):
    student_name = serializers.CharField()
    last_viewed_at = serializers.DateTimeField(allow_null=True)
    telegram_connected = serializers.BooleanField()
    telegram_bot_link = serializers.CharField()
    subjects = DashboardSubjectSerializer(many=True)
