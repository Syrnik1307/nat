from rest_framework import serializers
from .models import Homework, Question, Choice, StudentSubmission, Answer
from accounts.models import CustomUser


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'text', 'is_correct']
        extra_kwargs = {'is_correct': {'write_only': True}}


class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, required=False)

    class Meta:
        model = Question
        fields = ['id', 'prompt', 'question_type', 'points', 'order', 'choices']

    def create(self, validated_data):
        choices_data = validated_data.pop('choices', [])
        question = Question.objects.create(**validated_data)
        for c in choices_data:
            Choice.objects.create(question=question, **c)
        return question

    def update(self, instance, validated_data):
        choices_data = validated_data.pop('choices', None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        if choices_data is not None:
            instance.choices.all().delete()
            for c in choices_data:
                Choice.objects.create(question=instance, **c)
        return instance


class HomeworkSerializer(serializers.ModelSerializer):
    teacher_email = serializers.EmailField(source='teacher.email', read_only=True)
    questions = QuestionSerializer(many=True, required=False)

    class Meta:
        model = Homework
        fields = ['id', 'title', 'description', 'teacher', 'teacher_email', 'lesson', 'questions', 'created_at', 'updated_at']
        read_only_fields = ['teacher']

    def create(self, validated_data):
        questions_data = validated_data.pop('questions', [])
        validated_data['teacher'] = self.context['request'].user
        homework = Homework.objects.create(**validated_data)
        for q in questions_data:
            choices = q.pop('choices', [])
            question = Question.objects.create(homework=homework, **q)
            for c in choices:
                Choice.objects.create(question=question, **c)
        return homework


class AnswerSerializer(serializers.ModelSerializer):
    selected_choices = serializers.PrimaryKeyRelatedField(queryset=Choice.objects.all(), many=True, required=False)
    question_text = serializers.CharField(source='question.prompt', read_only=True)
    question_type = serializers.CharField(source='question.question_type', read_only=True)
    question_points = serializers.IntegerField(source='question.points', read_only=True)
    
    class Meta:
        model = Answer
        fields = ['id', 'question', 'question_text', 'question_type', 'question_points', 
                  'text_answer', 'selected_choices', 'auto_score', 'teacher_score', 
                  'teacher_feedback', 'needs_manual_review']
        read_only_fields = ['auto_score', 'needs_manual_review']


class StudentSubmissionSerializer(serializers.ModelSerializer):
    answers = AnswerSerializer(many=True, required=False)
    student_email = serializers.EmailField(source='student.email', read_only=True)
    student_name = serializers.SerializerMethodField()
    homework_title = serializers.CharField(source='homework.title', read_only=True)

    class Meta:
        model = StudentSubmission
        fields = ['id', 'homework', 'homework_title', 'student', 'student_email', 'student_name',
                  'status', 'total_score', 'answers', 'created_at', 'submitted_at', 'graded_at']
        read_only_fields = ['student', 'total_score']
    
    def get_student_name(self, obj):
        return f"{obj.student.first_name} {obj.student.last_name}".strip() or obj.student.email

    def create(self, validated_data):
        answers_data = validated_data.pop('answers', [])
        validated_data['student'] = self.context['request'].user
        submission = StudentSubmission.objects.create(**validated_data)
        for ans in answers_data:
            selected_choices = ans.pop('selected_choices', [])
            answer = Answer.objects.create(submission=submission, **ans)
            if selected_choices:
                answer.selected_choices.set(selected_choices)
            answer.evaluate()
        submission.compute_auto_score()
        return submission
