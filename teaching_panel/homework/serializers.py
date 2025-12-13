import copy
from rest_framework import serializers
from .models import Homework, Question, Choice, StudentSubmission, Answer
from accounts.models import CustomUser


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'text', 'is_correct']
        # Ученикам нельзя видеть правильность вариантов. write_only
        # позволяет передавать is_correct при создании/редактировании (для учителей),
        # но не возвращать в ответах API.
        extra_kwargs = {'is_correct': {'write_only': True}}


class ChoiceStudentSerializer(serializers.ModelSerializer):
    """Упрощенный сериализатор для учеников (без is_correct)."""
    class Meta:
        model = Choice
        fields = ['id', 'text']


def sanitize_question_config(question: Question):
    """Remove teacher-only hints before returning config to ученикам."""
    raw_config = question.config or {}
    if not isinstance(raw_config, dict):
        return {}

    config = copy.deepcopy(raw_config)
    q_type = question.question_type

    if q_type == 'TEXT':
        config.pop('correctAnswer', None)
    elif q_type == 'SINGLE_CHOICE':
        config.pop('correctOptionId', None)
    elif q_type == 'MULTI_CHOICE':
        config.pop('correctOptionIds', None)
    elif q_type == 'LISTENING':
        sub_questions = config.get('subQuestions') or []
        if isinstance(sub_questions, list):
            for item in sub_questions:
                if isinstance(item, dict):
                    item.pop('answer', None)
    elif q_type == 'DRAG_DROP':
        config.pop('correctOrder', None)
    elif q_type == 'FILL_BLANKS':
        answers = config.get('answers')
        if isinstance(answers, list):
            config['answers'] = ['' for _ in answers]
    elif q_type == 'HOTSPOT':
        hotspots = config.get('hotspots') or []
        if isinstance(hotspots, list):
            for hotspot in hotspots:
                if isinstance(hotspot, dict):
                    hotspot.pop('isCorrect', None)

    return config


class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, required=False)
    config = serializers.JSONField(required=False)

    class Meta:
        model = Question
        fields = ['id', 'prompt', 'question_type', 'points', 'order', 'choices', 'config']
        extra_kwargs = {
            'config': {'default': dict},
        }

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


class QuestionStudentSerializer(serializers.ModelSerializer):
    """Ученический сериализатор вопроса: без баллов и, конечно, без is_correct."""
    choices = ChoiceStudentSerializer(many=True, read_only=True)
    question_type = serializers.SerializerMethodField()
    config = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = ['id', 'prompt', 'question_type', 'order', 'choices', 'config']

    def get_question_type(self, obj):
        # Возвращаем фронтовое именование для multi choice
        return 'MULTIPLE_CHOICE' if obj.question_type == 'MULTI_CHOICE' else obj.question_type

    def get_config(self, obj):
        return sanitize_question_config(obj)


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


class HomeworkStudentSerializer(serializers.ModelSerializer):
    """Чтение ДЗ учениками: без баллов и без флагов правильности."""
    teacher_email = serializers.EmailField(source='teacher.email', read_only=True)
    questions = QuestionStudentSerializer(many=True, read_only=True)

    class Meta:
        model = Homework
        fields = ['id', 'title', 'description', 'teacher', 'teacher_email', 'lesson', 'questions', 'created_at']
        read_only_fields = fields


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
    max_score = serializers.SerializerMethodField()
    group_id = serializers.SerializerMethodField()
    group_name = serializers.SerializerMethodField()
    is_individual = serializers.SerializerMethodField()

    class Meta:
        model = StudentSubmission
        fields = ['id', 'homework', 'homework_title', 'student', 'student_email', 'student_name',
              'status', 'total_score', 'max_score', 'group_id', 'group_name', 'is_individual',
              'answers', 'teacher_feedback_summary', 'created_at', 'submitted_at', 'graded_at']
        # Статус и даты жизненного цикла управляются сервером через отдельные endpoints
        # (answer/saveProgress, submit, feedback) и не должны приходить от клиента.
        read_only_fields = [
            'id',
            'student',
            'status',
            'total_score',
            'teacher_feedback_summary',
            'created_at',
            'submitted_at',
            'graded_at',
        ]
    
    def get_student_name(self, obj):
        return f"{obj.student.first_name} {obj.student.last_name}".strip() or obj.student.email
    
    def get_max_score(self, obj):
        """Вычисляем максимальный балл для домашки"""
        return sum(q.points for q in obj.homework.questions.all())
    
    def get_group_id(self, obj):
        """Получаем ID группы: урок → группа студента у этого преподавателя → None"""
        if obj.homework.lesson and getattr(obj.homework.lesson, 'group', None):
            return obj.homework.lesson.group.id

        # Fallback: если у студента есть группы у этого преподавателя, берем первую
        teacher = getattr(obj.homework, 'teacher', None)
        if teacher and hasattr(obj.student, 'enrolled_groups'):
            group = obj.student.enrolled_groups.filter(teacher=teacher).first()
            if group:
                return group.id

        return None

    def get_group_name(self, obj):
        if obj.homework.lesson and getattr(obj.homework.lesson, 'group', None):
            return obj.homework.lesson.group.name

        teacher = getattr(obj.homework, 'teacher', None)
        if teacher and hasattr(obj.student, 'enrolled_groups'):
            group = obj.student.enrolled_groups.filter(teacher=teacher).first()
            if group:
                return group.name

        return 'Индивидуальные'

    def get_is_individual(self, obj):
        if obj.homework.lesson and getattr(obj.homework.lesson, 'group', None):
            return False

        teacher = getattr(obj.homework, 'teacher', None)
        if teacher and hasattr(obj.student, 'enrolled_groups'):
            group = obj.student.enrolled_groups.filter(teacher=teacher).first()
            if group:
                return False

        return True

    def create(self, validated_data):
        answers_data = validated_data.pop('answers', [])
        validated_data['student'] = self.context['request'].user
        # Защита от ситуации, когда клиент (или баг фронта) пытается проставить
        # статус/даты сдачи при создании попытки.
        validated_data.pop('status', None)
        validated_data.pop('submitted_at', None)
        validated_data.pop('graded_at', None)

        # Создаем попытку в статусе "в процессе", без автоматической сдачи.
        # Важно: kwargs после **validated_data должны побеждать любые значения.
        submission = StudentSubmission.objects.create(
            **validated_data,
            status='in_progress',
            submitted_at=None,
            graded_at=None,
        )
        if answers_data:
            for ans in answers_data:
                selected_choices = ans.pop('selected_choices', [])
                answer = Answer.objects.create(submission=submission, **ans)
                if selected_choices:
                    answer.selected_choices.set(selected_choices)
                answer.evaluate()
            submission.compute_auto_score()
        return submission
