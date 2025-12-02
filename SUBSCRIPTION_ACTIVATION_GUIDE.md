# Руководство по активации подписок

## Быстрая активация подписки

### Через management command (рекомендуется)

```bash
# На сервере
ssh tp
cd /var/www/teaching_panel/teaching_panel
source /var/www/teaching_panel/venv/bin/activate

# Активация по email (365 дней)
python manage.py activate_subscription --email user@example.com --days 365

# Активация по Telegram ID (30 дней)
python manage.py activate_subscription --telegram-id 123456789 --days 30
```

### Через Django shell

```bash
ssh tp
cd /var/www/teaching_panel/teaching_panel
source /var/www/teaching_panel/venv/bin/activate
python manage.py shell
```

```python
from accounts.models import CustomUser, Subscription
from django.utils import timezone
from datetime import timedelta

# Найти пользователя
u = CustomUser.objects.get(email='user@example.com')
# или
u = CustomUser.objects.get(telegram_id='123456789')

# Получить или создать подписку
s, created = Subscription.objects.get_or_create(user=u)

# Активировать на год
s.status = Subscription.STATUS_ACTIVE
s.expires_at = timezone.now() + timedelta(days=365)
s.save()

print(f'Subscription activated until {s.expires_at}')
print(f'Is active: {s.is_active()}')
```

## Проверка подписки

### Через API

```bash
# Получить токен
curl -X POST http://72.56.81.163/api/jwt/token/ \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}'

# Проверить доступ к записям
curl http://72.56.81.163/schedule/api/recordings/teacher/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Через Django shell

```python
from accounts.models import CustomUser
u = CustomUser.objects.get(email='user@example.com')
print(f'Has subscription: {hasattr(u, "subscription")}')
if hasattr(u, 'subscription'):
    s = u.subscription
    print(f'Status: {s.status}')
    print(f'Expires: {s.expires_at}')
    print(f'Is active: {s.is_active()}')
```

## Частые проблемы

### "Подписка не активна" при наличии подписки в админке

**Причина**: Статус подписки `pending` или `expires_at` в прошлом

**Решение**:
```bash
python manage.py activate_subscription --email user@example.com --days 365
```

### Подписка не создаётся автоматически

**Причина**: Триальная подписка создаётся только при первом действии, требующем подписку

**Решение**: Создать вручную через management command или админку

## Логика проверки подписки (для разработчиков)

### Метод `is_active()`

```python
# accounts/models.py::Subscription
def is_active(self):
    return self.status == self.STATUS_ACTIVE and self.expires_at > timezone.now()
```

**Требования**:
- `status` == `'active'`
- `expires_at` > текущее время

### Декоратор `@require_active_subscription`

Используется в endpoints для блокировки доступа без активной подписки:

```python
# teaching_panel/schedule/views.py
from accounts.subscriptions_utils import require_active_subscription

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_recording(request):
    try:
        require_active_subscription(request.user)
    except Exception as e:
        return Response({'detail': str(e)}, status=403)
    # ... rest of the code
```

**Endpoints с проверкой подписки**:
- `POST /schedule/api/lessons/<id>/start/`
- `POST /schedule/api/lessons/<id>/start-new/`
- `POST /schedule/api/lessons/upload_standalone_recording/`
- `GET /schedule/api/recordings/teacher/`

## Массовая активация

```python
# Активировать всех учителей на год
from accounts.models import CustomUser, Subscription
from django.utils import timezone
from datetime import timedelta

teachers = CustomUser.objects.filter(role='teacher')
for t in teachers:
    s, created = Subscription.objects.get_or_create(user=t)
    s.status = Subscription.STATUS_ACTIVE
    s.expires_at = timezone.now() + timedelta(days=365)
    s.save()
    print(f'Activated: {t.email}')
```

---

**Дата создания**: 2 декабря 2025  
**Версия**: 1.0
