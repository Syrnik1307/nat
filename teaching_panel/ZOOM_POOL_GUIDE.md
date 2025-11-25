# Инструкция по запуску Zoom Pool системы

## Архитектура системы

Система управления пулом Zoom-аккаунтов состоит из 5 компонентов (5 промптов):

### ✅ Промпт 1: Модели данных
- **ZoomAccount** - пул Zoom лицензий с флагом `is_busy` и связью `current_lesson`
- **RecurringLesson** - регулярные занятия (день недели, верхняя/нижняя неделя)
- **Lesson** - добавлены поля `zoom_start_url`, `zoom_account_used`, `zoom_meeting_id`

### ✅ Промпт 2: Атомарный захват аккаунтов
- **start_lesson_view()** - использует `select_for_update()` для блокировки строк БД
- Предотвращает race condition при одновременном старте уроков
- API call к Zoom вне транзакции для производительности

### ✅ Промпт 3: Генерация событий календаря
- **get_lessons_for_calendar()** - объединяет разовые и регулярные уроки
- Генерирует виртуальные события из RecurringLesson по дням недели
- Поддерживает верхнюю/нижнюю/все недели

### ✅ Промпт 4: Celery задача автоочистки
- **release_stuck_zoom_accounts()** - каждые 10 минут освобождает зависшие аккаунты
- Проверяет уроки, которые закончились >15 минут назад
- Очищает "осиротевших" аккаунтов (is_busy=True без урока)

### ✅ Промпт 5: Zoom Webhook
- **zoom_webhook_receiver()** - принимает события meeting.ended от Zoom
- Освобождает аккаунт сразу после завершения встречи
- Поддерживает Zoom verification token

---

## 🚀 Запуск системы

### 1. Запуск Redis (для Celery)

**Windows:**
```powershell
# Скачать Redis для Windows:
# https://github.com/microsoftarchive/redis/releases

# Или использовать Docker:
docker run -d -p 6379:6379 redis:alpine
```

**Linux/Mac:**
```bash
redis-server
```

### 2. Запуск Django сервера

```powershell
# Терминал 1
cd "c:\Users\User\Desktop\WEB panel\teaching_panel"
python manage.py runserver
```

### 3. Запуск Celery Worker

```powershell
# Терминал 2
cd "c:\Users\User\Desktop\WEB panel\teaching_panel"
celery -A teaching_panel worker --loglevel=info --pool=solo
```

**Примечание:** На Windows используем `--pool=solo` вместо дефолтного prefork.

### 4. Запуск Celery Beat (планировщик)

```powershell
# Терминал 3
cd "c:\Users\User\Desktop\WEB panel\teaching_panel"
celery -A teaching_panel beat --loglevel=info
```

Beat будет запускать `release_stuck_zoom_accounts` каждые 10 минут.

---

## 🧪 Тестирование системы

### Шаг 1: Создать Zoom аккаунты в админке

```
URL: http://127.0.0.1:8000/admin/schedule/zoomaccount/
Login: admin@example.com / admin123

Создать 2-3 аккаунта:
- Name: "Zoom Account 1"
- API Key: "fake_api_key_1"
- API Secret: "fake_secret_1"
- Zoom User ID: "user_zoom_id_1"
- Is Busy: False (не отмечено)
```

### Шаг 2: Создать урок

```python
# В Django shell (python manage.py shell)
from schedule.models import Lesson, Group
from accounts.models import CustomUser
from django.utils import timezone
from datetime import timedelta

teacher = CustomUser.objects.get(email='teacher1@example.com')
group = Group.objects.first()

lesson = Lesson.objects.create(
    title='Тестовый урок',
    teacher=teacher,
    group=group,
    start_time=timezone.now(),
    end_time=timezone.now() + timedelta(hours=1),
    topics='Тестирование Zoom Pool'
)
print(f"Урок создан: ID={lesson.id}")
```

### Шаг 3: Запустить урок (атомарный захват)

**Через API:**
```powershell
# PowerShell
$body = @{
    lesson_id = 1  # Замените на ваш ID
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/schedule/lesson/1/start/" `
    -Method POST `
    -Body $body `
    -ContentType "application/json"
```

**Ожидаемый результат:**
```json
{
  "status": "success",
  "meeting_data": {
    "id": "12345678901",
    "start_url": "https://zoom.us/s/12345678901?zak=mock_host_key",
    "join_url": "https://zoom.us/j/12345678901?pwd=mockpassword",
    "password": "Ab12Cd"
  },
  "zoom_account": "Zoom Account 1"
}
```

### Шаг 4: Проверить, что аккаунт занят

```
Админка: http://127.0.0.1:8000/admin/schedule/zoomaccount/
Поле "Is Busy" должно быть True
Поле "Current Lesson" = ваш урок
```

### Шаг 5: Тест Race Condition (одновременный старт)

```powershell
# Запустить 3 параллельных запроса
1..3 | ForEach-Object -Parallel {
    $body = @{ lesson_id = 1 } | ConvertTo-Json
    Invoke-RestMethod -Uri "http://127.0.0.1:8000/schedule/lesson/1/start/" `
        -Method POST -Body $body -ContentType "application/json"
}
```

**Ожидаемый результат:**
- Первый запрос: 200 OK (захватил аккаунт)
- Остальные: 429 Too Many Requests (все аккаунты заняты)

### Шаг 6: Тест Webhook (освобождение аккаунта)

```powershell
# Симуляция Zoom webhook события meeting.ended
$webhook_payload = @{
    event = "meeting.ended"
    payload = @{
        object = @{
            id = "12345678901"  # Meeting ID из урока
        }
    }
} | ConvertTo-Json -Depth 3

Invoke-RestMethod -Uri "http://127.0.0.1:8000/schedule/webhook/zoom/" `
    -Method POST `
    -Body $webhook_payload `
    -ContentType "application/json"
```

**Ожидаемый результат:**
```json
{
  "status": "success",
  "message": "Account Zoom Account 1 released",
  "lesson_id": 1,
  "meeting_id": "12345678901"
}
```

Проверить: `is_busy` должно стать False в админке.

### Шаг 7: Тест Celery автоочистки

```python
# 1. Создать "зависший" урок (закончился 20 минут назад)
from django.utils import timezone
from datetime import timedelta

lesson.end_time = timezone.now() - timedelta(minutes=20)
lesson.save()

# 2. Вручную запустить задачу (без ожидания 10 минут)
from schedule.tasks import release_stuck_zoom_accounts
result = release_stuck_zoom_accounts.delay()
print(result.get())
```

**Ожидаемый результат в Celery логе:**
```
[Celery] Освобожден зависший аккаунт Zoom Account 1 (урок #1 закончился в ...)
[Celery] Итого освобождено аккаунтов: 1
```

---

## 🔧 Настройка реального Zoom Webhook

### Использование ngrok (для локальной разработки)

1. Скачать ngrok: https://ngrok.com/download
2. Запустить туннель:
```bash
ngrok http 8000
```

3. Скопировать HTTPS URL (например: `https://abc123.ngrok.io`)

4. В Zoom App настройках:
   - Перейти: https://marketplace.zoom.us/develop/create
   - Создать "Webhook Only" приложение
   - В разделе "Event Subscriptions":
     - Event notification endpoint URL: `https://abc123.ngrok.io/schedule/webhook/zoom/`
     - Subscribe to events: "End Meeting" (`meeting.ended`)
   - Сохранить

5. Zoom отправит verification request - ваш webhook автоматически ответит.

---

## 📊 Мониторинг системы

### Проверка занятости аккаунтов (API)
```
GET /api/schedule/zoom-accounts/
```

### Логи Celery
Celery Worker выводит логи в консоль:
```
[Celery] Освобожден зависший аккаунт...
[Celery] Итого освобождено аккаунтов: X
```

### Django логи
```python
# settings.py
LOGGING = {
    'version': 1,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'loggers': {
        'schedule': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

---

## 🐛 Troubleshooting

### Celery не подключается к Redis
**Ошибка:** `Error 61 connecting to localhost:6379. Connection refused.`
**Решение:** Запустите Redis сервер (см. раздел "Запуск Redis")

### Webhook не работает
**Проблема:** Zoom не может достучаться до локального сервера
**Решение:** Используйте ngrok для создания публичного URL

### Аккаунты не освобождаются
**Проверка:**
```python
# Django shell
from schedule.models import ZoomAccount
print(ZoomAccount.objects.filter(is_busy=True))
```

**Решение:** Вручную запустите задачу:
```python
from schedule.tasks import release_stuck_zoom_accounts
release_stuck_zoom_accounts.delay()
```

### select_for_update() deadlock
**Ошибка:** TransactionManagementError
**Причина:** Вызов вне транзакции
**Решение:** Убедитесь, что используете `@transaction.atomic()` или `with transaction.atomic():`

---

## 🎯 Итоговая архитектура

```
┌─────────────────┐
│  Django Server  │
│   port 8000     │
└────────┬────────┘
         │
    ┌────┴────┐
    │  Redis  │  (порт 6379)
    └────┬────┘
         │
    ┌────┴──────────────────┐
    │                       │
┌───▼──────┐      ┌─────────▼─────┐
│  Celery  │      │  Celery Beat  │
│  Worker  │      │  (планировщик)│
└──────────┘      └───────────────┘
    │
    │ Каждые 10 минут:
    │ release_stuck_zoom_accounts()
    │
    ▼
┌─────────────────────────┐
│  ZoomAccount Pool       │
│  ┌─────────────────┐   │
│  │ Account 1       │   │
│  │ is_busy: False  │   │
│  └─────────────────┘   │
│  ┌─────────────────┐   │
│  │ Account 2       │   │
│  │ is_busy: True   │◄──┼─── select_for_update()
│  │ current_lesson:1│   │     (атомарный захват)
│  └─────────────────┘   │
└─────────────────────────┘
         ▲
         │ meeting.ended
         │
    ┌────┴─────────┐
    │ Zoom Webhook │
    └──────────────┘
```

## ✅ Чеклист готовности системы

- [x] ZoomAccount и RecurringLesson модели созданы
- [x] Миграция применена
- [x] start_lesson_view с select_for_update() реализован
- [x] Mock Zoom API клиент готов
- [x] Celery настроен (worker + beat)
- [x] release_stuck_zoom_accounts задача создана
- [x] zoom_webhook_receiver реализован
- [x] URL routes добавлены
- [x] get_lessons_for_calendar() helper готов
- [ ] Redis запущен
- [ ] Celery worker запущен
- [ ] Celery beat запущен
- [ ] Zoom аккаунты созданы в админке
- [ ] ngrok настроен (для webhook)

**Система полностью реализована и готова к запуску!** 🎉
