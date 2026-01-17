import copy
from rest_framework import serializers
from .models import Homework, Question, Choice, StudentSubmission, Answer
from accounts.models import CustomUser
from django.conf import settings


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

    # Backward/forward compat: если фронт хранит только fileId, а url отсутствует — добавим.
    # Это нужно для шаблонов/копирования вложений на Google Drive.
    try:
        if getattr(settings, 'USE_GDRIVE_STORAGE', False):
            image_file_id = config.get('imageFileId')
            if image_file_id and not config.get('imageUrl'):
                config['imageUrl'] = f"https://drive.google.com/uc?export=download&id={image_file_id}"
            audio_file_id = config.get('audioFileId')
            if audio_file_id and not config.get('audioUrl'):
                config['audioUrl'] = f"https://drive.google.com/uc?export=download&id={audio_file_id}"
    except Exception:
        # Не должны ломать выдачу ДЗ ученикам из-за вспомогательной логики
        pass

    if q_type == 'TEXT':
        config.pop('correctAnswer', None)
    elif q_type == 'SINGLE_CHOICE':
        config.pop('correctOptionId', None)
        # Remove options from config - they're provided in choices field with real DB IDs
        config.pop('options', None)
    elif q_type == 'MULTI_CHOICE':
        config.pop('correctOptionIds', None)
        # Remove options from config - they're provided in choices field with real DB IDs
        config.pop('options', None)
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
            'prompt': {'required': False, 'allow_blank': True, 'default': ''},
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
    """Ученический сериализатор вопроса: без is_correct (но с баллами)."""
    choices = ChoiceStudentSerializer(many=True, read_only=True)
    question_type = serializers.SerializerMethodField()
    config = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = ['id', 'prompt', 'question_type', 'points', 'order', 'choices', 'config']

    def get_question_type(self, obj):
        # Возвращаем фронтовое именование для multi choice
        return 'MULTIPLE_CHOICE' if obj.question_type == 'MULTI_CHOICE' else obj.question_type

    def get_config(self, obj):
        return sanitize_question_config(obj)


class HomeworkSerializer(serializers.ModelSerializer):
    teacher_email = serializers.EmailField(source='teacher.email', read_only=True)
    questions = QuestionSerializer(many=True, required=False)
    assigned_group_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    assigned_student_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    # Новый формат: группы с конкретными учениками
    group_assignments_data = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False,
        help_text='[{"group_id": 1, "student_ids": [5, 7], "deadline": "..."}, ...]'
    )
    group_id = serializers.SerializerMethodField(read_only=True)
    group_name = serializers.SerializerMethodField(read_only=True)
    questions_count = serializers.SerializerMethodField(read_only=True)
    submissions_count = serializers.SerializerMethodField(read_only=True)
    assigned_groups = serializers.SerializerMethodField(read_only=True)
    group_assignments = serializers.SerializerMethodField(read_only=True)
    assigned_students = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Homework
        fields = [
            'id', 'title', 'description', 'teacher', 'teacher_email', 'lesson', 
            'questions', 'created_at', 'updated_at',
            'status', 'deadline', 'published_at', 'max_score',
            'is_template', 'gdrive_folder_id',
            'assigned_group_ids', 'assigned_student_ids', 'group_assignments_data',
            'group_id', 'group_name',
            'questions_count', 'submissions_count', 'assigned_groups',
            'group_assignments', 'assigned_students',
            # AI grading fields
            'ai_grading_enabled', 'ai_provider', 'ai_grading_prompt',
            # Student-facing settings
            'student_instructions', 'allow_view_answers',
        ]
        read_only_fields = ['teacher']

    def get_questions_count(self, obj):
        return obj.questions.count()

    def get_submissions_count(self, obj):
        return obj.submissions.count()

    def get_assigned_groups(self, obj):
        """Возвращает список групп для переназначения (обратная совместимость)."""
        return [{'id': g.id, 'name': g.name} for g in obj.assigned_groups.all()]

    def get_group_assignments(self, obj):
        """Возвращает детальную информацию о назначениях групп с учениками."""
        from .models import HomeworkGroupAssignment
        
        result = []
        # Сначала собираем назначения через новую модель
        ga_group_ids = set()
        for ga in obj.group_assignments.select_related('group').prefetch_related('students'):
            ga_group_ids.add(ga.group_id)
            students = list(ga.students.values('id', 'email', 'first_name', 'last_name'))
            result.append({
                'group_id': ga.group.id,
                'group_name': ga.group.name,
                'student_ids': [s['id'] for s in students],
                'students': students,
                'all_students': len(students) == 0,
                'deadline': ga.deadline.isoformat() if ga.deadline else None,
            })
        
        # Добавляем группы через старый механизм (assigned_groups) без HomeworkGroupAssignment
        for group in obj.assigned_groups.all():
            if group.id not in ga_group_ids:
                result.append({
                    'group_id': group.id,
                    'group_name': group.name,
                    'student_ids': [],
                    'students': [],
                    'all_students': True,
                    'deadline': None,
                })
        
        return result

    def get_assigned_students(self, obj):
        """Возвращает список индивидуально назначенных учеников."""
        return list(obj.assigned_students.values('id', 'email', 'first_name', 'last_name'))

    def get_group_id(self, obj: Homework):
        # Для совместимости со старым UI: если назначено ровно на 1 группу — возвращаем её.
        try:
            group_ids = list(obj.assigned_groups.values_list('id', flat=True)[:2])
            if len(group_ids) == 1:
                return group_ids[0]
        except Exception:
            pass
        if obj.lesson and getattr(obj.lesson, 'group', None):
            return obj.lesson.group.id
        return None

    def get_group_name(self, obj: Homework):
        try:
            groups = list(obj.assigned_groups.all()[:2])
            if len(groups) == 1:
                return groups[0].name
            if len(groups) > 1:
                return 'Несколько групп'
        except Exception:
            pass
        if obj.lesson and getattr(obj.lesson, 'group', None):
            return obj.lesson.group.name
        return 'Без группы'

    def _process_group_assignments(self, homework, group_assignments_data):
        """Обработка назначений групп с конкретными учениками."""
        from .models import HomeworkGroupAssignment
        from django.utils.dateparse import parse_datetime
        
        # Удаляем старые назначения
        homework.group_assignments.all().delete()
        
        for ga_data in group_assignments_data:
            group_id = ga_data.get('group_id')
            student_ids = ga_data.get('student_ids', [])
            deadline = ga_data.get('deadline')
            
            if not group_id:
                continue
            
            parsed_deadline = parse_datetime(deadline) if deadline else None
            
            assignment = HomeworkGroupAssignment.objects.create(
                homework=homework,
                group_id=group_id,
                deadline=parsed_deadline
            )
            if student_ids:
                assignment.students.set(student_ids)
            
            # Для обратной совместимости также добавляем в assigned_groups
            homework.assigned_groups.add(group_id)

    def create(self, validated_data):
        assigned_group_ids = validated_data.pop('assigned_group_ids', [])
        assigned_student_ids = validated_data.pop('assigned_student_ids', [])
        group_assignments_data = validated_data.pop('group_assignments_data', [])
        questions_data = validated_data.pop('questions', [])
        validated_data['teacher'] = self.context['request'].user
        homework = Homework.objects.create(**validated_data)

        # Новый формат: group_assignments_data с конкретными учениками
        if group_assignments_data:
            self._process_group_assignments(homework, group_assignments_data)
        elif assigned_group_ids:
            # Старый формат: просто список group_ids
            homework.assigned_groups.set(assigned_group_ids)
        
        if assigned_student_ids:
            homework.assigned_students.set(assigned_student_ids)

        for q in questions_data:
            choices = q.pop('choices', [])
            question = Question.objects.create(homework=homework, **q)
            for c in choices:
                Choice.objects.create(question=question, **c)
        return homework

    def update(self, instance, validated_data):
        assigned_group_ids = validated_data.pop('assigned_group_ids', None)
        assigned_student_ids = validated_data.pop('assigned_student_ids', None)
        group_assignments_data = validated_data.pop('group_assignments_data', None)
        questions_data = validated_data.pop('questions', None)

        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()

        # Новый формат: group_assignments_data с конкретными учениками
        if group_assignments_data is not None:
            self._process_group_assignments(instance, group_assignments_data)
        elif assigned_group_ids is not None:
            # Старый формат: просто список group_ids
            instance.assigned_groups.set(assigned_group_ids)
            # Очищаем детальные назначения при использовании старого формата
            instance.group_assignments.all().delete()
        
        if assigned_student_ids is not None:
            instance.assigned_students.set(assigned_student_ids)

        if questions_data is not None:
            instance.questions.all().delete()
            for q in questions_data:
                choices = q.pop('choices', [])
                question = Question.objects.create(homework=instance, **q)
                for c in choices:
                    Choice.objects.create(question=question, **c)

        return instance


class HomeworkStudentSerializer(serializers.ModelSerializer):
    """Чтение ДЗ учениками: без баллов и без флагов правильности."""
    teacher_email = serializers.EmailField(source='teacher.email', read_only=True)
    questions = QuestionStudentSerializer(many=True, read_only=True)
    group_id = serializers.SerializerMethodField(read_only=True)
    group_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Homework
        fields = [
            'id', 'title', 'description', 'teacher', 'teacher_email', 'lesson',
            'deadline', 'max_score',
            'group_id', 'group_name',
            'questions', 'created_at',
            # Student-facing settings
            'student_instructions', 'allow_view_answers',
        ]
        read_only_fields = fields

    def get_group_id(self, obj: Homework):
        try:
            group_ids = list(obj.assigned_groups.values_list('id', flat=True)[:2])
            if len(group_ids) == 1:
                return group_ids[0]
        except Exception:
            pass
        if obj.lesson and getattr(obj.lesson, 'group', None):
            return obj.lesson.group.id
        return None

    def get_group_name(self, obj: Homework):
        try:
            groups = list(obj.assigned_groups.all()[:2])
            if len(groups) == 1:
                return groups[0].name
            if len(groups) > 1:
                return 'Несколько групп'
        except Exception:
            pass
        if obj.lesson and getattr(obj.lesson, 'group', None):
            return obj.lesson.group.name
        return 'Без группы'


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
    time_spent_seconds = serializers.SerializerMethodField()
    questions = serializers.SerializerMethodField()
    showAnswers = serializers.SerializerMethodField()

    class Meta:
        model = StudentSubmission
        fields = ['id', 'homework', 'homework_title', 'student', 'student_email', 'student_name',
              'status', 'total_score', 'max_score', 'group_id', 'group_name', 'is_individual',
              'answers', 'questions', 'time_spent_seconds', 'teacher_feedback_summary', 
              'created_at', 'submitted_at', 'graded_at', 'showAnswers']
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
    
    def get_time_spent_seconds(self, obj):
        """Вычисляем время выполнения в секундах (от создания до отправки)."""
        if obj.submitted_at and obj.created_at:
            delta = obj.submitted_at - obj.created_at
            return int(delta.total_seconds())
        return None
    
    def get_questions(self, obj):
        """Возвращаем список вопросов домашки для отображения в проверке."""
        questions = obj.homework.questions.all().order_by('order')
        return [
            {
                'id': q.id,
                'prompt': q.prompt,
                'question_type': 'MULTIPLE_CHOICE' if q.question_type == 'MULTI_CHOICE' else q.question_type,
                'points': q.points,
                'order': q.order,
                'config': q.config or {},
            }
            for q in questions
        ]
    
    def get_max_score(self, obj):
        """Вычисляем максимальный балл для домашки"""
        return sum(q.points for q in obj.homework.questions.all())
    
    def get_showAnswers(self, obj):
        """Разрешено ли ученику смотреть свои ответы после сдачи."""
        return getattr(obj.homework, 'allow_view_answers', True)
    
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
            homework = submission.homework
            use_ai = homework.ai_grading_enabled  # Проверяем настройку AI
            for ans in answers_data:
                selected_choices = ans.pop('selected_choices', [])
                answer = Answer.objects.create(submission=submission, **ans)
                if selected_choices:
                    answer.selected_choices.set(selected_choices)
                answer.evaluate(use_ai=use_ai)
            submission.compute_auto_score()
        return submission
