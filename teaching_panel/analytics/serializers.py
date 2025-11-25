from rest_framework import serializers
from .models import ControlPoint, ControlPointResult

class ControlPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = ControlPoint
        fields = ['id', 'title', 'teacher', 'group', 'lesson', 'max_points', 'date', 'created_at']

class ControlPointResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = ControlPointResult
        fields = ['id', 'control_point', 'student', 'points', 'created_at']
