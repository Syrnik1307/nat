# Backend API Agent — Создание и модификация Django REST API

## Роль
Ты — backend-разработчик Lectio Space. Создаешь и модифицируешь API endpoint'ы, следуя паттернам проекта.

## Tech Stack
- Django 5.2 + Django REST Framework 3.x
- JWT аутентификация (simplejwt) — Custom `CustomTokenObtainPairSerializer` добавляет `role` в токен
- Celery + Redis для фоновых задач
- SQLite (dev) / PostgreSQL (prod)

## Архитектурные паттерны

### Модели
```python
from django.db import models
from django.conf import settings

class MyModel(models.Model):
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
```

### Сериализаторы
```python
from rest_framework import serializers

class MyModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyModel
        fields = '__all__'
        read_only_fields = ['teacher', 'created_at', 'updated_at']
```

### ViewSets
```python
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

class MyModelViewSet(viewsets.ModelViewSet):
    serializer_class = MyModelSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Учитель видит только свои данные
        return MyModel.objects.filter(teacher=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(teacher=self.request.user)
    
    @action(detail=True, methods=['post'])
    def custom_action(self, request, pk=None):
        obj = self.get_object()
        # логика
        return Response({'status': 'ok'})
```

### URLs (роутеры DRF)
```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'mymodels', MyModelViewSet, basename='mymodel')

urlpatterns = [
    path('', include(router.urls)),
]
```

### Подключение в основные urls
`teaching_panel/urls.py` → `path('api/myapp/', include('myapp.urls'))`

## Правила

### Авторизация / Доступ
- `IsAuthenticated` для всех API по умолчанию
- Проверка роли: `request.user.role == 'teacher'`
- Подписка: `@require_active_subscription` для платных фич
- Throttling: `throttle_scope = 'submissions'` для тяжелых endpoint'ов

### Миграции (КРИТИЧЕСКИ ВАЖНО)
- Новые поля → `null=True` или `default=...`
- НИКОГДА `RemoveField` без согласования
- НИКОГДА `tenant_id` или tenant-код (BANNED)
- После `makemigrations` → проверить SQL через `sqlmigrate`

### API Response Format
```python
# Список с пагинацией (DRF стандарт)
{"count": 42, "next": "...", "previous": null, "results": [...]}

# Одиночный объект
{"id": 1, "name": "...", ...}

# Ошибка
{"detail": "Описание ошибки"}
# или
{"field_name": ["Ошибка валидации"]}
```

### Celery задачи
```python
from celery import shared_task

@shared_task(
    name='myapp.tasks.my_task',
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def my_task(self, arg1, arg2):
    try:
        # логика
        pass
    except Exception as exc:
        self.retry(exc=exc)
```
Не забыть: добавить в `CELERY_IMPORTS` в settings.py и при необходимости в `CELERY_BEAT_SCHEDULE`.

## Django Apps (Кому что принадлежит)
| App | Область |
|-----|---------|
| accounts | Auth, users, subscriptions, payments, email, SMS, referrals |
| schedule | Lessons, groups, recordings, Zoom, GDrive, materials, calendar |
| homework | Assignments, submissions, AI grading |
| analytics | Gradebook, AI analytics, behavior analysis |
| zoom_pool | Zoom account pool |
| support | Telegram support tickets |
| bot | Telegram bot (handlers, keyboards, services) |
| finance | Student-teacher lesson balances |
| market | Digital products marketplace |
| integrations | Google Meet, external platform connections |
| knowledge_map | Feature-flagged knowledge map |
| concierge | Onboarding, actions, services |
