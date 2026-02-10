"""
Views модуля симуляции экзаменов ЕГЭ/ОГЭ.
"""

import random
from datetime import timedelta

from django.db import transaction
from django.db.models import Count, F
from django.utils import timezone
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import (
    ExamBlueprint, ExamTaskSlot, ExamTask,
    ExamVariant, ExamVariantTask, ExamAttempt,
)
from .serializers import (
    ExamBlueprintListSerializer, ExamBlueprintDetailSerializer,
    ExamBlueprintCreateSerializer, ExamTaskSlotSerializer,
    ExamTaskListSerializer, ExamTaskDetailSerializer,
    ExamTaskCreateSerializer,
    ExamVariantListSerializer, ExamVariantDetailSerializer,
    ExamVariantManualCreateSerializer, ExamVariantGenerateSerializer,
    ExamVariantAssignSerializer,
    ExamAttemptSerializer, ExamAttemptResultSerializer,
)


class IsTeacherOrAdmin(permissions.BasePermission):
    """Доступ только для учителей и администраторов."""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            hasattr(request.user, 'role') and
            request.user.role in ('teacher', 'admin')
        )


class ExamBlueprintViewSet(viewsets.ModelViewSet):
    """
    CRUD для шаблонов экзаменов.
    
    GET    /api/exam/blueprints/           — список шаблонов
    POST   /api/exam/blueprints/           — создать шаблон
    GET    /api/exam/blueprints/{id}/      — детали шаблона
    PUT    /api/exam/blueprints/{id}/      — обновить
    DELETE /api/exam/blueprints/{id}/      — удалить
    
    POST   /api/exam/blueprints/{id}/slots/     — управление слотами
    POST   /api/exam/blueprints/{id}/duplicate/ — дублировать шаблон
    """
    permission_classes = [IsTeacherOrAdmin]
    
    def get_queryset(self):
        qs = ExamBlueprint.objects.select_related(
            'subject', 'subject__exam_type', 'created_by'
        ).prefetch_related('task_slots')
        
        user = self.request.user
        # Показываем: свои + публичные + своей школы
        from django.db.models import Q
        qs = qs.filter(
            Q(created_by=user) |
            Q(is_public=True) |
            Q(school=getattr(user, 'current_school', None))
        )
        
        # Фильтры
        subject = self.request.query_params.get('subject')
        if subject:
            qs = qs.filter(subject_id=subject)
        
        exam_type = self.request.query_params.get('exam_type')
        if exam_type:
            qs = qs.filter(subject__exam_type__code=exam_type)
        
        year = self.request.query_params.get('year')
        if year:
            qs = qs.filter(year=year)
        
        active_only = self.request.query_params.get('active', 'true')
        if active_only.lower() == 'true':
            qs = qs.filter(is_active=True)
        
        return qs.distinct()

    def get_serializer_class(self):
        if self.action == 'list':
            return ExamBlueprintListSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return ExamBlueprintCreateSerializer
        return ExamBlueprintDetailSerializer

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user,
            school=getattr(self.request.user, 'current_school', None),
        )

    @action(detail=True, methods=['post'])
    def slots(self, request, pk=None):
        """Пакетное обновление слотов задания."""
        blueprint = self.get_object()
        slots_data = request.data.get('slots', [])
        
        with transaction.atomic():
            blueprint.task_slots.all().delete()
            for slot_data in slots_data:
                serializer = ExamTaskSlotSerializer(data=slot_data)
                serializer.is_valid(raise_exception=True)
                serializer.save(blueprint=blueprint)
            blueprint.recalculate_total_score()
        
        return Response(
            ExamBlueprintDetailSerializer(blueprint).data,
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Дублировать шаблон."""
        original = self.get_object()
        
        with transaction.atomic():
            new_bp = ExamBlueprint.objects.create(
                subject=original.subject,
                title=f"{original.title} (копия)",
                year=original.year,
                duration_minutes=original.duration_minutes,
                total_primary_score=original.total_primary_score,
                score_scale=original.score_scale,
                grade_thresholds=original.grade_thresholds,
                description=original.description,
                is_active=True,
                is_public=False,
                created_by=request.user,
                school=getattr(request.user, 'current_school', None),
            )
            for slot in original.task_slots.all():
                ExamTaskSlot.objects.create(
                    blueprint=new_bp,
                    task_number=slot.task_number,
                    title=slot.title,
                    answer_type=slot.answer_type,
                    max_points=slot.max_points,
                    topic=slot.topic,
                    answer_config=slot.answer_config,
                    description=slot.description,
                    order=slot.order,
                )
        
        return Response(
            ExamBlueprintDetailSerializer(new_bp).data,
            status=status.HTTP_201_CREATED
        )


class ExamTaskViewSet(viewsets.ModelViewSet):
    """
    CRUD для банка заданий.
    
    GET  /api/exam/tasks/?blueprint=X&task_number=5  — задания по фильтру
    POST /api/exam/tasks/                            — добавить задание
    POST /api/exam/tasks/bulk-import/                — массовый импорт
    """
    permission_classes = [IsTeacherOrAdmin]

    def get_queryset(self):
        qs = ExamTask.objects.select_related(
            'question', 'blueprint', 'created_by'
        ).filter(is_active=True)
        
        blueprint = self.request.query_params.get('blueprint')
        if blueprint:
            qs = qs.filter(blueprint_id=blueprint)
        
        task_number = self.request.query_params.get('task_number')
        if task_number:
            qs = qs.filter(task_number=task_number)
        
        difficulty = self.request.query_params.get('difficulty')
        if difficulty:
            qs = qs.filter(difficulty=difficulty)
        
        source = self.request.query_params.get('source')
        if source:
            qs = qs.filter(source=source)
        
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(question__prompt__icontains=search)
        
        return qs

    def get_serializer_class(self):
        if self.action in ('create',):
            return ExamTaskCreateSerializer
        if self.action == 'retrieve':
            return ExamTaskDetailSerializer
        return ExamTaskListSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['post'], url_path='bulk-import')
    def bulk_import(self, request):
        """
        Массовый импорт заданий.
        Формат: {"blueprint_id": 1, "tasks": [{task_number, prompt, question_type, ...}, ...]}
        """
        blueprint_id = request.data.get('blueprint_id')
        tasks_data = request.data.get('tasks', [])
        
        if not blueprint_id or not tasks_data:
            return Response(
                {'detail': 'blueprint_id и tasks обязательны'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            blueprint = ExamBlueprint.objects.get(id=blueprint_id)
        except ExamBlueprint.DoesNotExist:
            return Response(
                {'detail': 'Шаблон не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        created = []
        errors = []
        
        with transaction.atomic():
            for i, task_data in enumerate(tasks_data):
                task_data['blueprint'] = blueprint.id
                serializer = ExamTaskCreateSerializer(data=task_data)
                if serializer.is_valid():
                    task = serializer.save(created_by=request.user)
                    created.append(task.id)
                else:
                    errors.append({'index': i, 'errors': serializer.errors})
        
        return Response({
            'created_count': len(created),
            'created_ids': created,
            'errors': errors,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Статистика банка заданий по blueprint."""
        blueprint_id = request.query_params.get('blueprint')
        if not blueprint_id:
            return Response({'detail': 'blueprint обязателен'}, status=400)
        
        stats = ExamTask.objects.filter(
            blueprint_id=blueprint_id, is_active=True
        ).values('task_number').annotate(
            count=Count('id'),
            easy=Count('id', filter=models.Q(difficulty='easy')),
            medium=Count('id', filter=models.Q(difficulty='medium')),
            hard=Count('id', filter=models.Q(difficulty='hard')),
        ).order_by('task_number')
        
        return Response(list(stats))


class ExamVariantViewSet(viewsets.ModelViewSet):
    """
    Управление вариантами экзамена.
    
    GET  /api/exam/variants/?blueprint=X — варианты по шаблону
    POST /api/exam/variants/generate/    — авто-генерация
    POST /api/exam/variants/manual/      — ручная сборка
    POST /api/exam/variants/{id}/assign/ — назначить группе
    """
    permission_classes = [IsTeacherOrAdmin]

    def get_queryset(self):
        qs = ExamVariant.objects.select_related(
            'blueprint', 'created_by', 'homework'
        ).prefetch_related('variant_tasks__task__question')
        
        blueprint = self.request.query_params.get('blueprint')
        if blueprint:
            qs = qs.filter(blueprint_id=blueprint)
        
        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return ExamVariantListSerializer
        return ExamVariantDetailSerializer

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Авто-генерация вариантов из банка заданий."""
        serializer = ExamVariantGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        try:
            blueprint = ExamBlueprint.objects.get(id=data['blueprint_id'])
        except ExamBlueprint.DoesNotExist:
            return Response({'detail': 'Шаблон не найден'}, status=404)
        
        slots = blueprint.task_slots.all().order_by('task_number')
        if not slots.exists():
            return Response(
                {'detail': 'В шаблоне нет слотов заданий'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        exclude_ids = set(data.get('exclude_task_ids', []))
        difficulty_mode = data.get('difficulty_balance', 'balanced')
        generated_variants = []
        
        with transaction.atomic():
            # Определяем следующий номер варианта
            last_num = blueprint.variants.aggregate(
                max_num=models.Max('variant_number')
            )['max_num'] or 0
            
            for i in range(data['count']):
                variant_num = last_num + i + 1
                variant = ExamVariant.objects.create(
                    blueprint=blueprint,
                    variant_number=variant_num,
                    title=f"Вариант {variant_num}",
                    is_manual=False,
                    created_by=request.user,
                )
                
                all_ok = True
                for slot in slots:
                    pool = ExamTask.objects.filter(
                        blueprint=blueprint,
                        task_number=slot.task_number,
                        is_active=True,
                    ).exclude(id__in=exclude_ids)
                    
                    if not pool.exists():
                        all_ok = False
                        continue
                    
                    # Выбираем задание с учётом сложности
                    task = self._select_task(pool, difficulty_mode)
                    
                    ExamVariantTask.objects.create(
                        variant=variant,
                        task=task,
                        task_number=slot.task_number,
                        order=slot.order,
                    )
                    
                    # Инкрементируем usage_count
                    task.usage_count = F('usage_count') + 1
                    task.save(update_fields=['usage_count'])
                    
                    # Исключаем из следующих вариантов в этой генерации
                    exclude_ids.add(task.id)
                
                generated_variants.append(variant)
        
        return Response(
            ExamVariantListSerializer(generated_variants, many=True).data,
            status=status.HTTP_201_CREATED
        )

    def _select_task(self, pool, difficulty_mode):
        """Выбрать задание из пула с учётом баланса сложности."""
        pool_list = list(pool)
        
        if difficulty_mode == 'random':
            return random.choice(pool_list)
        
        if difficulty_mode == 'easy':
            easy_tasks = [t for t in pool_list if t.difficulty == 'easy']
            if easy_tasks:
                return random.choice(easy_tasks)
            return random.choice(pool_list)
        
        if difficulty_mode == 'hard':
            hard_tasks = [t for t in pool_list if t.difficulty == 'hard']
            if hard_tasks:
                return random.choice(hard_tasks)
            return random.choice(pool_list)
        
        # balanced: предпочитаем менее использованные
        pool_list.sort(key=lambda t: t.usage_count)
        # Берём из нижней трети по usage_count
        cutoff = max(1, len(pool_list) // 3)
        candidates = pool_list[:cutoff]
        return random.choice(candidates)

    @action(detail=False, methods=['post'])
    def manual(self, request):
        """Ручная сборка варианта."""
        serializer = ExamVariantManualCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        try:
            blueprint = ExamBlueprint.objects.get(id=data['blueprint_id'])
        except ExamBlueprint.DoesNotExist:
            return Response({'detail': 'Шаблон не найден'}, status=404)
        
        with transaction.atomic():
            last_num = blueprint.variants.aggregate(
                max_num=models.Max('variant_number')
            )['max_num'] or 0
            variant_num = last_num + 1
            
            variant = ExamVariant.objects.create(
                blueprint=blueprint,
                variant_number=variant_num,
                title=data.get('title') or f"Вариант {variant_num}",
                is_manual=True,
                created_by=request.user,
            )
            
            for task_data in data['tasks']:
                task = ExamTask.objects.get(id=task_data['task_id'])
                ExamVariantTask.objects.create(
                    variant=variant,
                    task=task,
                    task_number=task_data['task_number'],
                    order=task_data['task_number'],
                )
                task.usage_count = F('usage_count') + 1
                task.save(update_fields=['usage_count'])
        
        return Response(
            ExamVariantDetailSerializer(variant).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """
        Назначить вариант группам.
        Создаёт Homework из заданий варианта и назначает группам.
        """
        variant = self.get_object()
        serializer = ExamVariantAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        if variant.homework:
            return Response(
                {'detail': 'Вариант уже назначен', 'homework_id': variant.homework.id},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from homework.models import Homework, Question, Choice
        from homework.models import HomeworkGroupAssignment
        from schedule.models import Group
        
        blueprint = variant.blueprint
        
        with transaction.atomic():
            # Создаём Homework
            homework = Homework.objects.create(
                teacher=request.user,
                title=f"{blueprint.title} — {variant.title}",
                description=blueprint.description,
                status='draft',
                max_score=blueprint.total_primary_score,
                deadline=data.get('deadline'),
                student_instructions=data.get('student_instructions', ''),
                allow_view_answers=False,  # Режим экзамена
                school=getattr(request.user, 'current_school', None),
            )
            
            # Копируем вопросы из банка в Homework
            variant_tasks = variant.variant_tasks.select_related(
                'task__question'
            ).order_by('task_number')
            
            question_mapping = {}  # old_question_id → new_question
            
            for vt in variant_tasks:
                original_q = vt.task.question
                new_q = Question.objects.create(
                    homework=homework,
                    prompt=original_q.prompt,
                    question_type=original_q.question_type,
                    points=original_q.points,
                    order=vt.task_number,
                    config=original_q.config,
                    explanation=original_q.explanation,
                )
                # Копируем choices
                for choice in original_q.choices.all():
                    Choice.objects.create(
                        question=new_q,
                        text=choice.text,
                        is_correct=choice.is_correct,
                    )
                question_mapping[original_q.id] = new_q
            
            # Назначаем группам
            for group_id in data['group_ids']:
                try:
                    group = Group.objects.get(id=group_id)
                    homework.assigned_groups.add(group)
                    HomeworkGroupAssignment.objects.create(
                        homework=homework,
                        group=group,
                        deadline=data.get('deadline'),
                    )
                except Group.DoesNotExist:
                    pass
            
            # Связываем вариант с Homework
            variant.homework = homework
            variant.save(update_fields=['homework'])
        
        return Response({
            'homework_id': homework.id,
            'variant_id': variant.id,
            'message': 'Вариант назначен. Опубликуйте ДЗ для доступа ученикам.',
        }, status=status.HTTP_201_CREATED)


class ExamAttemptViewSet(viewsets.ModelViewSet):
    """
    Управление попытками экзамена.
    
    POST /api/exam/attempts/{id}/start/        — начать экзамен (таймер)
    GET  /api/exam/attempts/{id}/timer/        — текущее время
    POST /api/exam/attempts/{id}/force-submit/ — авто-сдача
    GET  /api/exam/attempts/{id}/result/       — результаты
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ExamAttemptSerializer

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'role') and user.role in ('teacher', 'admin'):
            return ExamAttempt.objects.select_related(
                'submission', 'submission__student', 'variant', 'variant__blueprint'
            )
        # Ученик видит только свои
        return ExamAttempt.objects.filter(
            submission__student=user
        ).select_related(
            'submission', 'variant', 'variant__blueprint'
        )

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Начать экзамен — запускает таймер."""
        attempt = self.get_object()
        
        if attempt.started_at:
            return Response({
                'detail': 'Экзамен уже начат',
                'started_at': attempt.started_at,
                'deadline_at': attempt.deadline_at,
            }, status=status.HTTP_400_BAD_REQUEST)
        
        now = timezone.now()
        duration = attempt.variant.blueprint.duration_minutes
        
        attempt.started_at = now
        attempt.deadline_at = now + timedelta(minutes=duration)
        attempt.save(update_fields=['started_at', 'deadline_at'])
        
        # Обновляем статус submission
        attempt.submission.status = 'in_progress'
        attempt.submission.save(update_fields=['status'])
        
        return Response({
            'started_at': attempt.started_at,
            'deadline_at': attempt.deadline_at,
            'duration_minutes': duration,
        })

    @action(detail=True, methods=['get'])
    def timer(self, request, pk=None):
        """Получить серверное время до дедлайна."""
        attempt = self.get_object()
        
        if not attempt.deadline_at:
            return Response({'time_remaining_seconds': None, 'started': False})
        
        remaining = (attempt.deadline_at - timezone.now()).total_seconds()
        return Response({
            'time_remaining_seconds': max(0, int(remaining)),
            'deadline_at': attempt.deadline_at,
            'started': True,
            'expired': remaining <= 0,
        })

    @action(detail=True, methods=['post'], url_path='force-submit')
    def force_submit(self, request, pk=None):
        """Принудительная сдача (авто-сдача по таймеру или учителем)."""
        attempt = self.get_object()
        
        if attempt.submission.status in ('submitted', 'graded'):
            return Response({'detail': 'Уже сдано'}, status=400)
        
        with transaction.atomic():
            attempt.auto_submitted = True
            
            # Фиксируем время
            if attempt.started_at:
                attempt.time_spent_seconds = int(
                    (timezone.now() - attempt.started_at).total_seconds()
                )
            
            attempt.save(update_fields=['auto_submitted', 'time_spent_seconds'])
            
            # Сдаём submission
            submission = attempt.submission
            submission.status = 'submitted'
            submission.submitted_at = timezone.now()
            submission.save(update_fields=['status', 'submitted_at'])
            
            # Запускаем автопроверку всех ответов
            for answer in submission.answers.select_related('question').all():
                answer.evaluate()
                answer.save()
            
            submission.compute_auto_score()
            
            # Проверяем нужна ли ручная проверка
            needs_manual = submission.answers.filter(needs_manual_review=True).exists()
            if not needs_manual:
                submission.status = 'graded'
                submission.graded_at = timezone.now()
                submission.save(update_fields=['status', 'graded_at'])
            
            # Считаем баллы
            attempt.calculate_scores()
        
        return Response(
            ExamAttemptResultSerializer(attempt).data,
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['get'])
    def result(self, request, pk=None):
        """Детальный результат экзамена."""
        attempt = self.get_object()
        
        # Пересчитываем если ещё не было
        if attempt.primary_score is None:
            attempt.calculate_scores()
        
        return Response(ExamAttemptResultSerializer(attempt).data)

    @action(detail=False, methods=['get'])
    def my(self, request):
        """Список попыток текущего ученика."""
        attempts = ExamAttempt.objects.filter(
            submission__student=request.user
        ).select_related(
            'submission', 'variant', 'variant__blueprint'
        ).order_by('-started_at')
        
        return Response(
            ExamAttemptSerializer(attempts, many=True).data
        )

    @action(detail=False, methods=['get'])
    def analytics(self, request):
        """Аналитика по группе/ученику для учителя."""
        if not hasattr(request.user, 'role') or request.user.role not in ('teacher', 'admin'):
            return Response({'detail': 'Только для учителей'}, status=403)
        
        blueprint_id = request.query_params.get('blueprint')
        group_id = request.query_params.get('group')
        student_id = request.query_params.get('student')
        
        attempts = ExamAttempt.objects.select_related(
            'submission__student', 'variant__blueprint'
        )
        
        if blueprint_id:
            attempts = attempts.filter(variant__blueprint_id=blueprint_id)
        if group_id:
            attempts = attempts.filter(
                submission__homework__assigned_groups__id=group_id
            )
        if student_id:
            attempts = attempts.filter(submission__student_id=student_id)
        
        # Только завершённые
        attempts = attempts.exclude(primary_score=None)
        
        if not attempts.exists():
            return Response({
                'total_attempts': 0,
                'avg_primary': 0,
                'avg_test': 0,
                'weak_tasks': [],
            })
        
        # Средние баллы
        from django.db.models import Avg
        averages = attempts.aggregate(
            avg_primary=Avg('primary_score'),
            avg_test=Avg('test_score'),
        )
        
        # Слабые задания — анализ task_scores
        task_stats = {}
        for attempt in attempts:
            for ts in (attempt.task_scores or []):
                num = ts['task_number']
                if num not in task_stats:
                    task_stats[num] = {'total_score': 0, 'total_max': 0, 'count': 0}
                task_stats[num]['total_score'] += ts['score']
                task_stats[num]['total_max'] += ts['max']
                task_stats[num]['count'] += 1
        
        weak_tasks = []
        for num, st in sorted(task_stats.items()):
            pct = st['total_score'] / st['total_max'] * 100 if st['total_max'] else 0
            weak_tasks.append({
                'task_number': num,
                'avg_percent': round(pct, 1),
                'attempts': st['count'],
            })
        
        weak_tasks.sort(key=lambda x: x['avg_percent'])
        
        return Response({
            'total_attempts': attempts.count(),
            'avg_primary': round(averages['avg_primary'] or 0, 1),
            'avg_test': round(averages['avg_test'] or 0, 1),
            'weak_tasks': weak_tasks,
            'attempts': ExamAttemptSerializer(attempts[:50], many=True).data,
        })
