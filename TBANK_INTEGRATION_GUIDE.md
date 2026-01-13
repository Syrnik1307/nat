# T-Bank (Тинькофф) Integration Guide

Руководство по интеграции платёжной системы T-Bank (бывш. Тинькофф Эквайринг) в Teaching Panel LMS.

## Обзор

T-Bank интеграция работает **параллельно с YooKassa** — можно использовать оба провайдера или переключаться между ними.

**Возможности:**
- ✅ Разовые платежи (подписка monthly/yearly)
- ✅ Покупка дополнительного хранилища
- ✅ Рекуррентные платежи (автопродление через RebillId)
- ✅ Webhook уведомления о статусе платежа
- ✅ Автоматическая активация подписки

## Credentials

### Тестовый терминал (DEMO)
```
TerminalKey: 1768318650428DEMO
Password: AcsPix494kkbJbEI
```

### Production
Получить в личном кабинете: https://business.tbank.ru/oplata/main

## Конфигурация

### Environment Variables

```bash
# T-Bank credentials
TBANK_TERMINAL_KEY=1768318650428DEMO
TBANK_PASSWORD=AcsPix494kkbJbEI

# Какой провайдер использовать по умолчанию
DEFAULT_PAYMENT_PROVIDER=tbank  # или 'yookassa'

# URL для webhook callbacks (должен быть доступен извне)
SITE_URL=https://yourdomain.com

# Frontend URL для редиректа после оплаты
FRONTEND_URL=https://yourdomain.com
```

### settings.py

Настройки уже добавлены:
```python
TBANK_TERMINAL_KEY = os.environ.get('TBANK_TERMINAL_KEY', '')
TBANK_PASSWORD = os.environ.get('TBANK_PASSWORD', '')
DEFAULT_PAYMENT_PROVIDER = os.environ.get('DEFAULT_PAYMENT_PROVIDER', 'yookassa')
SITE_URL = os.environ.get('SITE_URL', 'http://localhost:8000')
```

## API Endpoints

### Создание платежа

```http
POST /api/subscription/create-payment/
Content-Type: application/json
Authorization: Bearer <token>

{
  "plan": "monthly",      // или "yearly"
  "provider": "tbank"     // опционально, по умолчанию из DEFAULT_PAYMENT_PROVIDER
}
```

**Ответ:**
```json
{
  "subscription": {...},
  "payment": {
    "payment_id": "3093639567",
    "status": "pending",
    "amount": "990.00"
  },
  "payment_url": "https://pay.tbank.ru/new/fU1ppgqa",
  "provider": "tbank"
}
```

### Покупка хранилища

```http
POST /api/subscription/add-storage/
Content-Type: application/json
Authorization: Bearer <token>

{
  "gb": 10,
  "provider": "tbank"
}
```

### Webhook (для T-Bank)

```
POST /api/payments/tbank/webhook/
```

T-Bank автоматически отправляет уведомления о статусе платежа.
Ответ: `HTTP 200` с телом `OK` (plain text).

## Настройка в личном кабинете T-Bank

1. Зайти в https://business.tbank.ru/oplata/main
2. Раздел "Магазины" → вкладка "Терминалы"
3. Нажать "Настроить"
4. Указать:
   - **NotificationURL**: `https://yourdomain.com/api/payments/tbank/webhook/`
   - **SuccessURL**: `https://yourdomain.com/teacher/subscription?status=success`
   - **FailURL**: `https://yourdomain.com/teacher/subscription?status=fail`

## Рекуррентные платежи (Автопродление)

### Как это работает

1. При первом платеже передаётся `Recurrent=Y`
2. T-Bank сохраняет карту и возвращает `RebillId` в webhook
3. `RebillId` сохраняется в `Subscription.tbank_rebill_id`
4. Для автопродления вызывается `TBankService.charge_recurring()`

### Реализация автопродления

Добавьте Celery task для автопродления:

```python
# schedule/tasks.py
from celery import shared_task
from accounts.models import Subscription
from accounts.tbank_service import TBankService
from django.utils import timezone
from datetime import timedelta

@shared_task
def process_auto_renewals():
    """Автопродление подписок за 1 день до истечения"""
    tomorrow = timezone.now() + timedelta(days=1)
    
    subscriptions = Subscription.objects.filter(
        status=Subscription.STATUS_ACTIVE,
        auto_renew=True,
        expires_at__lte=tomorrow,
        tbank_rebill_id__isnull=False,
    ).exclude(tbank_rebill_id='')
    
    for sub in subscriptions:
        result = TBankService.charge_recurring(
            subscription=sub,
            plan=sub.plan,
            rebill_id=sub.tbank_rebill_id
        )
        if result and result.get('success'):
            logger.info(f"Auto-renewal initiated for subscription {sub.id}")
        else:
            logger.warning(f"Auto-renewal failed for subscription {sub.id}")
```

Добавьте в `CELERY_BEAT_SCHEDULE`:
```python
'auto-renew-subscriptions': {
    'task': 'schedule.tasks.process_auto_renewals',
    'schedule': crontab(hour=10, minute=0),  # Каждый день в 10:00
},
```

## Статусы платежей T-Bank

| Статус | Описание | Действие |
|--------|----------|----------|
| `NEW` | Платёж создан | Ожидание |
| `AUTHORIZED` | Авторизован (для двухстадийных) | Ожидание |
| `CONFIRMED` | Успешно оплачен | ✅ Активация подписки |
| `REJECTED` | Отклонён | ❌ Пометить как failed |
| `CANCELED` | Отменён | ❌ Пометить как failed |
| `REFUNDED` | Возврат | Пометить как refunded |

## Безопасность

### Проверка Token в webhook

T-Bank подписывает все уведомления токеном. Алгоритм:
1. Собрать все параметры (кроме Token и вложенных объектов)
2. Добавить Password
3. Отсортировать по ключу
4. Конкатенировать значения
5. SHA-256 хэш

Это реализовано в `TBankService._verify_notification_token()`.

### IP Whitelist (опционально)

T-Bank отправляет webhooks с определённых IP. Можно добавить проверку в nginx:
```nginx
location /api/payments/tbank/webhook/ {
    # T-Bank IP ranges
    allow 91.194.226.0/24;
    allow 185.12.112.0/24;
    deny all;
    
    proxy_pass http://backend;
}
```

## Тестирование

### Тестовые карты

| Номер карты | Результат |
|-------------|-----------|
| 4300000000000777 | Успешный платёж |
| 4000000000000002 | Отклонён |
| 4000000000000010 | 3-D Secure |

CVV: любые 3 цифры
Срок: любой будущий

### Проверка интеграции

1. Создать платёж через API
2. Перейти по payment_url
3. Ввести тестовую карту
4. Проверить webhook в логах Django
5. Убедиться что подписка активирована

```bash
# Логи webhook
grep "T-Bank" /var/log/teaching_panel.log
```

## Миграция с YooKassa на T-Bank

1. Добавить env variables `TBANK_*`
2. Установить `DEFAULT_PAYMENT_PROVIDER=tbank`
3. Применить миграцию: `python manage.py migrate`
4. Настроить webhook URL в личном кабинете T-Bank
5. Протестировать на DEMO терминале

## Файлы интеграции

- `accounts/tbank_service.py` — основной сервис
- `accounts/payments_views.py` — webhook endpoint (`tbank_webhook`)
- `accounts/subscriptions_views.py` — модифицированные views с выбором провайдера
- `accounts/models.py` — поле `Subscription.tbank_rebill_id`
- `teaching_panel/settings.py` — конфигурация
- `teaching_panel/urls.py` — URL `/api/payments/tbank/webhook/`

## Документация T-Bank

- [Начало работы](https://developer.tbank.ru/eacq/intro)
- [API Init (создание платежа)](https://developer.tbank.ru/eacq/api/init)
- [Формирование Token](https://developer.tbank.ru/eacq/intro/developer/token)
- [Уведомления (webhooks)](https://developer.tbank.ru/eacq/intro/developer/notification)
- [Рекуррент (Charge)](https://developer.tbank.ru/eacq/api/charge)

---

**Дата обновления:** 13 января 2026
