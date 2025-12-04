# 🚀 Zoom API Quick Start Guide

## Быстрый запуск урока на проде

### URL: http://72.56.81.163

---

## 1️⃣ Способ 1: Через пул Zoom аккаунтов (рекомендуется)

**API Endpoint:**
```http
POST /api/schedule/lessons/{lesson_id}/start-new/
Authorization: Bearer {your_access_token}
```

**Ответ:**
```json
{
  "zoom_start_url": "https://zoom.us/s/...",
  "zoom_join_url": "https://zoom.us/j/...",
  "zoom_meeting_id": "86598602441",
  "zoom_password": "849208",
  "account_email": "test.zoom@teachpanel.com"
}
```

**Frontend:**
```javascript
import { startLessonNew } from '../apiService';

const response = await startLessonNew(lessonId);
window.open(response.data.zoom_start_url, '_blank');
```

---

## 2️⃣ Способ 2: Быстрый старт без расписания

**API Endpoint:**
```http
POST /api/schedule/lessons/quick-start/
Authorization: Bearer {your_access_token}
Content-Type: application/json

{
  "title": "Экспресс урок",
  "duration": 60,
  "group_id": 123
}
```

**Frontend:**
```javascript
import { startQuickLesson } from '../apiService';

const response = await startQuickLesson({
  title: 'Быстрый урок',
  duration: 60,
  group_id: groupId
});
window.open(response.data.zoom_start_url, '_blank');
```

---

## 3️⃣ Способ 3: Персональные credentials учителя

**Требования:**
- У учителя должны быть заполнены поля:
  - `zoom_account_id`
  - `zoom_client_id`
  - `zoom_client_secret`

**API Endpoint:**
```http
POST /api/schedule/lessons/{lesson_id}/start/
Authorization: Bearer {your_access_token}
```

---

## 🔧 Zoom Client в коде

**Файл:** `teaching_panel/schedule/zoom_client.py`

```python
from schedule.zoom_client import my_zoom_api_client

# Создать встречу
meeting_data = my_zoom_api_client.create_meeting(
    user_id='me',
    topic='Урок математики',
    start_time=datetime.now(),
    duration=60
)

# Результат
{
    'id': '86598602441',
    'start_url': 'https://zoom.us/s/...',
    'join_url': 'https://zoom.us/j/...',
    'password': '849208'
}

# Завершить встречу
my_zoom_api_client.end_meeting(meeting_id)
```

---

## 🗄️ Zoom Pool модели

**Файл:** `teaching_panel/zoom_pool/models.py`

```python
from zoom_pool.models import ZoomAccount

# Получить свободный аккаунт
free_account = ZoomAccount.objects.filter(
    is_active=True,
    current_meetings__lt=F('max_concurrent_meetings')
).first()

# Захватить аккаунт
free_account.acquire()  # current_meetings += 1

# Освободить аккаунт
free_account.release()  # current_meetings -= 1
```

---

## 🎯 Проверка на проде

### Проверить Zoom аккаунты в пуле

```bash
ssh tp
cd /var/www/teaching_panel/teaching_panel
source ../venv/bin/activate

python manage.py shell -c "
from zoom_pool.models import ZoomAccount
print('Zoom accounts:', ZoomAccount.objects.count())
for acc in ZoomAccount.objects.all():
    print(f'  {acc.email}: meetings={acc.current_meetings}/{acc.max_concurrent_meetings}')
"
```

### Проверить Zoom credentials

```bash
python manage.py shell -c "
from django.conf import settings
print('ZOOM_ACCOUNT_ID:', settings.ZOOM_ACCOUNT_ID)
print('ZOOM_CLIENT_ID:', settings.ZOOM_CLIENT_ID)
"
```

### Протестировать Zoom API

```bash
python manage.py shell
from schedule.zoom_client import my_zoom_api_client

# Получить токен
token = my_zoom_api_client._get_access_token()
print(f'Token: {token[:20]}...')

# Создать тестовую встречу
from datetime import datetime
meeting = my_zoom_api_client.create_meeting(
    user_id='me',
    topic='Test Meeting',
    start_time=datetime.now(),
    duration=30
)
print(f'Meeting ID: {meeting["id"]}')
print(f'Start URL: {meeting["start_url"]}')
```

---

## 🚨 Troubleshooting

### Ошибка: "Все Zoom аккаунты заняты"

**Решение:**
```bash
python manage.py shell
from zoom_pool.models import ZoomAccount
# Освободить все
ZoomAccount.objects.all().update(current_meetings=0)
```

### Ошибка: 401 Unauthorized от Zoom API

**Причины:**
1. Невалидные credentials
2. Истёк токен OAuth
3. Не настроены env variables

**Проверка:**
```bash
# На сервере
sudo nano /etc/systemd/system/teaching_panel.service
# Проверить Environment переменные:
# ZOOM_ACCOUNT_ID=...
# ZOOM_CLIENT_ID=...
# ZOOM_CLIENT_SECRET=...

sudo systemctl daemon-reload
sudo systemctl restart teaching_panel
```

### Ошибка: Frontend не открывает Zoom

**Причины:**
1. Popup блокировщик браузера
2. Невалидный zoom_start_url

**Решение:**
1. Разрешить popups для домена
2. Проверить консоль браузера (F12)
3. Проверить API ответ: должен содержать `zoom_start_url`

---

## 📊 Мониторинг

### Логи Django

```bash
ssh tp
sudo journalctl -u teaching_panel -f
# Смотреть в реальном времени
```

### Статус сервисов

```bash
sudo systemctl status teaching_panel
sudo systemctl status nginx
sudo systemctl status redis-server  # Для Celery
```

### Проверка API

```bash
# Без авторизации
curl http://72.56.81.163/api/schedule/lessons/

# С авторизацией (нужен токен)
curl http://72.56.81.163/api/me/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## ⚙️ Конфигурация

### Settings.py

```python
# Zoom API (Server-to-Server OAuth)
ZOOM_ACCOUNT_ID = os.environ.get('ZOOM_ACCOUNT_ID', '6w5GrnCgSgaHwMFFbhmlKw')
ZOOM_CLIENT_ID = os.environ.get('ZOOM_CLIENT_ID', 'vNl9EzZTy6h2UifsGVERg')
ZOOM_CLIENT_SECRET = os.environ.get('ZOOM_CLIENT_SECRET', 'jqMJb4R3UgOQ1Q2FEHtkv6Tkz3CxNX87')
ZOOM_WEBHOOK_SECRET_TOKEN = os.environ.get('ZOOM_WEBHOOK_SECRET_TOKEN', '2ocO-3htS8Sl1tVpEtZ2_A')
```

### Токен кэширование

Zoom OAuth токены кэшируются на **50 минут** (Zoom токены живут 60 минут).

**Ключ кэша:** `zoom_oauth_token_{account_id}`

**Очистка кэша:**
```python
from django.core.cache import cache
cache.delete('zoom_oauth_token_6w5GrnCgSgaHwMFFbhmlKw')
```

---

## 📖 Полная документация

- `ZOOM_PROD_TEST_REPORT.md` - подробный отчёт о тестировании
- `ZOOM_POOL_GUIDE.md` - руководство по Zoom Pool системе
- `LESSON_START_AND_RECORDING_TEST_PLAN.md` - тест-план запуска уроков
- `ZOOM_SETUP_COMPLETE.md` - настройка Zoom интеграции
- `ZOOM_WEBHOOK_SETUP.md` - настройка вебхуков

---

**Дата обновления:** 4 декабря 2025  
**Статус:** ✅ Работает на проде  
**URL:** http://72.56.81.163
