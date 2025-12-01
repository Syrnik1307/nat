# Интеграция YooKassa - Руководство по внедрению

## Обзор

Система оплаты подписок Teaching Panel интегрирована с YooKassa (российский платёжный шлюз). Реализованы:
- Оплата месячной подписки (990 ₽)
- Оплата годовой подписки (9900 ₽)
- Покупка дополнительного хранилища (20 ₽/GB)
- Webhook для автоматической активации подписок после оплаты
- Mock-режим для разработки без реальных учётных данных

## Архитектура

### Backend (Django)

**Основные компоненты:**
1. `accounts/payments_service.py` - Сервисный слой для работы с YooKassa
2. `accounts/payments_views.py` - Webhook endpoint для обработки callback'ов от YooKassa
3. `accounts/subscriptions_views.py` - API endpoints для создания платежей
4. `accounts/models.py` - Модели `Subscription` и `Payment`

**Цены (PLAN_PRICES в payments_service.py):**
- Месячная подписка: 990.00 RUB (30 дней, 5 GB хранилища)
- Годовая подписка: 9900.00 RUB (365 дней, 10 GB хранилища)
- Дополнительное хранилище: 20.00 RUB за 1 GB (навсегда)

### Frontend (React)

**Основные компоненты:**
1. `frontend/src/components/SubscriptionPage.js` - Страница управления подпиской
2. `frontend/src/components/SubscriptionPage.css` - Стили страницы
3. `frontend/src/components/SubscriptionBanner.js` - Баннер предупреждений
4. `frontend/src/auth.js` - AuthContext загружает подписку

**Маршруты:**
- `/teacher/subscription` - Страница управления подпиской (Protected, teacher/admin)
- `/billing` - Альтернативный маршрут (legacy)

## Настройка на сервере

### 1. Регистрация в YooKassa

1. Перейти на https://yookassa.ru/
2. Зарегистрировать аккаунт и дождаться модерации (1-2 дня)
3. Получить учётные данные из личного кабинета:
   - **Account ID** (shopId)
   - **Secret Key** (API ключ)

### 2. Конфигурация webhook

В личном кабинете YooKassa настроить webhook:

**URL:** `https://yourdomain.com/api/payments/yookassa/webhook/`

**События:**
- `payment.succeeded` - успешная оплата
- `payment.canceled` - отмена платежа

**Секретный ключ:**
Сгенерировать случайную строку (32+ символа) для HMAC-подписи:
```powershell
# PowerShell
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_})
```

### 3. Настройка переменных окружения

Добавить в `.env` на сервере:

```bash
# YooKassa credentials
YOOKASSA_ACCOUNT_ID=your_account_id_here
YOOKASSA_SECRET_KEY=your_secret_key_here
YOOKASSA_WEBHOOK_SECRET=your_generated_webhook_secret_here

# Frontend URL для return_url в платежах
FRONTEND_URL=https://yourdomain.com
```

**Важно:** Без этих переменных система работает в **mock-режиме** (возвращает тестовые payment_url).

### 4. Установка зависимостей

```bash
cd teaching_panel
source ../venv/bin/activate  # или venv\Scripts\activate на Windows
pip install yookassa>=3.0.0
```

Проверить установку:
```python
python -c "from yookassa import Configuration; print('YooKassa SDK installed')"
```

### 5. Миграции БД

```bash
python manage.py migrate
```

Проверить, что таблицы `accounts_subscription` и `accounts_payment` содержат новые поля:
- `base_storage_gb`
- `extra_storage_gb`
- `used_storage_gb`

### 6. Проверка webhook доступности

Webhook должен быть публично доступен по HTTPS:

```bash
curl -X POST https://yourdomain.com/api/payments/yookassa/webhook/ \
  -H "Content-Type: application/json" \
  -d '{"type": "payment.succeeded", "object": {"id": "test"}}'
```

Ожидаемый ответ: `200 OK` (если signature не передана, backend пропустит проверку в dev-режиме).

## Тестирование

### Локальное тестирование (mock-режим)

1. Запустить Django без YOOKASSA_ACCOUNT_ID:
```powershell
cd teaching_panel
python manage.py runserver
```

2. Запустить React:
```powershell
cd frontend
npm start
```

3. Перейти на http://localhost:3000/auth-new, залогиниться как teacher
4. Перейти на http://localhost:3000/teacher/subscription
5. Нажать "Оплатить" - откроется mock URL (localhost:8000/mock-payment-page)

### Тестирование с реальными credentials (dev)

1. Установить переменные окружения:
```powershell
$env:YOOKASSA_ACCOUNT_ID = "your_account_id"
$env:YOOKASSA_SECRET_KEY = "your_secret_key"
$env:YOOKASSA_WEBHOOK_SECRET = "your_webhook_secret"
$env:FRONTEND_URL = "http://localhost:3000"
```

2. Запустить Django:
```powershell
python manage.py runserver
```

3. Использовать ngrok для публичного webhook:
```bash
ngrok http 8000
```

4. В YooKassa webhook URL указать: `https://your-ngrok-url.ngrok.io/api/payments/yookassa/webhook/`

5. Создать платёж через фронтенд - будет редирект на настоящую страницу YooKassa

**Тестовые карты YooKassa:**
- `5555 5555 5555 4444` - успешная оплата
- `5555 5555 5555 5599` - отклонена

### Production тестирование

1. Убедиться, что все переменные окружения установлены в `.env` на сервере
2. Перезапустить gunicorn:
```bash
sudo systemctl restart teaching_panel
```

3. Проверить логи:
```bash
sudo journalctl -u teaching_panel -f
```

4. Создать тестовый платёж и отследить webhook:
   - Фронтенд: Создаётся платёж → редирект на YooKassa
   - Оплата тестовой картой
   - YooKassa отправляет webhook → Django обрабатывает → подписка активируется
   - Проверить в админке: статус подписки должен быть `active`, `expires_at` установлен

## API Endpoints

### GET /api/subscription/
Получить текущую подписку пользователя.

**Response:**
```json
{
  "id": 1,
  "plan": "monthly",
  "status": "active",
  "started_at": "2025-01-15T10:00:00Z",
  "expires_at": "2025-02-14T10:00:00Z",
  "auto_renew": true,
  "total_paid": "990.00",
  "base_storage_gb": 5,
  "extra_storage_gb": 0,
  "used_storage_gb": 0.45,
  "total_storage_gb": 5,
  "payments": [
    {
      "id": 1,
      "amount": "990.00",
      "currency": "RUB",
      "status": "succeeded",
      "payment_system": "yookassa",
      "created_at": "2025-01-15T10:00:00Z",
      "paid_at": "2025-01-15T10:05:00Z"
    }
  ]
}
```

### POST /api/subscription/create-payment/
Создать платёж для покупки подписки.

**Request:**
```json
{
  "plan": "monthly"  // или "yearly"
}
```

**Response:**
```json
{
  "payment_url": "https://yookassa.ru/payments/123456/confirmation",
  "payment_id": "123456",
  "subscription": { ... }
}
```

**Логика:**
- Переводит подписку в статус `pending`
- Создаёт Payment запись
- Возвращает payment_url для редиректа
- После оплаты webhook активирует подписку

### POST /api/subscription/add-storage/
Купить дополнительное хранилище.

**Request:**
```json
{
  "gb": 50
}
```

**Response:**
```json
{
  "payment_url": "https://yookassa.ru/payments/789012/confirmation",
  "payment_id": "789012",
  "subscription": { ... }
}
```

**Логика:**
- Создаёт платёж на сумму `gb * 20 RUB`
- После оплаты webhook добавляет GB к `extra_storage_gb`

### POST /api/subscription/cancel/
Отменить автопродление подписки.

**Response:**
```json
{
  "status": "cancelled",
  "auto_renew": false,
  "cancelled_at": "2025-01-20T12:00:00Z"
}
```

**Логика:**
- Устанавливает `status=cancelled`, `auto_renew=false`
- Доступ сохраняется до `expires_at`

### POST /api/payments/yookassa/webhook/
Webhook для обработки событий от YooKassa (не вызывается вручную).

**Обрабатываемые события:**
- `payment.succeeded` - активирует подписку или добавляет storage
- `payment.canceled` - помечает Payment как failed

## Логика активации подписки

**PaymentService.process_payment_webhook():**

1. Проверяет статус платежа: `succeeded`
2. Находит Payment по `payment_id`
3. Если `metadata['type'] == 'subscription'`:
   - Обновляет `Subscription.status = 'active'`
   - Устанавливает `expires_at = now() + 30/365 days` (в зависимости от плана)
   - Обновляет `base_storage_gb` (5 GB monthly, 10 GB yearly)
   - Увеличивает `total_paid`
4. Если `metadata['type'] == 'storage'`:
   - Добавляет GB к `extra_storage_gb`
   - Увеличивает `total_paid`
5. Обновляет `Payment.status = 'succeeded'`, `paid_at = now()`

## Блокировка доступа при истечении подписки

**Decorator:** `@require_active_subscription` в `accounts/subscriptions_utils.py`

**Применяется к:**
- `POST /api/schedule/lessons/{id}/start/` - запуск урока
- `POST /api/schedule/lessons/{id}/start-new/` - создание Zoom-урока
- `POST /api/schedule/lessons/{id}/quick-start/` - быстрый запуск
- `POST /api/schedule/lessons/{id}/recordings/` - загрузка записей
- `GET /api/schedule/lessons/{id}/recordings/` - просмотр записей

**Логика:**
```python
if subscription.status != 'active' or timezone.now() >= subscription.expires_at:
    return Response({'detail': 'Подписка истекла'}, status=403)
```

## UI Components

### SubscriptionPage.js

**Секции:**
1. **Current Subscription** - текущий план, статус, дата истечения, использование хранилища
2. **Plans** - карточки месячного и годового плана с кнопками оплаты
3. **Storage** - форма покупки дополнительного хранилища
4. **Payment History** - список всех платежей

**Состояния подписки:**
- `active` + days left > 0 → ✅ Активна
- `active` + days left ≤ 0 → ⏱️ Истекла
- `pending` → ⏳ Ожидает оплаты
- `cancelled` → ❌ Отменена
- `expired` → ⏱️ Истекла

**Кнопки:**
- "Оплатить" (план) → `POST /api/subscription/create-payment/` → `window.location.href = payment_url`
- "Купить X GB" → `POST /api/subscription/add-storage/` → редирект
- "Отменить автопродление" → `POST /api/subscription/cancel/`

### SubscriptionBanner.js

Отображается на `TeacherHomePage` при:
- Подписка истекла (`status='expired'` или `days_left ≤ 0`)
- Осталось < 7 дней (`warning`)
- Ожидание оплаты (`status='pending'`)
- Подписка отменена (`status='cancelled'`)

**Клик на "Оплатить"** → `navigate('/teacher/subscription')`

## Troubleshooting

### Проблема: Mock payment_url возвращается в production

**Причина:** Переменные YOOKASSA_* не установлены или неправильны.

**Решение:**
1. Проверить `.env`: `cat /path/to/teaching_panel/.env | grep YOOKASSA`
2. Перезапустить gunicorn: `sudo systemctl restart teaching_panel`
3. Проверить logs: `sudo journalctl -u teaching_panel -n 50`

### Проблема: Webhook не активирует подписку

**Причина:** Webhook не доходит до сервера или signature неверная.

**Решение:**
1. Проверить в YooKassa личном кабинете: раздел "Уведомления" → проверить статус webhook
2. Проверить nginx логи: `sudo tail -f /var/log/nginx/error.log`
3. Проверить Django logs: `sudo journalctl -u teaching_panel -f`
4. Проверить `YOOKASSA_WEBHOOK_SECRET` совпадает с секретом в YooKassa
5. Временно отключить проверку signature (dev only):
   ```python
   # payments_views.py, закомментировать проверку signature
   # if not verify_signature(...):
   #     return JsonResponse({'error': 'Invalid signature'}, status=403)
   ```

### Проблема: Подписка активировалась, но доступ блокируется

**Причина:** `expires_at` не установлен или в прошлом.

**Решение:**
1. Проверить в Django shell:
   ```python
   from accounts.models import Subscription
   sub = Subscription.objects.get(user__email='teacher@example.com')
   print(sub.status, sub.expires_at)
   ```
2. Если `expires_at` пустой или прошёл:
   ```python
   from django.utils import timezone
   from datetime import timedelta
   sub.expires_at = timezone.now() + timedelta(days=30)
   sub.status = 'active'
   sub.save()
   ```

### Проблема: Ошибка "ModuleNotFoundError: No module named 'yookassa'"

**Причина:** Пакет не установлен в venv.

**Решение:**
```bash
cd teaching_panel
source ../venv/bin/activate
pip install yookassa>=3.0.0
sudo systemctl restart teaching_panel
```

### Проблема: CORS errors при редиректе с YooKassa

**Причина:** `return_url` указывает на неправильный домен.

**Решение:**
1. Проверить `FRONTEND_URL` в `.env`: `https://yourdomain.com` (без trailing slash)
2. Убедиться, что `CORS_ALLOWED_ORIGINS` в settings.py содержит frontend URL
3. Проверить nginx конфигурацию: CORS headers должны передаваться

## Roadmap

### Ближайшие улучшения:
- [ ] Email уведомления о приближении окончания подписки
- [ ] Автопродление подписки через сохранённые платёжные методы
- [ ] Промокоды и скидки
- [ ] Расширенная аналитика платежей для админов
- [ ] Интеграция с телеграм-ботом для уведомлений об оплате

### Долгосрочные:
- [ ] Интеграция альтернативных платёжных систем (Stripe для международных клиентов)
- [ ] Тарификация по количеству студентов
- [ ] Реферальная программа с бонусным хранилищем

## Полезные команды

```bash
# Проверить статус подписки пользователя
python manage.py shell -c "
from accounts.models import Subscription, User
u = User.objects.get(email='teacher@example.com')
s = Subscription.objects.get(user=u)
print(f'Status: {s.status}, Expires: {s.expires_at}, Storage: {s.total_storage_gb} GB')
"

# Активировать подписку вручную (тестирование)
python manage.py shell -c "
from accounts.models import Subscription, User
from django.utils import timezone
from datetime import timedelta
u = User.objects.get(email='teacher@example.com')
s = Subscription.objects.get(user=u)
s.plan = 'monthly'
s.status = 'active'
s.expires_at = timezone.now() + timedelta(days=30)
s.base_storage_gb = 5
s.save()
print('Subscription activated')
"

# Проверить webhook connectivity
curl -X POST https://yourdomain.com/api/payments/yookassa/webhook/ \
  -H "Content-Type: application/json" \
  -H "X-Yookassa-Signature: test" \
  -d '{"type": "payment.succeeded", "object": {"id": "test123"}}'
```

---

**Последнее обновление:** 29 ноября 2025
