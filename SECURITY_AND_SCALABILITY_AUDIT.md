# 🛡️ ПОЛНЫЙ АУДИТ БЕЗОПАСНОСТИ И МАСШТАБИРУЕМОСТИ
## Teaching Panel LMS — 11 декабря 2025

**Цель:** Проверка готовности к нагрузке 2-3 тыс. преподавателей + 5-7 тыс. учеников одновременно

---

## 📊 EXECUTIVE SUMMARY

| Категория | Статус | Критичных | Серьёзных | Средних |
|-----------|--------|-----------|-----------|---------|
| Безопасность | ⚠️ Требует внимания | 4 | 7 | 3 |
| Производительность | ✅ Хорошо | 0 | 2 | 4 |
| Масштабируемость | ✅ Готов | 0 | 1 | 2 |
| Архитектура | ✅ Хорошо | 0 | 0 | 3 |

**Общая готовность к продакшену: 75%** — требуется исправить критические уязвимости безопасности

---

## 🔴 КРИТИЧЕСКИЕ УЯЗВИМОСТИ (требуют немедленного исправления)

### 1. Path Traversal в загрузке файлов

**Файлы:**
- [homework/views.py](teaching_panel/homework/views.py#L143-L146) — `upload_file`
- [schedule/views.py](teaching_panel/schedule/views.py#L466-L472) — `upload_standalone_recording`

**Проблема:**
```python
# homework/views.py:143
safe_name = uploaded_file.name.replace(' ', '_').replace('..', '')
# НЕ ЗАЩИЩАЕТ ОТ: "....//", "../", "%2e%2e%2f"
```

**Исправление:**
```python
import os
from django.utils.text import get_valid_filename

# Полная санитизация имени файла
original_name = uploaded_file.name
# Убираем путь (../../../etc/passwd → passwd)
safe_name = os.path.basename(original_name)
# Удаляем опасные символы
safe_name = get_valid_filename(safe_name)
# Добавляем уникальный префикс
file_name = f"homework_{request.user.id}_{uuid.uuid4().hex[:8]}_{safe_name}"
```

---

### 2. IDOR в настройках приватности записей

**Файлы:**
- [schedule/views.py#L490-498](teaching_panel/schedule/views.py#L490) — `upload_standalone_recording`
- [schedule/views.py#L872-880](teaching_panel/schedule/views.py#L872) — `upload_recording`

**Проблема:** Учитель может указать ID ЛЮБЫХ групп/студентов при настройке доступа к записи.

**Исправление:**
```python
# В apply_privacy или в view
def apply_privacy(self, privacy_type, group_ids, student_ids, teacher):
    # ВАЛИДАЦИЯ: группы должны принадлежать учителю
    valid_groups = Group.objects.filter(id__in=group_ids, teacher=teacher)
    if valid_groups.count() != len(group_ids):
        raise ValidationError("Доступ запрещён к некоторым группам")
    
    # ВАЛИДАЦИЯ: студенты должны быть в группах учителя
    teacher_student_ids = CustomUser.objects.filter(
        enrolled_groups__teacher=teacher, 
        id__in=student_ids
    ).values_list('id', flat=True)
    if set(student_ids) - set(teacher_student_ids):
        raise ValidationError("Доступ запрещён к некоторым студентам")
```

---

### 3. Отсутствие проверки MIME-типа и размера видео

**Файл:** [schedule/views.py#L460-475](teaching_panel/schedule/views.py#L460)

**Проблема:** Можно загрузить любой файл (PHP, HTML, EXE) вместо видео.

**Исправление:**
```python
@action(detail=False, methods=['post'], url_path='upload_standalone_recording')
def upload_standalone_recording(self, request):
    video_file = request.FILES.get('video')
    
    # Проверка MIME-типа
    allowed_mime_types = ['video/mp4', 'video/webm', 'video/mpeg', 'video/quicktime']
    if video_file.content_type not in allowed_mime_types:
        return Response(
            {'detail': f'Неподдерживаемый тип файла: {video_file.content_type}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Проверка размера (макс 2 GB)
    max_size = 2 * 1024 * 1024 * 1024
    if video_file.size > max_size:
        return Response(
            {'detail': 'Файл слишком большой. Максимум: 2 GB'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Проверка магических байтов файла
    first_bytes = video_file.read(12)
    video_file.seek(0)
    
    video_signatures = [
        b'\x00\x00\x00\x18ftypmp42',  # MP4
        b'\x00\x00\x00\x1cftypisom',  # MP4 ISOM
        b'\x1aE\xdf\xa3',             # WebM
    ]
    
    if not any(first_bytes.startswith(sig[:len(first_bytes)]) for sig in video_signatures):
        return Response(
            {'detail': 'Файл не является валидным видео'},
            status=status.HTTP_400_BAD_REQUEST
        )
```

---

### 4. YooKassa Webhook без верификации

**Файл:** [accounts/payments_views.py#L25-35](teaching_panel/accounts/payments_views.py#L25)

**Проблема:** Если `YOOKASSA_WEBHOOK_SECRET` не настроен, webhook всё равно обрабатывается.

**Исправление:**
```python
@csrf_exempt
@require_http_methods(["POST"])
def yookassa_webhook(request):
    # ОБЯЗАТЕЛЬНАЯ проверка секрета
    webhook_secret = getattr(settings, 'YOOKASSA_WEBHOOK_SECRET', None)
    
    if not webhook_secret:
        logger.error("YOOKASSA_WEBHOOK_SECRET not configured!")
        return JsonResponse({'error': 'Webhooks disabled'}, status=503)
    
    # Всегда проверяем подпись
    signature = request.headers.get('X-Yookassa-Signature', '')
    body = request.body.decode('utf-8')
    
    expected_signature = hmac.new(
        webhook_secret.encode('utf-8'),
        body.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(signature, expected_signature):
        logger.warning(f"Invalid webhook signature from {request.META.get('REMOTE_ADDR')}")
        return JsonResponse({'error': 'Invalid signature'}, status=403)
```

---

## 🟠 СЕРЬЁЗНЫЕ УЯЗВИМОСТИ

### 5. Утечка zoom_start_url студентам

**Файл:** [schedule/serializers.py#L68](teaching_panel/schedule/serializers.py#L68)

**Проблема:** `zoom_start_url` — это HOST-ссылка для запуска встречи. Студенты могут её использовать.

**Исправление:**
```python
class LessonSerializer(serializers.ModelSerializer):
    zoom_start_url = serializers.SerializerMethodField()
    
    def get_zoom_start_url(self, obj):
        request = self.context.get('request')
        if not request:
            return None
        user = request.user
        # Только преподаватель и админ видят start_url
        if getattr(user, 'role', None) in ['teacher', 'admin']:
            return obj.zoom_start_url
        return None
```

---

### 6. Mass Assignment — добавление любого студента в группу

**Файл:** [schedule/views.py#L127-140](teaching_panel/schedule/views.py#L127)

**Проблема:** Учитель может добавить любого студента в группу без его согласия.

**Рекомендация:** Реализовать систему приглашений с подтверждением или ограничить добавление только по invite_code.

---

### 7. mark_attendance для любого student_id

**Файл:** [schedule/views.py#L720-741](teaching_panel/schedule/views.py#L720)

**Исправление:**
```python
@action(detail=True, methods=['post'])
def mark_attendance(self, request, pk=None):
    lesson = self.get_object()
    attendances = request.data.get('attendances', [])
    
    # Получаем валидные student_id из группы урока
    valid_student_ids = set(lesson.group.students.values_list('id', flat=True))
    
    for attendance_data in attendances:
        student_id = attendance_data.get('student_id')
        
        # ВАЛИДАЦИЯ: студент должен быть в группе
        if student_id not in valid_student_ids:
            continue  # или вернуть ошибку
        
        Attendance.objects.update_or_create(...)
```

---

## 🟡 ПРОБЛЕМЫ ПРОИЗВОДИТЕЛЬНОСТИ

### 8. N+1 запросы в GroupViewSet.get_queryset()

**Файл:** [schedule/views.py#L119-125](teaching_panel/schedule/views.py#L119)

**Текущий код:**
```python
def get_queryset(self):
    queryset = super().get_queryset()  # Group.objects.all()
    if user.role == 'student':
        return queryset.filter(students=user)  # N+1 при сериализации students
```

**Исправление:**
```python
def get_queryset(self):
    queryset = super().get_queryset().select_related('teacher').prefetch_related('students')
```

---

### 9. RecurringLesson разворачивание без кеширования

**Файл:** [schedule/views.py#L314-400](teaching_panel/schedule/views.py#L314)

**Проблема:** Каждый запрос календаря пересчитывает все виртуальные уроки.

**Рекомендация:**
```python
from django.core.cache import cache

def _build_recurring_virtual_lessons(self, request, start_dt, end_dt, existing_queryset):
    cache_key = f"recurring_lessons_{request.user.id}_{start_dt.date()}_{end_dt.date()}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    # ... вычисления ...
    
    cache.set(cache_key, virtual_lessons, 300)  # 5 минут
    return virtual_lessons
```

---

### 10. Отсутствующие индексы БД

**Рекомендуемые индексы:**

```python
# schedule/models.py - Lesson
class Meta:
    indexes = [
        models.Index(fields=['start_time']),  # ✅ Есть
        models.Index(fields=['teacher', 'start_time']),  # ✅ Есть
        models.Index(fields=['group', 'start_time']),  # ✅ Есть
        models.Index(fields=['is_quick_lesson']),  # ❌ ДОБАВИТЬ
        models.Index(fields=['zoom_meeting_id']),  # ❌ ДОБАВИТЬ для поиска по meeting
    ]

# homework/models.py - Homework
class Meta:
    indexes = [
        models.Index(fields=['teacher', 'status']),  # ❌ ДОБАВИТЬ
        models.Index(fields=['lesson', 'status']),  # ❌ ДОБАВИТЬ
    ]

# accounts/models.py - CustomUser
class Meta:
    indexes = [
        models.Index(fields=['email']),  # Должен быть через unique=True
        models.Index(fields=['role']),  # ❌ ДОБАВИТЬ для фильтрации
    ]
```

---

## 📈 РЕКОМЕНДАЦИИ ПО МАСШТАБИРУЕМОСТИ

### ✅ Что уже хорошо:

1. **Celery для фоновых задач** — правильная архитектура
2. **Redis кеширование** — настроено с connection pool
3. **JWT аутентификация** — stateless, масштабируется горизонтально
4. **Rate limiting** — настроен для основных endpoints
5. **Database connection pooling** — настроен через dj-database-url
6. **Индексы БД** — основные индексы на Lesson присутствуют

### 🔧 Что нужно улучшить:

#### 1. Gunicorn workers

**Файл:** [gunicorn.conf.py](teaching_panel/gunicorn.conf.py)

```python
# Текущее
workers = 3
worker_class = "sync"

# Рекомендация для 10K пользователей
import multiprocessing
workers = multiprocessing.cpu_count() * 2 + 1  # ~9 на 4-ядерном CPU
worker_class = "gthread"  # Или "gevent" для async
threads = 4  # Для gthread
max_requests = 1000
max_requests_jitter = 100
timeout = 30  # Снизить с 120
```

#### 2. Database Pool для PostgreSQL

**Файл:** [settings.py](teaching_panel/teaching_panel/settings.py)

```python
if os.environ.get('DATABASE_URL'):
    DATABASES = {
        'default': dj_database_url.config(
            default=os.environ.get('DATABASE_URL'),
            conn_max_age=600,  # ✅ Уже есть
            conn_health_checks=True,  # ✅ Уже есть
        )
    }
    
    # ДОБАВИТЬ: Connection pooling через PgBouncer или django-db-connection-pool
    # pip install django-db-connection-pool
    DATABASES['default']['ENGINE'] = 'dj_db_conn_pool.backends.postgresql'
    DATABASES['default']['POOL_OPTIONS'] = {
        'POOL_SIZE': 20,
        'MAX_OVERFLOW': 10,
    }
```

#### 3. Кеширование сессий и токенов

```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL'),
        'OPTIONS': {
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,  # ✅ Уже есть
            }
        }
    },
    'sessions': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL') + '/2',
        'KEY_PREFIX': 'sessions',
    }
}

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'sessions'
```

#### 4. CDN для статики и медиа

```python
# settings.py для production
STATICFILES_STORAGE = 'storages.backends.s3boto3.S3StaticStorage'
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

AWS_S3_CUSTOM_DOMAIN = 'cdn.yourdomain.com'
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}
```

---

## 🔐 НАСТРОЙКИ БЕЗОПАСНОСТИ ДЛЯ PRODUCTION

### Файл: settings.py — требуемые изменения

```python
# 1. ОБЯЗАТЕЛЬНО: Безопасный SECRET_KEY
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ImproperlyConfigured("SECRET_KEY environment variable required")

# 2. ОБЯЗАТЕЛЬНО: Whitelist ALLOWED_HOSTS
ALLOWED_HOSTS = ['yourdomain.com', 'www.yourdomain.com']
# УДАЛИТЬ: ALLOWED_HOSTS = ['*']  # ← ОПАСНО!

# 3. HTTPS настройки
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000  # 1 год
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# 4. Cookie безопасность
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# 5. Content Security Policy
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'", 'cdn.jsdelivr.net')
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", 'fonts.googleapis.com')
CSP_IMG_SRC = ("'self'", 'data:', 'blob:', '*.googleusercontent.com')
CSP_CONNECT_SRC = ("'self'", 'api.zoom.us', '*.yookassa.ru')

# 6. CORS ограничения
CORS_ALLOWED_ORIGINS = [
    'https://yourdomain.com',
    'https://www.yourdomain.com',
]
CORS_ALLOW_CREDENTIALS = True
```

---

## 📋 ЧЕКЛИСТ ПЕРЕД PRODUCTION

### Безопасность (КРИТИЧНО)

- [ ] Исправить Path Traversal в загрузке файлов
- [ ] Добавить валидацию владельца групп в apply_privacy
- [ ] Добавить проверку MIME-типа видео
- [ ] Настроить YOOKASSA_WEBHOOK_SECRET
- [ ] Скрыть zoom_start_url от студентов
- [ ] Валидировать student_ids в mark_attendance
- [ ] Убрать ALLOWED_HOSTS = ['*']
- [ ] Настроить HTTPS и secure cookies
- [ ] Удалить debug endpoints (/api/debug/env/)
- [ ] Заменить тестовые ключи reCAPTCHA

### Производительность

- [ ] Добавить prefetch_related в GroupViewSet
- [ ] Кешировать recurring lessons
- [ ] Добавить недостающие индексы БД
- [ ] Настроить Gunicorn workers для нагрузки
- [ ] Включить database connection pooling

### Мониторинг

- [ ] Настроить Sentry (SENTRY_DSN)
- [ ] Включить slow query logging (SQL_DEBUG=1 в dev)
- [ ] Добавить APM (New Relic / Datadog)
- [ ] Настроить алерты на 5xx ошибки

---

## 🧪 РЕКОМЕНДАЦИЯ: НАГРУЗОЧНОЕ ТЕСТИРОВАНИЕ

У вас есть [locustfile.py](teaching_panel/locustfile.py) — отлично!

### Сценарий тестирования:

```bash
# Запуск локально
cd teaching_panel
locust -f locustfile.py --host=http://127.0.0.1:8000

# Параметры для симуляции 10K пользователей
# Users: 1000 учителей + 3000 студентов = 4000
# Spawn rate: 100 users/sec
# Duration: 10 минут
```

### Метрики успеха:

| Метрика | Цель | Критично |
|---------|------|----------|
| p50 latency | < 100ms | < 500ms |
| p95 latency | < 300ms | < 1000ms |
| p99 latency | < 500ms | < 2000ms |
| Error rate | < 0.1% | < 1% |
| RPS | > 500 | > 100 |

---

## 📌 ПРИОРИТЕТЫ ИСПРАВЛЕНИЙ

### Неделя 1 (Критично)
1. ✅ Path Traversal в загрузке файлов
2. ✅ IDOR в apply_privacy
3. ✅ YooKassa webhook security
4. ✅ Проверка MIME-типа видео

### Неделя 2 (Важно)
5. Скрыть zoom_start_url от студентов
6. Валидация в mark_attendance
7. Production security settings

### Неделя 3 (Производительность)
8. Database индексы
9. Кеширование recurring lessons
10. Gunicorn optimization

---

**Дата аудита:** 11 декабря 2025  
**Аудитор:** GitHub Copilot (Claude Opus 4.5)  
**Версия проекта:** Teaching Panel LMS v1.0
