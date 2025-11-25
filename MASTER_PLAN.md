# 🎯 ЕДИНЫЙ ПЛАН РАБОТЫ - Teaching Panel LMS

## 📊 Распределение модулей

### 🟢 Модуль 1: Homework & Analytics
**Ответственный:** Напарник Tihon  
**Документация:** [`HOMEWORK_MODULE_SPEC.md`](./HOMEWORK_MODULE_SPEC.md)  
**Статус:** Ожидает начала работы

**Включает:**
- Журнал посещений группы
- Рейтинг студентов
- Конструктор домашних заданий (8 типов)
- Автопроверка
- Точки контроля (экзамены)
- Экспорт отчетов
- Геймификация

---

### 🔵 Модуль 2: Chat System  
**Ответственный:** Напарник #2  
**Документация:** [`CHAT_MODULE_SPEC.md`](./CHAT_MODULE_SPEC.md)  
**Статус:** Ожидает начала работы

**Включает:**
- Личные чаты (1-на-1)
- Групповые чаты
- WebSocket real-time
- Отправка файлов
- Уведомления
- Статусы онлайн/оффлайн

---

### 🟠 Модуль 3: Core + Zoom + Schedule
**Ответственный:** ТЫ  
**Документация:** [`CORE_MODULE_SPEC.md`](./CORE_MODULE_SPEC.md)  
**Статус:** Frontend готов ✅ · Backend ядро завершено ✅ · Zoom Pool v1 ✅ · Cosmos прототип ✅

**Включает:**
- Авторизация/Регистрация
- Управление группами
- Расписание занятий
- Zoom Pool System
- Посещаемость
- Календарь
- Навигация

---

## 🚀 ТВОЙ ПЛАН РАБОТЫ (Модуль Core)

### ✅ Что уже готово (Frontend):
1. ✅ Shared компоненты (Button, Modal, Input, Card, Badge)
2. ✅ LoginPage с валидацией
3. ✅ RegisterPage с анимацией успеха
4. ✅ Calendar с FullCalendar (3 вида просмотра)
5. ✅ ZoomPoolManager (управление аккаунтами)
6. ✅ StartLessonButton (авто создание Zoom)
7. ✅ App.js с роутами
8. ✅ NavBar с навигацией
9. ✅ React Dev Server работает на localhost:3000

---

## 🧪 Реализовано (Backend Core)

Основные части, запланированные ранее, выполнены:
1. Регистрация пользователей (эндпоинт `POST /api/jwt/register/`) с политикой пароля ✔️
2. Zoom Pool приложение (модель, сериализатор, ViewSet, admin, сидер) ✔️
3. Расширение модели `Lesson` новым полем `zoom_account` ✔️
4. Новый эндпоинт запуска урока `start-new` (использует пул) ✔️
5. Legacy `start` эндпоинт оставлен как fallback ✔️
6. Celery задачи: освобождение аккаунтов (legacy + новый пул), напоминания ✔️
7. Тесты для валидации уроков и `start-new` сценариев ✔️
8. Frontend интеграция: TeacherDashboard использует `start-new` с fallback ✔️
9. LessonAttendance показывает статус Zoom, ссылки Start/Join, email аккаунта ✔️
10. RecurringLessonsManage — генерация уроков без автосоздания Zoom ✔️
11. Сид-команда `seed_zoom_pool` для тестовых аккаунтов ✔️
12. Cosmos DB прототип: singleton клиент, репозитории, миграционный скрипт, гайд ✔️

## 📝 ТЕКУЩИЕ ДОПОЛНИТЕЛЬНЫЕ ЗАДАЧИ / УЛУЧШЕНИЯ

### Улучшения Core (опционально)
- [x] Добавить оптимистичный контроль версий (ETag) в Cosmos репозиториях
- [x] Диагностическое логирование медленных Cosmos запросов
- [ ] Расширить тесты: успешный цикл освобождения аккаунта после окончания урока
- [ ] Единый сервисный слой для Zoom (замена mock на реальный API)
- [ ] Обработка 429 и экспоненциальный retry для Zoom API

### Безопасность / Наблюдаемость
- [x] Rate-limit на запуск урока (3 попытки/минуту)
- [x] Логирование аудита (кто стартовал, когда, из какого IP)
- [ ] Метрики Celery задач (в Prometheus / custom endpoint)

### Следующие фичи Core (после стабилизации)
- [ ] Редактирование урока с пересозданием Zoom (при значимом переносе времени)
- [ ] Автовыбор свободного аккаунта с учётом teacher affinity (будущее поле)
- [ ] Архив Zoom встреч в отдельном хранилище (S3 + ссылка в LessonRecording)

## 🪐 Cosmos DB (Prototype)
Что уже сделано:
- Конфиг фича-флаг (`COSMOS_DB_ENABLED`)
- Singleton клиент `cosmos_db.py`
- Репозитории: Lessons, ZoomAccounts, Attendance
- Миграция `manage_cosmos_migration.py`
- Инструкция `COSMOS_EMULATOR_GUIDE.md`

План развития:
- [ ] Добавить контейнер `analyticsEvents`
- [ ] Перейти на иерархический ключ `/groupId/lessonDate` для крупных групп (миграционный скрипт)
- [ ] TTL для временных аналитических событий
- [ ] Batched bulk upsert для ускорения миграции
- [ ] Индексы (custom indexing policy) для полей `start_time`, `teacherId`

## 📝 (Исторический раздел) Исходный План Задач
Ниже сохранён для контекста исходный план (уже выполнено) и может быть удалён позднее.

## 📝 ТЕКУЩИЕ ЗАДАЧИ (Backend для Core модуля) — (история)

### Фаза 1: Регистрация и авторизация ⏰ 2-3 часа

#### 1.1 Endpoint регистрации
**Файл:** `teaching_panel/accounts/views.py`

**Что делать:**
- Добавить функцию `register_user()`
- Валидация email (уникальность)
- Валидация пароля (6+ символов, заглавная, строчная, цифра)
- Создание пользователя с ролью
- Обработка birth_date

**API:**
```
POST /api/jwt/register/
{
    "email": "user@example.com",
    "password": "Password123",
    "first_name": "Иван",
    "last_name": "Иванов",
    "role": "student",  # или "teacher"
    "birth_date": "2000-01-01"  # optional
}

Response 201:
{
    "detail": "Регистрация успешна"
}

Response 400:
{
    "detail": "Пользователь с таким email уже существует"
}
```

**Добавить в urls:**
```python
# accounts/urls.py
path('jwt/register/', register_user, name='register'),
```

---

#### 1.2 Проверка существующей авторизации
**Файл:** `teaching_panel/accounts/jwt_views.py`

**Проверить:**
- ✅ POST /api/jwt/create/ (логин) - уже работает?
- ✅ POST /api/jwt/refresh/ (обновление токена) - уже работает?
- ✅ POST /api/jwt/verify/ (проверка токена) - уже работает?

**Если не работает - починить.**

---

### Фаза 2: Zoom Pool System ⏰ 4-5 часов

#### 2.1 Создать Django приложение
```bash
cd teaching_panel
python manage.py startapp zoom_pool
```

**Добавить в INSTALLED_APPS:**
```python
# teaching_panel/settings.py
INSTALLED_APPS = [
    # ...
    'zoom_pool',
]
```

---

#### 2.2 Модель ZoomAccount
**Файл:** `teaching_panel/zoom_pool/models.py`

```python
from django.db import models
from django.utils import timezone

class ZoomAccount(models.Model):
    """Zoom аккаунт в пуле"""
    email = models.EmailField(unique=True)
    api_key = models.CharField(max_length=255)
    api_secret = models.CharField(max_length=255)
    zoom_user_id = models.CharField(max_length=255, blank=True)
    
    max_concurrent_meetings = models.IntegerField(default=1)
    current_meetings = models.IntegerField(default=0)
    
    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['current_meetings', '-last_used_at']
    
    def __str__(self):
        return f"{self.email} ({self.current_meetings}/{self.max_concurrent_meetings})"
    
    def is_available(self):
        """Проверка доступности аккаунта"""
        return self.is_active and self.current_meetings < self.max_concurrent_meetings
    
    def acquire(self):
        """Занять аккаунт"""
        if not self.is_available():
            raise ValueError('Аккаунт недоступен')
        self.current_meetings += 1
        self.last_used_at = timezone.now()
        self.save()
    
    def release(self):
        """Освободить аккаунт"""
        if self.current_meetings > 0:
            self.current_meetings -= 1
            self.save()
```

---

#### 2.3 Serializer
**Файл:** `teaching_panel/zoom_pool/serializers.py`

```python
from rest_framework import serializers
from .models import ZoomAccount

class ZoomAccountSerializer(serializers.ModelSerializer):
    is_available = serializers.SerializerMethodField()
    
    class Meta:
        model = ZoomAccount
        fields = [
            'id', 'email', 'api_key', 'api_secret', 'zoom_user_id',
            'max_concurrent_meetings', 'current_meetings',
            'is_active', 'last_used_at', 'is_available',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['current_meetings', 'last_used_at']
    
    def get_is_available(self, obj):
        return obj.is_available()
```

---

#### 2.4 ViewSet с endpoints
**Файл:** `teaching_panel/zoom_pool/views.py`

```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import ZoomAccount
from .serializers import ZoomAccountSerializer

class ZoomAccountViewSet(viewsets.ModelViewSet):
    queryset = ZoomAccount.objects.all()
    serializer_class = ZoomAccountSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        # Только учителя могут управлять Zoom аккаунтами
        if self.request.user.role != 'teacher':
            return []
        return super().get_permissions()
    
    @action(detail=True, methods=['post'])
    def release(self, request, pk=None):
        """Освободить аккаунт вручную"""
        account = self.get_object()
        account.release()
        return Response({
            'detail': 'Аккаунт освобожден',
            'current_meetings': account.current_meetings
        })
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Включить/выключить аккаунт"""
        account = self.get_object()
        account.is_active = not account.is_active
        account.save()
        return Response({
            'detail': 'Статус изменен',
            'is_active': account.is_active
        })
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Статистика пула"""
        total = ZoomAccount.objects.count()
        active = ZoomAccount.objects.filter(is_active=True).count()
        available = ZoomAccount.objects.filter(
            is_active=True,
            current_meetings__lt=models.F('max_concurrent_meetings')
        ).count()
        
        return Response({
            'total': total,
            'active': active,
            'available': available,
            'in_use': active - available
        })
```

---

#### 2.5 URLs
**Файл:** `teaching_panel/zoom_pool/urls.py`

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ZoomAccountViewSet

router = DefaultRouter()
router.register(r'', ZoomAccountViewSet, basename='zoom-account')

urlpatterns = [
    path('', include(router.urls)),
]
```

**Подключить в главный urls:**
```python
# teaching_panel/urls.py
urlpatterns = [
    # ...
    path('api/zoom-pool/', include('zoom_pool.urls')),
]
```

---

#### 2.6 Admin
**Файл:** `teaching_panel/zoom_pool/admin.py`

```python
from django.contrib import admin
from .models import ZoomAccount

@admin.register(ZoomAccount)
class ZoomAccountAdmin(admin.ModelAdmin):
    list_display = ['email', 'current_meetings', 'max_concurrent_meetings', 
                    'is_active', 'last_used_at']
    list_filter = ['is_active']
    search_fields = ['email']
    readonly_fields = ['current_meetings', 'last_used_at', 'created_at', 'updated_at']
```

---

#### 2.7 Миграции
```bash
cd teaching_panel
python manage.py makemigrations zoom_pool
python manage.py migrate
```

---

### Фаза 3: Интеграция с уроками ⏰ 3-4 часа

#### 3.1 Endpoint для старта урока
**Файл:** `teaching_panel/schedule/views.py`

**Добавить метод в `LessonViewSet`:**

```python
from zoom_pool.models import ZoomAccount
from django.db import transaction

@action(detail=True, methods=['post'])
def start_lesson(self, request, pk=None):
    """
    Начать урок - выделить Zoom аккаунт и создать встречу
    
    POST /api/schedule/lessons/{id}/start/
    
    Response 200:
    {
        "zoom_join_url": "https://zoom.us/j/...",
        "zoom_start_url": "https://zoom.us/s/...",
        "zoom_meeting_id": "123456789",
        "zoom_password": "abc123",
        "account_email": "teacher1@zoom.com"
    }
    
    Response 503:
    {
        "detail": "Все Zoom аккаунты заняты. Попробуйте позже."
    }
    """
    lesson = self.get_object()
    
    # Проверка прав (только учитель группы)
    if lesson.group.teacher != request.user:
        return Response(
            {'detail': 'У вас нет прав на этот урок'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Проверка времени (можно стартовать за 15 мин до начала)
    from django.utils import timezone
    now = timezone.now()
    if lesson.start_time - timezone.timedelta(minutes=15) > now:
        return Response(
            {'detail': 'Урок можно начать за 15 минут до начала'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Если уже есть Zoom встреча - вернуть её
    if lesson.zoom_meeting_id:
        return Response({
            'zoom_join_url': lesson.zoom_join_url,
            'zoom_start_url': lesson.zoom_start_url,
            'zoom_meeting_id': lesson.zoom_meeting_id,
            'zoom_password': lesson.zoom_password,
            'account_email': 'Уже создана'
        })
    
    # Найти свободный Zoom аккаунт
    with transaction.atomic():
        zoom_account = ZoomAccount.objects.select_for_update().filter(
            is_active=True,
            current_meetings__lt=models.F('max_concurrent_meetings')
        ).first()
        
        if not zoom_account:
            return Response(
                {'detail': 'Все Zoom аккаунты заняты. Попробуйте позже.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        # Занять аккаунт
        zoom_account.acquire()
        
        # Создать Zoom встречу (используй существующий zoom_client)
        from .zoom_client import create_zoom_client
        zoom_client = create_zoom_client(zoom_account)
        
        meeting_data = zoom_client.create_meeting(
            topic=f"{lesson.group.name} - {lesson.title}",
            start_time=lesson.start_time,
            duration=lesson.duration_minutes
        )
        
        # Сохранить данные в урок
        lesson.zoom_meeting_id = meeting_data['id']
        lesson.zoom_join_url = meeting_data['join_url']
        lesson.zoom_start_url = meeting_data['start_url']
        lesson.zoom_password = meeting_data.get('password', '')
        lesson.zoom_account = zoom_account
        lesson.save()
    
    return Response({
        'zoom_join_url': lesson.zoom_join_url,
        'zoom_start_url': lesson.zoom_start_url,
        'zoom_meeting_id': lesson.zoom_meeting_id,
        'zoom_password': lesson.zoom_password,
        'account_email': zoom_account.email
    })
```

---

#### 3.2 Обновить модель Lesson
**Файл:** `teaching_panel/schedule/models.py`

**Добавить поле в модель `Lesson`:**

```python
from zoom_pool.models import ZoomAccount

class Lesson(models.Model):
    # ... существующие поля ...
    
    # Добавить:
    zoom_account = models.ForeignKey(
        ZoomAccount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lessons'
    )
```

**Миграция:**
```bash
python manage.py makemigrations schedule
python manage.py migrate
```

---

#### 3.3 Celery задача для освобождения аккаунтов
**Файл:** `teaching_panel/schedule/tasks.py`

**Добавить:**

```python
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from zoom_pool.models import ZoomAccount

@shared_task
def release_finished_zoom_accounts():
    """
    Освобождает Zoom аккаунты, где все встречи закончились
    Запускается каждые 5 минут
    """
    now = timezone.now()
    
    # Найти все занятые аккаунты
    busy_accounts = ZoomAccount.objects.filter(current_meetings__gt=0)
    
    for account in busy_accounts:
        # Найти все активные уроки этого аккаунта
        active_lessons = account.lessons.filter(
            start_time__lte=now,
            start_time__gte=now - timedelta(hours=3)  # уроки за последние 3 часа
        )
        
        # Проверить, закончились ли все уроки
        all_finished = True
        for lesson in active_lessons:
            lesson_end = lesson.start_time + timedelta(minutes=lesson.duration_minutes)
            if lesson_end > now:
                all_finished = False
                break
        
        # Если все закончились - освободить аккаунт
        if all_finished and active_lessons.count() > 0:
            releases = min(account.current_meetings, active_lessons.count())
            for _ in range(releases):
                account.release()
            
            print(f"Released {releases} meetings from {account.email}")
```

**Добавить в Celery Beat:**
```python
# teaching_panel/celery.py

app.conf.beat_schedule = {
    # ... существующие задачи ...
    
    'release-finished-zoom-accounts': {
        'task': 'schedule.tasks.release_finished_zoom_accounts',
        'schedule': crontab(minute='*/5'),  # Каждые 5 минут
    },
}
```

---

### Фаза 4: Улучшение существующих компонентов ⏰ 2 часа

#### 4.1 Обновить RecurringLessonsManage
**Что добавить:**
- При создании урока НЕ создавать Zoom встречу сразу
- Zoom встреча создается только при клике "Начать урок"
- Добавить кнопку "Начать урок" в список уроков

#### 4.2 Обновить LessonAttendance
**Что добавить:**
- Показывать статус Zoom встречи (создана/не создана)
- Добавить ссылку Join для студентов
- Добавить ссылку Start для учителя

---

### Фаза 5: Тестирование и отладка ⏰ 2 часа

#### 5.1 Создать тестовые данные
```bash
cd teaching_panel
python manage.py shell
```

```python
from zoom_pool.models import ZoomAccount

# Создать тестовые Zoom аккаунты
ZoomAccount.objects.create(
    email='zoom1@test.com',
    api_key='test_key_1',
    api_secret='test_secret_1',
    max_concurrent_meetings=2
)

ZoomAccount.objects.create(
    email='zoom2@test.com',
    api_key='test_key_2',
    api_secret='test_secret_2',
    max_concurrent_meetings=1
)
```

#### 5.2 Тестовые сценарии

**Сценарий 1: Регистрация**
1. Открыть http://localhost:3000/register
2. Заполнить форму
3. Проверить валидацию пароля
4. Зарегистрироваться
5. Проверить редирект на /login

**Сценарий 2: Zoom Pool**
1. Войти как teacher
2. Открыть /zoom-pool
3. Проверить статистику (total, active, available)
4. Добавить новый аккаунт
5. Изменить статус (active/inactive)
6. Удалить аккаунт

**Сценарий 3: Начать урок**
1. Войти как teacher
2. Открыть /calendar
3. Создать новый урок (или выбрать существующий)
4. Кликнуть "Начать урок" (StartLessonButton)
5. Проверить модальное окно с Zoom ссылками
6. Скопировать ссылку
7. Проверить в БД что zoom_account занят (current_meetings = 1)

**Сценарий 4: Освобождение аккаунта**
1. Подождать 5+ минут после окончания урока
2. Проверить что Celery задача сработала
3. Проверить в БД что current_meetings = 0

---

## 📊 ОБЩАЯ ОЦЕНКА ВРЕМЕНИ

### Модуль Core (Твой):
- ✅ Frontend готов: 8 часов (уже сделано)
- ⏰ Backend регистрация: 2-3 часа
- ⏰ Backend Zoom Pool: 4-5 часов
- ⏰ Backend интеграция с уроками: 3-4 часа
- ⏰ Улучшения UI: 2 часа
- ⏰ Тестирование: 2 часа

**ИТОГО для тебя: ~13-16 часов работы** (Backend часть)

---

### Модуль Homework & Analytics (Tihon):
- Frontend: 15-20 часов
- Backend (уже готов): 0 часов
- Тестирование: 3-4 часа

**ИТОГО для Tihon: ~18-24 часа**

---

### Модуль Chat (Напарник #2):
- Frontend: 12-15 часов
- Backend WebSocket: 8-10 часов
- Тестирование: 3-4 часа

**ИТОГО для Напарника #2: ~23-29 часов**

---

## 🎯 СЛЕДУЮЩИЙ ШАГ - НАЧИНАЕМ!

### Что делаю прямо сейчас:

1. ✅ Создать приложение `zoom_pool`
2. ✅ Создать модель `ZoomAccount`
3. ✅ Создать Serializer
4. ✅ Создать ViewSet с endpoints
5. ✅ Настроить URLs
6. ✅ Запустить миграции
7. ✅ Добавить endpoint регистрации
8. ✅ Обновить модель Lesson (добавить zoom_account)
9. ✅ Создать endpoint start_lesson
10. ✅ Создать Celery задачу
11. ✅ Тестирование

---

## ✅ Актуальный Checklist Прогресса

### Backend Core
- [x] Регистрация пользователей (POST /api/jwt/register/)
- [x] Zoom Pool приложение создано
- [x] Модель ZoomAccount + admin + сидер
- [x] CRUD / stats / toggle / release endpoints
- [x] Endpoint start_lesson (legacy) + start-new (pool)
- [x] Celery задачи освобождения (legacy + pool) и напоминания
- [x] Миграции выполнены
- [x] Тестовые данные (сидер + sample уроки)
- [x] Интеграция Frontend ↔ Backend (TeacherDashboard, Attendance, RecurringLessons)
- [x] Тесты (валидация уроков, recurring expansion, start-new сценарии)
- [x] Cosmos DB прототип (клиент, репы, миграция, гайд)

### Frontend Core
- [x] Shared компоненты
- [x] LoginPage
- [x] RegisterPage
- [x] Calendar (FullCalendar, виртуальные recurring события)
- [x] ZoomPoolManager
- [x] StartLessonButton / интеграция start-new
- [x] Навигация и дашборды (преподаватель/студент)
- [x] Attendance модалка со статусом Zoom

### Дополнительно (готово)
- [x] RecurringLessonsManage: генерация без авто Zoom
- [x] Система throttle при запуске урока (базовая)

### Pending / Next
- [ ] Cosmos ETag / оптимистичный апдейт
- [ ] Расширение логирования и метрик
- [ ] Реальный Zoom API клиент
- [ ] AnalyticsEvents контейнер
- [ ] Расширенные UI индикаторы занятого аккаунта

---

## 🚦 КРИТЕРИИ ГОТОВНОСТИ

### Модуль считается готовым когда:
1. ✅ Все endpoints работают без ошибок
2. ✅ Frontend корректно отображает данные
3. ✅ Все формы валидируются
4. ✅ Celery задачи выполняются по расписанию
5. ✅ Нет критических багов
6. ✅ Документация обновлена

---

## 🎉 УСПЕХ!

После завершения всех модулей:
1. Merge всех веток в `develop`
2. Полное тестирование интеграции
3. Деплой на production сервер
4. Презентация заказчику

---

**Готов начинать?** 🚀
