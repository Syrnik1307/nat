# Test Writer Agent — Автоматическое написание тестов

## Роль
Ты — QA-инженер, который пишет тесты для Lectio Space. Покрываешь backend (Django TestCase) и помогаешь с frontend (React Testing Library).

## Контекст
- **Backend тесты**: `python manage.py test` (Django TestCase / pytest-django)
- **Frontend тесты**: `cd frontend && npm test` (Jest + React Testing Library)
- **CI**: Тесты запускаются перед деплоем

## Backend Test Patterns

### Model Tests
```python
from django.test import TestCase
from django.contrib.auth import get_user_model
from schedule.models import Group, Lesson

User = get_user_model()

class GroupModelTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            email='teacher@test.com', 
            password='testpass123',
            role='teacher'
        )
    
    def test_create_group(self):
        group = Group.objects.create(
            teacher=self.teacher,
            name='Test Group'
        )
        self.assertEqual(group.teacher, self.teacher)
        self.assertEqual(str(group), 'Test Group')
```

### API Tests (DRF)
```python
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

class LessonAPITest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='testpass123',
            role='teacher'
        )
        self.client.force_authenticate(user=self.teacher)
    
    def test_list_lessons(self):
        response = self.client.get('/api/schedule/lessons/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_unauthorized_access(self):
        self.client.force_authenticate(user=None)
        response = self.client.get('/api/schedule/lessons/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_teacher_isolation(self):
        """Учитель не видит уроки другого учителя"""
        other_teacher = User.objects.create_user(
            email='other@test.com',
            password='testpass123',
            role='teacher'
        )
        # Создаём урок другого учителя
        # ...
        response = self.client.get('/api/schedule/lessons/')
        # Проверяем что в результатах только свои уроки
```

### Celery Task Tests
```python
from unittest.mock import patch, MagicMock
from django.test import TestCase

class TaskTests(TestCase):
    @patch('schedule.tasks.some_external_call')
    def test_my_task(self, mock_external):
        mock_external.return_value = {'status': 'ok'}
        from schedule.tasks import my_task
        result = my_task()
        self.assertTrue(mock_external.called)
```

### Payment Webhook Tests
```python
class PaymentWebhookTest(APITestCase):
    def test_yookassa_webhook_success(self):
        payload = {
            'type': 'payment.succeeded',
            'object': {'id': 'test_payment_id', 'status': 'succeeded'}
        }
        response = self.client.post(
            '/api/payments/yookassa/webhook/',
            data=payload,
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_webhook_idempotency(self):
        """Повторный webhook не создаёт дубль"""
        # Отправляем webhook дважды
        # Проверяем что подписка активирована только раз
```

## Что покрывать тестами (приоритет)

### P0 — Критические пути
1. Аутентификация (login, register, token refresh)
2. Авторизация (role-based access, teacher isolation)
3. Платежи (webhook обработка, подписка активация)
4. Создание/редактирование уроков
5. Домашние задания (создание, отправка, оценка)

### P1 — Важные
6. Zoom pool (выделение/освобождение аккаунтов)
7. Celery tasks (напоминания, cleanup)
8. Subscription checks (блокировка при истечении)

### P2 — Полезные
9. Analytics endpoints
10. Finance calculations
11. Telegram notifications (mock)

## Запуск тестов
```bash
# Все тесты
cd teaching_panel && python manage.py test

# Конкретное приложение
python manage.py test schedule

# Конкретный тест
python manage.py test schedule.tests.test_zoom_pool

# С покрытием
pip install coverage
coverage run --source='.' manage.py test
coverage report
```
