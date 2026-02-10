"""
Сериализаторы модуля экзаменов.
"""

from rest_framework import serializers
from .models import (
    ExamBlueprint, ExamTaskSlot, ExamTask,
    ExamVariant, ExamVariantTask, ExamAttempt,
)


# ============================================================
# ExamBlueprint
# ============================================================

class ExamTaskSlotSerializer(serializers.ModelSerializer):
    """Слот задания (вложен в Blueprint)."""
    topic_name = serializers.CharField(source='topic.name', read_only=True, default='')
    
    class Meta:
        model = ExamTaskSlot
        fields = [
            'id', 'task_number', 'title', 'answer_type', 'max_points',
            'topic', 'topic_name', 'answer_config', 'description', 'order',
        ]
        read_only_fields = ['id']


class ExamBlueprintListSerializer(serializers.ModelSerializer):
    """Краткий сериализатор для списка шаблонов."""
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    exam_type = serializers.CharField(source='subject.exam_type.code', read_only=True)
    task_slots_count = serializers.IntegerField(source='task_slots.count', read_only=True)
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ExamBlueprint
        fields = [
            'id', 'title', 'subject', 'subject_name', 'exam_type',
            'year', 'duration_minutes', 'total_primary_score',
            'task_slots_count', 'is_active', 'is_public',
            'created_by', 'created_by_name', 'created_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_at']

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.email
        return ''


class ExamBlueprintDetailSerializer(serializers.ModelSerializer):
    """Полный сериализатор с вложенными слотами."""
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    exam_type = serializers.CharField(source='subject.exam_type.code', read_only=True)
    task_slots = ExamTaskSlotSerializer(many=True, read_only=True)
    created_by_name = serializers.SerializerMethodField()
    variants_count = serializers.IntegerField(source='variants.count', read_only=True)
    
    class Meta:
        model = ExamBlueprint
        fields = [
            'id', 'title', 'subject', 'subject_name', 'exam_type',
            'year', 'duration_minutes', 'total_primary_score',
            'score_scale', 'grade_thresholds', 'description',
            'is_active', 'is_public',
            'task_slots', 'variants_count',
            'created_by', 'created_by_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.email
        return ''


class ExamBlueprintCreateSerializer(serializers.ModelSerializer):
    """Создание/обновление шаблона с вложенными слотами."""
    task_slots = ExamTaskSlotSerializer(many=True, required=False)
    
    class Meta:
        model = ExamBlueprint
        fields = [
            'id', 'title', 'subject', 'year',
            'duration_minutes', 'total_primary_score',
            'score_scale', 'grade_thresholds', 'description',
            'is_active', 'is_public', 'task_slots',
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        slots_data = validated_data.pop('task_slots', [])
        blueprint = ExamBlueprint.objects.create(**validated_data)
        for slot_data in slots_data:
            ExamTaskSlot.objects.create(blueprint=blueprint, **slot_data)
        blueprint.recalculate_total_score()
        return blueprint

    def update(self, instance, validated_data):
        slots_data = validated_data.pop('task_slots', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if slots_data is not None:
            # Удаляем старые слоты и создаём новые
            instance.task_slots.all().delete()
            for slot_data in slots_data:
                ExamTaskSlot.objects.create(blueprint=instance, **slot_data)
            instance.recalculate_total_score()
        
        return instance


# ============================================================
# ExamTask (банк заданий)
# ============================================================

class ExamTaskListSerializer(serializers.ModelSerializer):
    """Краткий сериализатор задания из банка."""
    question_prompt = serializers.CharField(source='question.prompt', read_only=True)
    question_type = serializers.CharField(source='question.question_type', read_only=True)
    question_points = serializers.IntegerField(source='question.points', read_only=True)
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ExamTask
        fields = [
            'id', 'blueprint', 'task_number',
            'question', 'question_prompt', 'question_type', 'question_points',
            'difficulty', 'source', 'source_reference',
            'tags', 'usage_count', 'is_active',
            'created_by', 'created_by_name', 'created_at',
        ]
        read_only_fields = ['id', 'usage_count', 'created_by', 'created_at']

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.email
        return ''


class ExamTaskDetailSerializer(serializers.ModelSerializer):
    """Полный сериализатор с вложенным вопросом."""
    question_data = serializers.SerializerMethodField()
    
    class Meta:
        model = ExamTask
        fields = [
            'id', 'blueprint', 'task_number',
            'question', 'question_data',
            'difficulty', 'source', 'source_reference',
            'tags', 'usage_count', 'is_active',
            'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'usage_count', 'created_by', 'created_at', 'updated_at']

    def get_question_data(self, obj):
        """Вернуть полные данные вопроса включая choices."""
        q = obj.question
        choices = [
            {'id': c.id, 'text': c.text, 'is_correct': c.is_correct}
            for c in q.choices.all()
        ]
        return {
            'id': q.id,
            'prompt': q.prompt,
            'question_type': q.question_type,
            'points': q.points,
            'config': q.config,
            'explanation': q.explanation,
            'choices': choices,
        }


class ExamTaskCreateSerializer(serializers.ModelSerializer):
    """
    Создание задания в банк.
    
    Принимает данные вопроса inline (prompt, question_type, config, choices)
    и создаёт Question + ExamTask в одной транзакции.
    """
    # Inline question fields
    prompt = serializers.CharField(write_only=True)
    question_type = serializers.CharField(write_only=True)
    points = serializers.IntegerField(write_only=True, default=1)
    config = serializers.JSONField(write_only=True, required=False, default=dict)
    explanation = serializers.CharField(write_only=True, required=False, default='')
    choices = serializers.ListField(
        child=serializers.DictField(), write_only=True, required=False, default=list
    )
    
    class Meta:
        model = ExamTask
        fields = [
            'id', 'blueprint', 'task_number',
            'difficulty', 'source', 'source_reference',
            'tags', 'is_active',
            # Inline question fields
            'prompt', 'question_type', 'points', 'config',
            'explanation', 'choices',
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        from homework.models import Question, Choice, Homework
        
        # Извлекаем данные вопроса
        prompt = validated_data.pop('prompt')
        question_type = validated_data.pop('question_type')
        points = validated_data.pop('points', 1)
        config = validated_data.pop('config', {})
        explanation = validated_data.pop('explanation', '')
        choices_data = validated_data.pop('choices', [])
        
        blueprint = validated_data['blueprint']
        
        # Создаём или находим системное ДЗ-контейнер для банка заданий
        bank_homework, _ = Homework.objects.get_or_create(
            title=f'__exam_bank__{blueprint.id}',
            teacher=blueprint.created_by,
            defaults={
                'status': 'draft',
                'description': f'Системный контейнер для банка заданий: {blueprint.title}',
                'school': blueprint.school,
            }
        )
        
        # Создаём Question
        question = Question.objects.create(
            homework=bank_homework,
            prompt=prompt,
            question_type=question_type,
            points=points,
            config=config,
            explanation=explanation,
            order=0,
        )
        
        # Создаём choices
        for choice_data in choices_data:
            Choice.objects.create(
                question=question,
                text=choice_data.get('text', ''),
                is_correct=choice_data.get('is_correct', False),
            )
        
        # Создаём ExamTask
        exam_task = ExamTask.objects.create(
            question=question,
            **validated_data,
        )
        
        return exam_task


# ============================================================
# ExamVariant
# ============================================================

class ExamVariantTaskSerializer(serializers.ModelSerializer):
    """Задание в варианте."""
    task_detail = ExamTaskListSerializer(source='task', read_only=True)
    
    class Meta:
        model = ExamVariantTask
        fields = ['id', 'task', 'task_detail', 'task_number', 'order']
        read_only_fields = ['id']


class ExamVariantListSerializer(serializers.ModelSerializer):
    """Краткий сериализатор варианта."""
    blueprint_title = serializers.CharField(source='blueprint.title', read_only=True)
    task_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = ExamVariant
        fields = [
            'id', 'blueprint', 'blueprint_title',
            'variant_number', 'title', 'is_manual',
            'task_count', 'homework',
            'created_by', 'created_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_at']


class ExamVariantDetailSerializer(serializers.ModelSerializer):
    """Полный сериализатор варианта с заданиями."""
    blueprint_title = serializers.CharField(source='blueprint.title', read_only=True)
    variant_tasks = ExamVariantTaskSerializer(many=True, read_only=True)
    duration_minutes = serializers.IntegerField(source='blueprint.duration_minutes', read_only=True)
    total_primary_score = serializers.IntegerField(source='blueprint.total_primary_score', read_only=True)
    
    class Meta:
        model = ExamVariant
        fields = [
            'id', 'blueprint', 'blueprint_title',
            'variant_number', 'title', 'is_manual',
            'variant_tasks', 'homework',
            'duration_minutes', 'total_primary_score',
            'created_by', 'created_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_at']


class ExamVariantManualCreateSerializer(serializers.Serializer):
    """Ручная сборка варианта из конкретных заданий."""
    blueprint_id = serializers.IntegerField()
    title = serializers.CharField(required=False, default='')
    # Список пар {task_number, task_id}
    tasks = serializers.ListField(
        child=serializers.DictField(),
        help_text='[{"task_number": 1, "task_id": 42}, ...]'
    )


class ExamVariantGenerateSerializer(serializers.Serializer):
    """Автоматическая генерация варианта."""
    blueprint_id = serializers.IntegerField()
    count = serializers.IntegerField(default=1, min_value=1, max_value=10)
    exclude_task_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False, default=list,
        help_text='ID заданий для исключения (уже использованные)'
    )
    difficulty_balance = serializers.ChoiceField(
        choices=['random', 'balanced', 'easy', 'hard'],
        default='balanced',
        help_text='Баланс сложности'
    )


class ExamVariantAssignSerializer(serializers.Serializer):
    """Назначить вариант группе (создаёт Homework)."""
    group_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text='ID групп для назначения'
    )
    deadline = serializers.DateTimeField(required=False, allow_null=True)
    student_instructions = serializers.CharField(required=False, default='')


# ============================================================
# ExamAttempt
# ============================================================

class ExamAttemptSerializer(serializers.ModelSerializer):
    """Попытка экзамена (для ученика)."""
    student_name = serializers.SerializerMethodField()
    variant_title = serializers.CharField(source='variant.title', read_only=True)
    blueprint_title = serializers.CharField(source='variant.blueprint.title', read_only=True)
    time_remaining_seconds = serializers.SerializerMethodField()
    
    class Meta:
        model = ExamAttempt
        fields = [
            'id', 'submission', 'variant', 'variant_title', 'blueprint_title',
            'started_at', 'deadline_at', 'auto_submitted',
            'primary_score', 'test_score', 'grade',
            'task_scores', 'time_spent_seconds', 'fullscreen_exits',
            'time_remaining_seconds', 'student_name',
        ]
        read_only_fields = [
            'id', 'started_at', 'deadline_at', 'auto_submitted',
            'primary_score', 'test_score', 'grade', 'task_scores',
        ]

    def get_student_name(self, obj):
        student = obj.submission.student
        return student.get_full_name() or student.email

    def get_time_remaining_seconds(self, obj):
        if not obj.deadline_at:
            return None
        from django.utils import timezone
        remaining = (obj.deadline_at - timezone.now()).total_seconds()
        return max(0, int(remaining))


class ExamAttemptResultSerializer(serializers.ModelSerializer):
    """Детальный результат экзамена."""
    student_name = serializers.SerializerMethodField()
    variant_title = serializers.CharField(source='variant.title', read_only=True)
    blueprint_title = serializers.CharField(source='variant.blueprint.title', read_only=True)
    max_primary_score = serializers.IntegerField(
        source='variant.blueprint.total_primary_score', read_only=True
    )
    score_scale = serializers.JSONField(
        source='variant.blueprint.score_scale', read_only=True
    )
    
    class Meta:
        model = ExamAttempt
        fields = [
            'id', 'submission', 'variant', 'variant_title', 'blueprint_title',
            'started_at', 'deadline_at', 'auto_submitted',
            'primary_score', 'test_score', 'grade',
            'max_primary_score', 'score_scale',
            'task_scores', 'time_spent_seconds', 'fullscreen_exits',
            'student_name',
        ]

    def get_student_name(self, obj):
        student = obj.submission.student
        return student.get_full_name() or student.email
