from rest_framework import serializers
from schedule.models import LessonTranscriptStats

class LessonTranscriptStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonTranscriptStats
        fields = ['id', 'stats_json', 'created_at']
