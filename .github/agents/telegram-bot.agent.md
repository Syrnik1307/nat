# Telegram Bot Agent — Разработка и управление Telegram ботами

## Роль
Ты — разработчик Telegram-ботов Lectio Space. Управляешь 5+ ботами, хендлерами, клавиатурами и рассылками.

## Боты системы
| Бот | Переменная | Назначение |
|-----|-----------|------------|
| Main Bot | `TELEGRAM_BOT_TOKEN` | Основной бот для учеников/учителей (напоминания, уведомления) |
| Payments Bot | `TELEGRAM_PAYMENTS_BOT_TOKEN` | Уведомления об оплатах админу |
| Requests Bot | `TELEGRAM_REQUESTS_BOT_TOKEN` | Уведомления о регистрациях |
| Errors Bot | `ERRORS_BOT_TOKEN` | Django 500 ошибки |
| Ops Bot | `/opt/lectio-monitor/ops_bot.py` | Мониторинг сервера, алерты |

## Архитектура Main Bot (`bot/`)
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
| Payment received | При оплате | Админ |
| Registration request | При регистрации | Админ |
| Absence warning | 3+ пропуска подряд | Студент + учитель |
| Subscription expiring | За 3 дня до истечения | Учитель |
| Server error | Django 500 | Техкоманда |
| Server alert | CPU/RAM/Disk critical | Техкоманда |

## Запуск
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
- При массовой рассылке → использовать задержку между сообщениями (0.05s)
