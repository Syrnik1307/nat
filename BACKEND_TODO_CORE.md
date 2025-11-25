# 🔧 Backend TODO для модуля Core

## Приоритетные API endpoints для реализации

### 1. Регистрация пользователей ✅ ВЫСОКИЙ ПРИОРИТЕТ

**Файл:** `teaching_panel/accounts/views.py`

```python
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()

@api_view(['POST'])
def register_user(request):
    """
    Регистрация нового пользователя
    
    POST /api/jwt/register/
    {
        "email": "user@example.com",
        "password": "Password123",
        "first_name": "Иван",
        "last_name": "Иванов",
        "role": "student",  # или "teacher"
        "birth_date": "2000-01-01"  # optional
    }
    """
    email = request.data.get('email')
    password = request.data.get('password')
    first_name = request.data.get('first_name')
    last_name = request.data.get('last_name')
    role = request.data.get('role', 'student')
    birth_date = request.data.get('birth_date')
    
    # Валидация
    if User.objects.filter(email=email).exists():
        return Response(
            {'detail': 'Пользователь с таким email уже существует'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Создание пользователя
    user = User.objects.create_user(
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        role=role
    )
    
    if birth_date:
        user.birth_date = birth_date
        user.save()
    
    return Response(
        {'detail': 'Регистрация успешна'},
        status=status.HTTP_201_CREATED
    )
```

**Добавить в urls.py:**
```python
# accounts/urls.py
from .views import register_user

urlpatterns = [
    # ...
    path('jwt/register/', register_user, name='register'),
]
```

---

### 2. Zoom Pool System ✅ ВЫСОКИЙ ПРИОРИТЕТ

**Создать новое приложение:**
```bash
cd teaching_panel
python manage.py startapp zoom_pool
```

**Модель:** `teaching_panel/zoom_pool/models.py`

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

**ViewSet:** `teaching_panel/zoom_pool/views.py`

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
    
    @action(detail=True, methods=['post'])
    def release(self, request, pk=None):
        """Освободить аккаунт вручную"""
        account = self.get_object()
        account.release()
        return Response({'detail': 'Аккаунт освобожден'})
    
    @action(detail=False, methods=['get'])
    def get_available(self, request):
        """Получить первый доступный аккаунт"""
        account = ZoomAccount.objects.filter(
            is_active=True,
            current_meetings__lt=models.F('max_concurrent_meetings')
        ).first()
        
        if not account:
            return Response(
                {'detail': 'Нет доступных аккаунтов'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        serializer = self.get_serializer(account)
        return Response(serializer.data)
```

**Serializer:** `teaching_panel/zoom_pool/serializers.py`

```python
from rest_framework import serializers
from .models import ZoomAccount

class ZoomAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = ZoomAccount
        fields = [
            'id', 'email', 'zoom_user_id', 
            'max_concurrent_meetings', 'current_meetings',
            'is_active', 'last_used_at'
        ]
        read_only_fields = ['current_meetings', 'last_used_at']
    
    # API Key и Secret не возвращаем в response для безопасности
```

**URLs:** `teaching_panel/zoom_pool/urls.py`

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ZoomAccountViewSet

router = DefaultRouter()
router.register(r'', ZoomAccountViewSet, basename='zoom-pool')

urlpatterns = [
    path('', include(router.urls)),
]
```

**Добавить в main urls:**
```python
# teaching_panel/urls.py
urlpatterns = [
    # ...
    path('api/zoom-pool/', include('zoom_pool.urls')),
]
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

### 3. Старт занятия с автоматическим Zoom ✅ ВЫСОКИЙ ПРИОРИТЕТ

**Файл:** `teaching_panel/schedule/views.py`

```python
from rest_framework.decorators import action
from zoom_pool.models import ZoomAccount
from core.zoom_service import create_zoom_meeting

class LessonViewSet(viewsets.ModelViewSet):
    # ... существующий код ...
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """
        Начать занятие с автоматическим созданием Zoom встречи
        
        POST /api/schedule/lessons/{id}/start/
        
        Response:
        {
            "zoom_join_url": "https://zoom.us/j/123456789",
            "zoom_start_url": "https://zoom.us/s/123456789?zak=...",
            "zoom_meeting_id": "123456789",
            "zoom_password": "abc123"
        }
        """
        lesson = self.get_object()
        
        # Проверка: уже есть Zoom встреча?
        if lesson.zoom_meeting_id:
            return Response({
                'zoom_join_url': lesson.zoom_join_url,
                'zoom_start_url': lesson.zoom_start_url,
                'zoom_meeting_id': lesson.zoom_meeting_id,
                'zoom_password': lesson.zoom_password,
            })
        
        # Получить свободный Zoom аккаунт из пула
        zoom_account = ZoomAccount.objects.filter(
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
        
        try:
            # Создать Zoom встречу
            meeting_data = create_zoom_meeting(
                api_key=zoom_account.api_key,
                api_secret=zoom_account.api_secret,
                topic=f"Занятие {lesson.group.name}",
                start_time=lesson.start_time,
                duration=lesson.duration_minutes,
            )
            
            # Сохранить данные встречи в урок
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
            })
            
        except Exception as e:
            # Освободить аккаунт при ошибке
            zoom_account.release()
            return Response(
                {'detail': f'Ошибка создания встречи: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
```

**Добавить поле в модель Lesson:**
```python
# schedule/models.py
from zoom_pool.models import ZoomAccount

class Lesson(models.Model):
    # ... существующие поля ...
    
    zoom_account = models.ForeignKey(
        ZoomAccount, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='lessons'
    )
    zoom_password = models.CharField(max_length=50, blank=True)
```

**Миграции:**
```bash
python manage.py makemigrations
python manage.py migrate
```

---

### 4. Восстановление пароля ✅ СРЕДНИЙ ПРИОРИТЕТ

**Файл:** `teaching_panel/accounts/views.py`

```python
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

@api_view(['POST'])
def reset_password(request):
    """
    Отправить ссылку для восстановления пароля
    
    POST /api/auth/reset-password/
    {
        "email": "user@example.com"
    }
    """
    email = request.data.get('email')
    
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        # Не раскрываем, что пользователь не существует
        return Response({'detail': 'Если email существует, ссылка будет отправлена'})
    
    # Генерация токена
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    
    # Формирование ссылки
    reset_url = f"http://localhost:3000/reset-password/{uid}/{token}/"
    
    # Отправка email
    send_mail(
        subject='Восстановление пароля',
        message=f'Перейдите по ссылке для восстановления пароля: {reset_url}',
        from_email='noreply@teaching-panel.com',
        recipient_list=[email],
        fail_silently=False,
    )
    
    return Response({'detail': 'Ссылка для восстановления отправлена на email'})
```

---

### 5. Celery задача для автоосвобождения Zoom аккаунтов

**Файл:** `teaching_panel/schedule/tasks.py`

```python
from celery import shared_task
from django.utils import timezone
from .models import Lesson

@shared_task
def release_finished_zoom_accounts():
    """
    Освободить Zoom аккаунты для завершенных занятий
    Запускать каждые 5 минут
    """
    now = timezone.now()
    
    # Найти все занятия, которые закончились
    finished_lessons = Lesson.objects.filter(
        end_time__lt=now,
        zoom_account__isnull=False,
        status__in=['scheduled', 'in_progress']
    )
    
    for lesson in finished_lessons:
        if lesson.zoom_account:
            lesson.zoom_account.release()
            lesson.status = 'completed'
            lesson.save()
    
    return f'Освобождено {finished_lessons.count()} аккаунтов'
```

**Добавить в Celery Beat:**
```python
# teaching_panel/celery.py
from celery.schedules import crontab

app.conf.beat_schedule = {
    # ... существующие задачи ...
    
    'release-finished-zoom-accounts': {
        'task': 'schedule.tasks.release_finished_zoom_accounts',
        'schedule': crontab(minute='*/5'),  # Каждые 5 минут
    },
}
```

---

## 📋 Чеклист реализации Backend

- [ ] **1. Регистрация:**
  - [ ] Создать view `register_user`
  - [ ] Добавить URL `POST /api/jwt/register/`
  - [ ] Валидация данных
  - [ ] Хеширование пароля

- [ ] **2. Zoom Pool:**
  - [ ] Создать приложение `zoom_pool`
  - [ ] Создать модель `ZoomAccount`
  - [ ] Создать serializer
  - [ ] Создать ViewSet
  - [ ] Добавить URLs
  - [ ] Миграции

- [ ] **3. Старт занятия:**
  - [ ] Добавить поле `zoom_account` в `Lesson`
  - [ ] Создать action `start` в `LessonViewSet`
  - [ ] Интеграция с Zoom API
  - [ ] Обработка ошибок

- [ ] **4. Восстановление пароля:**
  - [ ] View для отправки email
  - [ ] View для сброса пароля по токену
  - [ ] Настройка SMTP в settings.py

- [ ] **5. Celery задачи:**
  - [ ] Задача освобождения Zoom аккаунтов
  - [ ] Добавить в Beat schedule

---

## 🚀 Быстрый старт

### 1. Создать приложение Zoom Pool
```bash
cd teaching_panel
python manage.py startapp zoom_pool
```

### 2. Скопировать код моделей и views выше

### 3. Добавить в INSTALLED_APPS
```python
# settings.py
INSTALLED_APPS = [
    # ...
    'zoom_pool',
]
```

### 4. Миграции
```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Создать супер-пользователя для тестирования Zoom Pool
```bash
python manage.py createsuperuser
```

### 6. Добавить тестовый Zoom аккаунт через Django Admin
```
http://127.0.0.1:8000/admin/zoom_pool/zoomaccount/add/
```

---

**Приоритет реализации:**
1. ✅ Zoom Pool (самое важное для занятий)
2. ✅ Старт занятия
3. ✅ Регистрация
4. Восстановление пароля (можно потом)
