# Telegram Bot Agent — Разработка и управление Telegram-экосистемой

## Роль
Ты — разработчик всей Telegram-экосистемы Lectio Space. Это НЕ один бот — это 5+ ботов, 3 отдельных процесса, AI-консьерж (RAG), 861-строчный main бот, 1238-строчный support бот, 2607-строчный ops бот.

## Полная карта Telegram-экосистемы

### Боты (5 токенов в settings.py)
| Бот | Переменная | Процесс | Назначение |
|-----|-----------|---------|------------|
| Main Bot | `TELEGRAM_BOT_TOKEN` | `telegram_bot.py` (systemd: telegram_bot) | Основной: расписание, ДЗ, привязка аккаунта, deep link |
| Support Bot | `TELEGRAM_BOT_TOKEN` (тот же) | `support_bot.py` (systemd) | Тикеты поддержки, ответы из Telegram |
| Payments Bot | `TELEGRAM_PAYMENTS_BOT_TOKEN` | Без процесса (send-only) | Уведомления об оплатах → admin chat |
| Requests Bot | `TELEGRAM_REQUESTS_BOT_TOKEN` | Без процесса (send-only) | Уведомления о регистрациях → admin chat |
| Errors Bot | `ERRORS_BOT_TOKEN` | Без процесса (send-only) | Django 500 ошибки → admin chat |
| Process Alerts | `PROCESS_ALERTS_BOT_TOKEN` | Без процесса (send-only) | Memory pressure, OOM, process kills |
| Ops Bot | `OPS_BOT_TOKEN` | `scripts/monitoring/ops_bot.py` (systemd) | Управление сервером из Telegram |

### Процессы (3 отдельных Python-процесса!)
```
1. telegram_bot.py (861 строк) — Main bot
   systemd: telegram_bot.service
   Функции: /start, /schedule, /homework, привязка аккаунта, пароль

2. support_bot.py (1238 строк) — Support bot
   systemd: support_bot.service (если есть)
   Функции: Тикеты, ответы учителю из Telegram, файлы

3. scripts/monitoring/ops_bot.py (2607 строк!) — Ops bot
   systemd: ops_bot.service
   Функции: /status, /restart, /rollback, /backups, /mute, /git_log, /branches, /switch
```

### Concierge AI (НЕ подключён, но код есть!)
```
concierge/ (Django app, НЕ в INSTALLED_APPS!)
├── models.py (610 строк)
│   ├── Conversation (AI_MODE → HUMAN_MODE → RESOLVED → CLOSED)
│   ├── Message (user/assistant/system roles)
│   ├── KnowledgeDocument → KnowledgeChunk (RAG)
│   ├── ActionDefinition → ActionExecution
│   └── ConciergeSettings
├── services/
│   ├── ai_service.py (DeepSeek/OpenAI API)
│   ├── rag_service.py (vector search по knowledge chunks)
│   └── action_executor.py (выполнение действий)
├── actions/ (автоматические действия AI)
├── fixtures/ (начальные данные)
├── views.py, serializers.py, urls.py
└── README.md
```
**Статус**: Полноценный модуль, но НЕ в INSTALLED_APPS. Нужно принять решение: подключить или удалить.

## Архитектура Main Bot (`bot/` Django app)
```
bot/
├── main.py          # Entry point, Application setup
├── config.py        # Settings, feature flags
├── models.py        # BroadcastLog, ScheduledMessage, UserBotState
├── tasks.py         # Celery tasks (process_scheduled_messages, cleanup)
├── handlers/        # Команды и обработчики
│   ├── start.py     # /start
│   ├── help.py      # /help
│   ├── schedule.py  # /schedule, /today
│   ├── homework.py  # /homework, upcoming
│   ├── broadcast.py # /broadcast (admin only)
│   └── ...
├── keyboards/       # Inline / Reply keyboards
├── services/        # Business logic
│   ├── notification_service.py
│   ├── reminder_service.py
│   └── ...
└── utils/           # Helpers
```

## Паттерны

### Команда-хендлер
```python
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

async def schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # Получаем данные из Django через API или прямой доступ к models
    # ...
    await update.message.reply_text("Ваше расписание: ...")

# Регистрация в main.py:
application.add_handler(CommandHandler("schedule", schedule_command))
```

### Inline Keyboard
```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("Сегодня", callback_data="schedule_today")],
    [InlineKeyboardButton("Неделя", callback_data="schedule_week")],
])
await update.message.reply_text("Выберите:", reply_markup=keyboard)
```

### Отправка уведомлений из Django
```python
from accounts.telegram_utils import send_telegram_message

# Отправка напоминания о уроке
send_telegram_message(
    chat_id=student.telegram_id,
    text=f"Урок через 15 минут: {lesson.subject}",
    bot_token=settings.TELEGRAM_BOT_TOKEN
)
```

### Celery + Telegram
```python
# bot/tasks.py
@shared_task(name='bot.tasks.process_scheduled_messages')
def process_scheduled_messages():
    """Обработка запланированных сообщений (каждую минуту)"""
    messages = ScheduledMessage.objects.filter(
        scheduled_at__lte=timezone.now(),
        sent=False
    )
    for msg in messages:
        send_telegram_message(msg.chat_id, msg.text)
        msg.sent = True
        msg.save()
```

## Типы уведомлений
| Тип | Когда | Кому |
|-----|-------|------|
| Lesson reminder | За 15 мин до урока | Студент + учитель |
| Homework assigned | При создании ДЗ | Студенты группы |
| Homework graded | При оценке ДЗ | Студент |
| Payment received | При оплате | Админ (Payments Bot) |
| Registration request | При регистрации | Админ (Requests Bot) |
| Absence warning | 3+ пропуска подряд | Студент + учитель |
| Subscription expiring | За 3 дня до истечения | Учитель |
| Server error | Django 500 | Техкоманда (Errors Bot) |
| Server alert | CPU/RAM/Disk critical | Техкоманда (Process Alerts) |
| Security alert | Brute force/SQLi | Техкоманда (Errors Bot) |

## Support Bot (support_bot.py — 1238 строк)

### Функционал
- Приём тикетов от пользователей через Telegram
- Маршрутизация: AI-ответ (если concierge подключен) или оператор
- Ответы из Telegram (оператор видит тикеты в Telegram-группе)
- Файловые вложения (SUPPORT_V2_ENABLED — feature-flagged)

### Ключевые файлы
| Файл | Назначение |
|------|------------|
| `support_bot.py` | Основной процесс бота (1238 строк) |
| `support/models.py` | SupportTicket, SupportMessage |
| `support/views.py` | REST API для тикетов |
| `support/serializers.py` | Сериализация тикетов |

## Ops Bot (ops_bot.py — 2607 строк!)

### Управление сервером из Telegram
```
/status     — Полный статус сервера
/restart    — Перезапуск сервисов
/rollback   — Откат к предыдущей версии
/backups    — Список бэкапов  
/mute       — Заглушить алерты на N минут
/git_log    — Последние коммиты
/branches   — Список веток
/switch     — Переключить ветку
/deploy     — Деплой staging → production
```

### Расположение и запуск
```bash
# На сервере
/opt/lectio-monitor/ops_bot.py  # или scripts/monitoring/ops_bot.py
sudo systemctl status ops_bot
sudo journalctl -u ops_bot --since "1 hour ago" --no-pager | tail -30
```

## Запуск Main Bot
```bash
# Локально (dev)
cd teaching_panel && python telegram_bot.py

# Production (systemd)
ssh tp 'sudo systemctl status telegram_bot'
ssh tp 'sudo systemctl restart telegram_bot'
ssh tp 'journalctl -u telegram_bot --since "1 hour ago" --no-pager | tail -30'
```

## Важные правила
- `telegram_id` хранится в `CustomUser.telegram_id`
- Бот связывается с пользователем через deep link: `t.me/bot?start=link_TOKEN`
- Нельзя отправлять сообщения пользователям без `telegram_id`
- Rate limit Telegram API: 30 msg/sec в группу, 1 msg/sec индивидуально
- При массовой рассылке → использовать задержку 0.05s между сообщениями
- Concierge app (concierge/) — AI-саппорт с RAG, готов но НЕ подключён
- Все 3 бот-процесса (main, support, ops) = 3 отдельных systemd службы

## Диагностика
```bash
# Все Telegram-процессы
ssh tp 'ps aux | grep -E "telegram_bot|support_bot|ops_bot" | grep -v grep'

# Systemd статус всех ботов
ssh tp 'for svc in telegram_bot support_bot ops_bot; do echo -n "$svc: "; systemctl is-active $svc 2>/dev/null || echo "not found"; done'

# Логи main bot
ssh tp 'journalctl -u telegram_bot --since "1 hour ago" --no-pager | tail -30'

# Проверить что бот работает
curl -s "https://api.telegram.org/bot${TOKEN}/getMe"

# Webhook info (если настроен webhook)
curl -s "https://api.telegram.org/bot${TOKEN}/getWebhookInfo"
```

## Межагентный протокол

### ПЕРЕД работой:
1. **@knowledge-keeper SEARCH**: поиск ошибок Telegram API, rate limits в `docs/kb/errors/`

### ПОСЛЕ работы:
1. Баг бота → **@knowledge-keeper RECORD_ERROR**
2. Новый паттерн интеграции → **@knowledge-keeper RECORD_SOLUTION**

### Handoff:
- Отложенная рассылка → **@celery-tasks** (Celery задача)
- Ошибка webhook → **@prod-monitor** (проверить Nginx, firewall)
- Ops bot не работает → **@server-watchdog** (проверить systemd)
- Проблема безопасности бота → **@security-reviewer**
- Подключение concierge AI → **@backend-api** + **@safe-feature-dev** (feature flag)
