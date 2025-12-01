# YooKassa - Быстрый старт

## Локальное тестирование (mock-режим)

1. **Запустить Django:**
```powershell
cd teaching_panel
python manage.py runserver
```

2. **Запустить React:**
```powershell
cd frontend
npm start
```

3. **Протестировать:**
- Перейти на http://localhost:3000/auth-new
- Войти как teacher (создать через Django admin если нужно)
- Перейти на http://localhost:3000/teacher/subscription
- Нажать "Оплатить месяц" или "Оплатить год"
- Откроется mock payment URL (localhost:8000/mock-payment-page)

**Mock-режим активен когда:** `YOOKASSA_ACCOUNT_ID` не установлен в environment.

## Production setup (3 шага)

### Шаг 1: Регистрация YooKassa
1. https://yookassa.ru/ → Регистрация
2. Дождаться модерации (1-2 дня)
3. Получить credentials:
   - Account ID (shopId)
   - Secret Key (API ключ)

### Шаг 2: Настроить webhook
В личном кабинете YooKassa:
- URL: `https://yourdomain.com/api/payments/yookassa/webhook/`
- События: `payment.succeeded`, `payment.canceled`
- Сгенерировать webhook secret (32+ символа)

### Шаг 3: Добавить переменные в .env
```bash
YOOKASSA_ACCOUNT_ID=your_account_id
YOOKASSA_SECRET_KEY=your_secret_key
YOOKASSA_WEBHOOK_SECRET=your_webhook_secret
FRONTEND_URL=https://yourdomain.com
```

Перезапустить gunicorn:
```bash
sudo systemctl restart teaching_panel
```

## Тестовые карты YooKassa

- `5555 5555 5555 4444` - успешная оплата
- `5555 5555 5555 5599` - отклонена
- CVV: любой 3-значный код
- Срок: любая будущая дата

## Архитектура платёжного flow

```
1. Пользователь → [Выбор плана на /teacher/subscription]
2. Frontend → POST /api/subscription/create-payment/ {plan: 'monthly'}
3. Backend → PaymentService.create_subscription_payment()
4. Backend → YooKassa API (создание платежа)
5. Backend → Response {payment_url: 'https://yookassa.ru/...'}
6. Frontend → window.location.href = payment_url
7. Пользователь → [Оплата на сайте YooKassa]
8. YooKassa → POST /api/payments/yookassa/webhook/ {type: 'payment.succeeded'}
9. Backend → PaymentService.process_payment_webhook()
10. Backend → Активирует подписку (status=active, expires_at=+30 days)
11. Пользователь → [Возврат на /teacher] → Доступ разблокирован
```

## Цены

- **Месячная подписка:** 990 ₽ (30 дней, 5 GB хранилища)
- **Годовая подписка:** 9900 ₽ (365 дней, 10 GB хранилища, экономия 1980 ₽)
- **Дополнительное хранилище:** 20 ₽/GB (навсегда)

## Что блокируется при неактивной подписке

- ❌ Запуск уроков (`start()`, `start_new()`, `quick_start()`)
- ❌ Загрузка записей уроков (`add_recording()`)
- ❌ Просмотр списка записей (`teacher_recordings_list()`)
- ✅ Доступ к профилю, настройкам, чату (не блокируется)

## Быстрая диагностика

```bash
# Проверить статус подписки
python manage.py shell -c "
from accounts.models import Subscription, User
u = User.objects.get(email='teacher@example.com')
s = Subscription.objects.get(user=u)
print(f'{s.status} | Expires: {s.expires_at} | Storage: {s.total_storage_gb} GB')
"

# Активировать подписку вручную (для тестирования)
python manage.py shell -c "
from accounts.models import Subscription, User
from django.utils import timezone
from datetime import timedelta
u = User.objects.get(email='teacher@example.com')
s = Subscription.objects.get(user=u)
s.status = 'active'
s.expires_at = timezone.now() + timedelta(days=30)
s.save()
print('Activated')
"

# Проверить доступность webhook
curl -X POST https://yourdomain.com/api/payments/yookassa/webhook/ \
  -H "Content-Type: application/json" \
  -d '{"type": "payment.succeeded", "object": {"id": "test"}}'
```

## Troubleshooting

| Проблема | Решение |
|----------|---------|
| Mock URL вместо реального | Проверить переменные `YOOKASSA_*` в `.env`, перезапустить gunicorn |
| Webhook не активирует подписку | Проверить URL webhook в YooKassa, проверить логи `journalctl -u teaching_panel -f` |
| "ModuleNotFoundError: yookassa" | `pip install yookassa>=3.0.0` в venv |
| Доступ блокируется после оплаты | Проверить `expires_at` в БД, убедиться что webhook обработался |

## Полная документация

Подробности в [YOOKASSA_INTEGRATION_GUIDE.md](./YOOKASSA_INTEGRATION_GUIDE.md)
