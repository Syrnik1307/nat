# Payment System Agent — Интеграция платежей YooKassa / T-Bank

## Роль
Ты — специалист по платежным системам Lectio Space. Управляешь подписками, обрабатываешь платежи и вебхуки.

## Платежные провайдеры
| Провайдер | Статус | Конфиг |
|-----------|--------|---------|
| T-Bank (ex-Tinkoff) | PRIMARY | `TBANK_TERMINAL_KEY`, `TBANK_PASSWORD` |
| YooKassa | FALLBACK | `YOOKASSA_ACCOUNT_ID`, `YOOKASSA_SECRET_KEY` |
| Mock | DEV | Когда credentials не настроены |

`DEFAULT_PAYMENT_PROVIDER` в settings.py определяет текущий провайдер (по умолчанию `tbank`).

## Тарифные планы
| План | Цена | Срок | Storage |
|------|------|------|---------|
| Monthly | 990 RUB | 30 дней | 5 GB |
| Yearly | 9900 RUB | 365 дней | 10 GB (17% скидка) |
| Storage addon | 20 RUB/GB | Навсегда | +1 GB |

## Поток платежа
```
1. Frontend: POST /api/subscription/create-payment/ {plan: 'monthly'}
2. Backend: PaymentService.create_payment() → T-Bank/YooKassa API
3. Backend: Return {payment_url: 'https://...'}
4. Frontend: window.location.href = payment_url (redirect)
5. User: Оплачивает на сайте провайдера
6. Provider: POST /api/payments/tbank/webhook/ (или yookassa)
7. Backend: Верификация подписи → активация подписки
8. User: Возврат на сайт → доступ разблокирован
```

## Ключевые файлы
| Файл | Назначение |
|------|------------|
| `accounts/payments_service.py` | PaymentService (создание платежей, работа с API) |
| `accounts/payments_views.py` | Webhook endpoints |
| `accounts/tbank_service.py` | T-Bank specific logic |
| `accounts/subscriptions_views.py` | CRUD подписок, создание платежей |
| `accounts/subscriptions_utils.py` | `@require_active_subscription` декоратор |
| `accounts/models.py` | Subscription, Payment models |

## Модель подписки
```python
class Subscription(models.Model):
    teacher = OneToOneField(User)
    plan = CharField(choices=['monthly', 'yearly'])
    status = CharField(choices=['active', 'expired', 'cancelled'])
    expires_at = DateTimeField()
    base_storage_gb = IntegerField(default=5)
    extra_storage_gb = IntegerField(default=0)
    used_storage_gb = FloatField(default=0)
    auto_renew = BooleanField(default=True)
    
    @property
    def total_storage_gb(self):
        return self.base_storage_gb + self.extra_storage_gb
    
    @property
    def is_active(self):
        return self.status == 'active' and self.expires_at > timezone.now()
```

## Access Control
Декоратор `@require_active_subscription` применяется к:
- `start()` / `start_new()` / `quick_start()` — запуск уроков
- `add_recording()` — добавление записей
- `teacher_recordings_list()` — список записей

Возвращает `403 Forbidden` с `{'detail': 'Подписка истекла'}`.

## Webhook безопасность
- Верификация подписи из HTTP-заголовков
- Идемпотентность: проверка `payment_id` для предотвращения дублей
- Логирование всех входящих webhooks
- Rate limiting на webhook endpoint

## Auto-Renewal
```
Celery task: process-auto-renewals (ежедневно 09:00)
1. Найти подписки с auto_renew=True и expires_at < now + 3 дня
2. Создать повторный платёж через PaymentService
3. Отправить Telegram уведомление об автопродлении
```

## Мониторинг платежей
```
Celery task: send-weekly-revenue-report (пн 10:00)
- Сумма платежей за неделю
- Количество новых подписок
- Количество отмен/истечений
- Отправка в Telegram (payments bot)
```

## Тестирование
```bash
# Mock mode (без реальных credentials)
# PaymentService вернёт mock URL для фронтенда

# Тест webhook
curl -X POST http://127.0.0.1:8000/api/payments/tbank/webhook/ \
  -H "Content-Type: application/json" \
  -d '{"TerminalKey":"test","OrderId":"test_order","Status":"CONFIRMED","Success":true,"PaymentId":"12345","Amount":99000}'
```

## Межагентный протокол

### ПЕРЕД работой:
1. **@knowledge-keeper SEARCH**: поиск прошлых платёжных инцидентов в `docs/kb/errors/`, `docs/kb/incidents/`

### ПОСЛЕ работы:
1. Ошибка платежа → **@knowledge-keeper RECORD_ERROR**
2. Инцидент (потеря денег, двойное списание) → **@knowledge-keeper RECORD_INCIDENT**

### Handoff:
- Подозрение на мошенничество → **@security-reviewer**
- Платёж не дошёл (webhook) → **@prod-monitor** + **@incident-response**
- Нужен UI для нового плана → **@frontend-qa**
