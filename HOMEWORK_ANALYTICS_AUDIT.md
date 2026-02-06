# 🔍 АУДИТ МОДУЛЕЙ `homework` & `analytics`

**Дата:** 5 февраля 2026  
**Фокус:** Загрузка файлов, AI Grading, Database Performance  
**Scope:** ~4500 строк кода

---

## 📊 EXECUTIVE SUMMARY

| Аспект | Оценка | Критичность |
|--------|--------|-------------|
| Загрузка файлов | 7/10 | 🟡 СРЕДНЯЯ |
| AI Grading | 6/10 | 🟡 СРЕДНЯЯ |
| Database Performance | 7/10 | 🟡 СРЕДНЯЯ |

---

## 1. ЗАГРУЗКА ФАЙЛОВ

### 1.1 Текущая реализация

**Файлы:**
- [homework/views.py#L161-L300](teaching_panel/homework/views.py#L161-L300) - `upload_file()`, `upload_document_direct()`
- [homework/models.py#L750-L815](teaching_panel/homework/models.py#L750-L815) - `HomeworkFile`

**Текущие лимиты:**

| Параметр | Значение | Источник |
|----------|----------|----------|
| `FILE_UPLOAD_MAX_MEMORY_SIZE` | **10 GB** | settings.py:259 |
| `DATA_UPLOAD_MAX_MEMORY_SIZE` | **10 GB** | settings.py:258 |
| Homework file limit | **50 MB** | views.py:218 |

### 1.2 Проблема: Файл 10GB

**Сценарий:** Пользователь загружает файл 10GB через endpoint

**Что происходит:**
```python
# settings.py - разрешает 10GB в память!
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024 * 1024  # 10GB
```

**ОДНАКО** в `upload_file()` есть проверка:
```python
# homework/views.py:218
max_size = 50 * 1024 * 1024  # 50 MB
if uploaded_file.size > max_size:
    return Response({'detail': f'Файл слишком большой. Максимум: 50 MB'}, status=400)
```

**Риск:** НО эта проверка происходит **ПОСЛЕ** того как Django уже прочитал файл в память или на диск!

При файле 10GB:
1. Django начинает читать файл
2. Если `FILE_UPLOAD_MAX_MEMORY_SIZE = 10GB` и RAM < 10GB → **OOM Kill**
3. Если хватает RAM → файл читается 10+ минут, потом отклоняется

**Рекомендация:** Использовать nginx для ограничения размера ДО того как запрос попадёт в Django:

```nginx
# nginx.conf
client_max_body_size 100M;  # Отклоняет файлы >100MB на уровне nginx
```

### 1.3 MIME-Type Валидация

**Текущая реализация:**
```python
# homework/views.py:200-215
allowed_image_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
allowed_audio_types = ['audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/ogg', 'audio/mp4']

mime_type = uploaded_file.content_type  # ❌ Доверяем клиенту!
```

**Проблема:** `content_type` берётся из HTTP заголовка `Content-Type`, который клиент может подделать.

**Атака:**
```bash
# Загружаем .exe файл как "image/png"
curl -X POST -F "file=@malware.exe;type=image/png" /api/homework/homeworks/upload-file/
```

**Рекомендация:** Валидация по magic bytes:

```python
import magic  # pip install python-magic-bin (Windows) или python-magic (Linux)

def validate_mime_type(file_path, claimed_mime):
    """Проверяет реальный MIME-тип файла по magic bytes."""
    actual_mime = magic.from_file(file_path, mime=True)
    
    # Разрешённые MIME типы
    ALLOWED_TYPES = {
        'image/jpeg', 'image/png', 'image/gif', 'image/webp',
        'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/ogg', 'audio/mp4',
        'application/pdf', 'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    }
    
    if actual_mime not in ALLOWED_TYPES:
        raise ValueError(f"Недопустимый тип файла: {actual_mime}")
    
    return actual_mime
```

### 1.4 Сценарии тестирования загрузки

```python
# homework/tests/test_file_upload.py
"""
Сценарии для тестирования загрузки файлов.
"""
import pytest
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from unittest.mock import patch, MagicMock
import io


class TestFileUploadLimits(TestCase):
    """Тесты ограничений размера файлов."""
    
    def setUp(self):
        self.client = APIClient()
        # Создать teacher и залогинить
        
    def test_file_exceeds_50mb_rejected(self):
        """Файл больше 50MB должен быть отклонён."""
        # Создаём файл 51MB
        large_content = b'x' * (51 * 1024 * 1024)
        large_file = SimpleUploadedFile(
            'large.png',
            large_content,
            content_type='image/png'
        )
        
        response = self.client.post(
            '/api/homework/homeworks/upload-file/',
            {'file': large_file, 'file_type': 'image'},
            format='multipart'
        )
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('слишком большой', response.data['detail'])
    
    def test_file_exactly_50mb_accepted(self):
        """Файл ровно 50MB должен быть принят."""
        content = b'x' * (50 * 1024 * 1024)
        file = SimpleUploadedFile('exact.png', content, content_type='image/png')
        
        response = self.client.post(
            '/api/homework/homeworks/upload-file/',
            {'file': file, 'file_type': 'image'},
            format='multipart'
        )
        
        self.assertEqual(response.status_code, 201)


class TestMimeTypeValidation(TestCase):
    """Тесты валидации MIME-типов."""
    
    def test_fake_mime_type_rejected(self):
        """Файл с поддельным MIME-типом должен быть отклонён."""
        # EXE файл с заголовком image/png
        exe_content = b'MZ' + b'\x00' * 100  # PE header signature
        fake_image = SimpleUploadedFile(
            'malware.png',
            exe_content,
            content_type='image/png'  # Ложь!
        )
        
        # TODO: После внедрения magic bytes валидации
        # response = self.client.post(...)
        # self.assertEqual(response.status_code, 400)
    
    def test_valid_jpeg_accepted(self):
        """Реальный JPEG должен быть принят."""
        # JPEG magic bytes: FF D8 FF
        jpeg_content = b'\xff\xd8\xff\xe0' + b'\x00' * 100
        jpeg_file = SimpleUploadedFile(
            'real.jpg',
            jpeg_content,
            content_type='image/jpeg'
        )
        
        # Должен пройти валидацию


class TestLargeFileStreaming(TestCase):
    """Тесты потоковой загрузки больших файлов."""
    
    @override_settings(FILE_UPLOAD_MAX_MEMORY_SIZE=5*1024*1024)  # 5MB
    def test_large_file_uses_temp_file(self):
        """Файл больше 5MB должен использовать временный файл, не память."""
        content = b'x' * (10 * 1024 * 1024)  # 10MB
        file = SimpleUploadedFile('big.png', content, content_type='image/png')
        
        # Django должен использовать TemporaryUploadedFile
        from django.core.files.uploadedfile import TemporaryUploadedFile
        
        # После загрузки проверить что файл на диске, не в памяти
```

---

## 2. AI GRADING SERVICE

### 2.1 Текущая реализация

**Файл:** [homework/ai_grading_service.py](teaching_panel/homework/ai_grading_service.py)

**Архитектура:**
```
┌─────────────────┐
│ Answer.evaluate │ ←── Синхронный вызов в Django view
└────────┬────────┘
         │
         ▼
┌────────────────────┐
│ grade_text_answer  │ ←── Синхронная обёртка
└────────┬───────────┘
         │
         ▼
┌─────────────────────────────┐
│ AIGradingService            │
│  .grade_answer_sync()       │ ←── Блокирующий HTTP вызов
│    └── httpx.Client.post()  │     timeout=30s
└─────────────────────────────┘
```

### 2.2 Проблемы

#### Проблема 1: Синхронный вызов блокирует worker

```python
# homework/views.py:1382
answer_obj.evaluate(use_ai=use_ai)  # ❌ Синхронно!
```

При 100 студентов × 10 вопросов = 1000 AI вызовов.  
Каждый вызов = 2-5 секунд → **до 80 минут блокировки**.

Все Gunicorn workers заняты → сайт недоступен.

#### Проблема 2: Нет retry механизма

```python
# ai_grading_service.py:187-265 - grade_answer_sync
try:
    with httpx.Client(timeout=self.timeout) as client:
        response = client.post(...)  # ❌ Нет retry!
except httpx.TimeoutException:
    return AIGradingResult(..., error="Timeout")  # Просто возвращаем ошибку
```

При временных сетевых проблемах AI проверка сразу падает.

#### Проблема 3: Нет rate limiting к AI провайдерам

DeepSeek/OpenAI имеют rate limits. При массовой сдаче ДЗ можем получить 429.

### 2.3 Рекомендации

#### 2.3.1 Асинхронная проверка через Celery

```python
# homework/tasks.py
from celery import shared_task
from django.db import transaction

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=10,
    retry_backoff_max=300,
    max_retries=3,
    soft_time_limit=60,
    time_limit=120,
    rate_limit='10/m',  # Не более 10 AI вызовов в минуту
)
def grade_answer_with_ai(self, answer_id):
    """Асинхронная AI проверка одного ответа."""
    from homework.models import Answer
    from homework.ai_grading_service import AIGradingService
    
    answer = Answer.objects.select_related('question', 'submission__homework').get(id=answer_id)
    homework = answer.submission.homework
    
    if not homework.ai_grading_enabled:
        return {'status': 'skipped', 'reason': 'ai_disabled'}
    
    service = AIGradingService(provider=homework.ai_provider)
    
    result = service.grade_answer_sync(
        question_text=answer.question.prompt,
        student_answer=answer.text_answer,
        max_points=answer.question.points,
        correct_answer=answer.question.config.get('correctAnswer'),
        teacher_context=homework.ai_grading_prompt
    )
    
    with transaction.atomic():
        answer.auto_score = result.score
        answer.teacher_feedback = f"[AI: {result.confidence:.0%}] {result.feedback}"
        answer.needs_manual_review = result.error is not None or result.confidence < 0.7
        answer.save(update_fields=['auto_score', 'teacher_feedback', 'needs_manual_review'])
    
    # Пересчитать total_score
    answer.submission.compute_auto_score()
    
    return {
        'answer_id': answer_id,
        'score': result.score,
        'confidence': result.confidence,
        'error': result.error
    }


@shared_task
def grade_submission_with_ai(submission_id):
    """Запускает AI проверку для всех TEXT вопросов в submission."""
    from homework.models import StudentSubmission, Answer
    
    submission = StudentSubmission.objects.get(id=submission_id)
    
    text_answers = Answer.objects.filter(
        submission=submission,
        question__question_type='TEXT',
        auto_score__isnull=True
    ).values_list('id', flat=True)
    
    for answer_id in text_answers:
        grade_answer_with_ai.delay(answer_id)
    
    return {'queued': len(text_answers)}
```

#### 2.3.2 Встроенный retry в сервис

```python
# ai_grading_service.py - добавить retry
import tenacity

class AIGradingService:
    
    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=2, max=30),
        retry=tenacity.retry_if_exception_type((
            httpx.TimeoutException,
            httpx.ConnectError,
            httpx.HTTPStatusError,  # Для 429, 500, 502, 503
        )),
        before_sleep=lambda retry_state: logger.warning(
            f"AI grading retry #{retry_state.attempt_number}: {retry_state.outcome.exception()}"
        )
    )
    def _call_api(self, api_url, headers, payload):
        """HTTP вызов с retry."""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(api_url, headers=headers, json=payload)
            
            # 429 = rate limited, retry
            if response.status_code == 429:
                raise httpx.HTTPStatusError(
                    "Rate limited",
                    request=response.request,
                    response=response
                )
            
            response.raise_for_status()
            return response.json()
```

---

## 3. DATABASE PERFORMANCE

### 3.1 Анализ запросов

#### 3.1.1 Потенциальная N+1 проблема в `TeacherStatsViewSet.breakdown()`

```python
# analytics/views.py:370-420
for g in groups:  # N групп
    students = list(g.students.all())  # ✅ prefetch_related уже сделан
    
    for st in students:  # M студентов
        st_att_qs = att_qs.filter(student=st)  # ❌ N×M запросов!
        st_submissions = StudentSubmission.objects.filter(student=st, ...)  # ❌ Ещё N×M!
```

При 10 групп × 30 студентов = **600 дополнительных запросов** на один API вызов.

#### 3.1.2 Тяжёлые агрегации в `monthly_dynamics()`

```python
# analytics/views.py:610-640
for month in range(12):
    lessons_qs = Lesson.objects.filter(...)  # 1 запрос
    attendance_qs = Attendance.objects.filter(...)  # 1 запрос
    submissions_submitted_qs = StudentSubmission.objects.filter(...)  # 1 запрос
    submissions_graded_qs = StudentSubmission.objects.filter(...)  # 1 запрос
    # + подзапросы с annotate
```

При 12 месяцев = **48+ запросов** минимум.

### 3.2 Отсутствующие индексы

**ControlPointResult:**
```python
class Meta:
    unique_together = ['control_point', 'student']
    # ❌ Нет индекса на control_point для быстрой фильтрации по группе
```

**StudentAIReport / StudentBehaviorReport:**
```python
class Meta:
    unique_together = ['student', 'teacher', 'period_start', 'period_end']
    # ❌ Нет индекса на teacher для быстрой выборки всех отчётов учителя
```

### 3.3 Рекомендации по оптимизации

#### 3.3.1 Добавить индексы

```python
# analytics/models.py

class ControlPointResult(models.Model):
    # ... fields ...
    
    class Meta:
        unique_together = ['control_point', 'student']
        indexes = [
            models.Index(fields=['control_point', 'student'], name='cp_result_cp_student_idx'),
            models.Index(fields=['student', 'created_at'], name='cp_result_student_time_idx'),
        ]


class StudentAIReport(models.Model):
    # ... fields ...
    
    class Meta:
        indexes = [
            models.Index(fields=['teacher', 'status', 'created_at'], name='ai_report_teacher_idx'),
            models.Index(fields=['student', 'created_at'], name='ai_report_student_idx'),
        ]


class StudentBehaviorReport(models.Model):
    # ... fields ...
    
    class Meta:
        indexes = [
            models.Index(fields=['teacher', 'status', 'risk_level'], name='behavior_teacher_risk_idx'),
            models.Index(fields=['student', 'created_at'], name='behavior_student_idx'),
        ]
```

#### 3.3.2 Денормализация для аналитики

Создать материализованную таблицу со snapshot-метриками:

```python
# analytics/models.py

class StudentPerformanceSnapshot(models.Model):
    """
    Денормализованный snapshot метрик студента.
    Обновляется раз в день Celery task.
    """
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='student_snapshots')
    
    snapshot_date = models.DateField()
    
    # Посещаемость
    total_lessons = models.IntegerField(default=0)
    attended_lessons = models.IntegerField(default=0)
    attendance_percent = models.FloatField(null=True)
    
    # ДЗ
    total_homework = models.IntegerField(default=0)
    submitted_homework = models.IntegerField(default=0)
    homework_percent = models.FloatField(null=True)
    avg_homework_score = models.FloatField(null=True)
    
    # Контрольные точки
    total_control_points = models.IntegerField(default=0)
    avg_control_points_score = models.FloatField(null=True)
    
    class Meta:
        unique_together = ['student', 'group', 'snapshot_date']
        indexes = [
            models.Index(fields=['teacher', 'snapshot_date'], name='snapshot_teacher_date_idx'),
            models.Index(fields=['group', 'snapshot_date'], name='snapshot_group_date_idx'),
        ]


# Celery task для обновления snapshot
@shared_task
def update_student_performance_snapshots():
    """Запускается раз в день в 03:00."""
    from analytics.models import StudentPerformanceSnapshot
    # ... логика агрегации и сохранения
```

#### 3.3.3 Оптимизация N+1 в breakdown()

```python
# analytics/views.py - оптимизированная версия
@action(detail=False, methods=['get'])
def breakdown_optimized(self, request):
    """Оптимизированная версия с 3 запросами вместо N×M."""
    
    groups = Group.objects.filter(teacher=user).prefetch_related('students')
    group_ids = [g.id for g in groups]
    
    # 1. Собираем все student_ids
    all_student_ids = set()
    for g in groups:
        all_student_ids.update(s.id for s in g.students.all())
    
    # 2. Один запрос для всей посещаемости
    attendance_stats = Attendance.objects.filter(
        lesson__group_id__in=group_ids
    ).values('student_id', 'lesson__group_id').annotate(
        present=Count('id', filter=Q(status='present')),
        total=Count('id', filter=~Q(status__isnull=True))
    )
    
    # 3. Один запрос для всех ДЗ
    homework_stats = StudentSubmission.objects.filter(
        homework__lesson__group_id__in=group_ids,
        student_id__in=all_student_ids
    ).values('student_id', 'homework__lesson__group_id').annotate(
        completed=Count('id', filter=Q(total_score__isnull=False))
    )
    
    # Строим lookup словари
    att_lookup = {}  # (student_id, group_id) -> {present, total}
    for row in attendance_stats:
        key = (row['student_id'], row['lesson__group_id'])
        att_lookup[key] = {'present': row['present'], 'total': row['total']}
    
    # ... использовать lookup вместо N×M запросов
```

### 3.4 Тестирование производительности

```python
# analytics/tests/test_performance.py
"""
Тесты производительности для аналитики с 10,000 студентов.
"""
from django.test import TestCase, TransactionTestCase
from django.db import connection, reset_queries
from django.conf import settings
import time


class AnalyticsPerformanceTest(TransactionTestCase):
    """Тесты производительности."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Создаём тестовые данные: 100 групп × 100 студентов = 10,000
        cls._create_test_data(groups=100, students_per_group=100)
    
    @classmethod
    def _create_test_data(cls, groups, students_per_group):
        """Создаёт тестовые данные для нагрузочного теста."""
        # Batch insert для скорости
        from accounts.models import CustomUser
        from schedule.models import Group
        
        teacher = CustomUser.objects.create_user(
            email='perf_teacher@test.com',
            password='test123',
            role='teacher'
        )
        
        for g_idx in range(groups):
            group = Group.objects.create(name=f'PerfGroup_{g_idx}', teacher=teacher)
            
            students = [
                CustomUser(
                    email=f'perf_student_{g_idx}_{s_idx}@test.com',
                    role='student'
                )
                for s_idx in range(students_per_group)
            ]
            CustomUser.objects.bulk_create(students)
            group.students.set(students)
    
    def test_gradebook_query_count(self):
        """Gradebook не должен делать больше 10 запросов."""
        settings.DEBUG = True
        reset_queries()
        
        start = time.time()
        response = self.client.get('/api/analytics/gradebook/group/?group=1')
        elapsed = time.time() - start
        
        query_count = len(connection.queries)
        
        self.assertLess(query_count, 10, f"Too many queries: {query_count}")
        self.assertLess(elapsed, 2.0, f"Too slow: {elapsed:.2f}s")
    
    def test_breakdown_with_10k_students(self):
        """Breakdown должен работать за <5 секунд с 10K студентов."""
        start = time.time()
        response = self.client.get('/api/analytics/teacher-stats/breakdown/')
        elapsed = time.time() - start
        
        self.assertEqual(response.status_code, 200)
        self.assertLess(elapsed, 5.0, f"Breakdown too slow: {elapsed:.2f}s")
```

---

## 4. ИТОГОВЫЕ РЕКОМЕНДАЦИИ

### Приоритет ВЫСОКИЙ

1. **nginx client_max_body_size** - защита от 10GB файлов на уровне nginx
2. **AI Grading через Celery** - не блокировать web workers
3. **Retry механизм для AI API** - tenacity или встроенный в task

### Приоритет СРЕДНИЙ

4. **Magic bytes валидация MIME** - защита от подделки Content-Type
5. **Индексы в analytics models** - ускорение запросов
6. **Оптимизация N+1 в breakdown()** - 3 запроса вместо 600

### Приоритет НИЗКИЙ

7. **StudentPerformanceSnapshot** - денормализация для дашбордов
8. **Rate limiting к AI провайдерам** - `rate_limit='10/m'` в Celery

---

## 5. МИГРАЦИЯ ДЛЯ ИНДЕКСОВ

```python
# analytics/migrations/XXXX_add_performance_indexes.py
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', 'previous_migration'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='controlpointresult',
            index=models.Index(
                fields=['control_point', 'student'],
                name='cp_result_cp_student_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='studentaireport',
            index=models.Index(
                fields=['teacher', 'status', 'created_at'],
                name='ai_report_teacher_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='studentbehaviorreport',
            index=models.Index(
                fields=['teacher', 'status', 'risk_level'],
                name='behavior_teacher_risk_idx'
            ),
        ),
    ]
```

---

**Конец отчёта**  
_Создан: 5 февраля 2026_
