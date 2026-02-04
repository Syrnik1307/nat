# Отчёт об исправлении: Telegram Support Bot

## Дата: 4 февраля 2026

## Проблема

**Communication Breakdown**: Входящие сообщения от пользователей в Telegram боте поддержки не появлялись в админ-панели.

## Причины

### 1. Логическая ошибка в `handle_message()` (КРИТИЧЕСКАЯ)

В файле [support_bot.py](teaching_panel/support_bot.py#L549-L559) был следующий код:

```python
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    
    try:
        user = await get_user_by_telegram_id(telegram_id)
        if not user.is_staff:
            return  # ← БАГ! Все сообщения от обычных пользователей ИГНОРИРОВАЛИСЬ
    except CustomUser.DoesNotExist:
        return  # ← Незарегистрированные тоже игнорировались
```

**Проблема**: Код сначала проверял `is_staff` и возвращался, никогда не доходя до блока `elif mode == 'user':` где создавались тикеты.

### 2. SynchronousOnlyOperation ошибки

В логах видны ошибки Django:
```
django.core.exceptions.SynchronousOnlyOperation: You cannot call this from an async context
```

Это происходило на строке 439 при попытке синхронного ORM вызова в async функции.

## Решение

### Исправленная логика в `handle_message()`:

```python
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    message_text = update.message.text
    
    # Логируем входящее сообщение
    logger.info(f"[MSG] telegram_id={telegram_id}, text={message_text[:50]}...")
    
    try:
        user = await get_user_by_telegram_id(telegram_id)
    except CustomUser.DoesNotExist:
        # Уведомляем о необходимости регистрации
        await update.message.reply_text("Для связи с поддержкой необходимо зарегистрироваться...")
        return
    
    ctx = user_context.get(telegram_id, {})
    mode = ctx.get('mode')
    
    # СНАЧАЛА обрабатываем обычных пользователей
    if mode == 'user':
        creating = ctx.get('creating_ticket')
        # ... логика создания тикета
        
        # Если нет активного создания - создаём быстрый тикет
        ticket = await create_ticket(...)
        return
    
    # ПОТОМ обрабатываем админов
    if mode == 'admin' or (user and user.is_staff):
        # ... логика ответа на тикет
        return
    
    # Fallback для обычных пользователей без контекста
    if user and not user.is_staff:
        ticket = await create_ticket(...)
```

### Ключевые изменения:

1. **Логирование** - все входящие сообщения теперь логируются с `[MSG]` тегом
2. **Приоритет user над admin** - сначала обрабатываем создание тикетов для обычных пользователей
3. **Fallback тикет** - любое сообщение от обычного пользователя создаёт тикет
4. **Убраны escape-символы** `\\n\\n` → `\n\n` для корректного отображения

## Восстановление данных

К сожалению, Telegram API **не хранит историю сообщений** после их получения через `getUpdates`.

Потерянные сообщения невозможно восстановить, так как:
- Бот работает в режиме polling, а не webhook
- До исправления не было логирования входящих сообщений
- `post_logs.txt` содержит только логи zoom, не telegram

## Профилактика

1. **Логирование** добавлено - все сообщения логируются с `[MSG]` тегом
2. **Создан скрипт мониторинга** [check_support_messages.py](teaching_panel/check_support_messages.py):
   ```bash
   python check_support_messages.py           # Последние тикеты
   python check_support_messages.py --stats   # Статистика
   python check_support_messages.py --users   # Пользователи с TG
   ```

## Тестирование

После деплоя бот успешно перезапустился:
```
Feb 04 18:19:00 support_bot[202758]: ✅ Бот поддержки запущен!
Feb 04 18:19:01 support_bot[202758]: Application started
```

Проверка логов:
```bash
ssh tp 'sudo journalctl -u support_bot --since "now" | grep "\[MSG\]"'
```

## Файлы изменений

- [support_bot.py](teaching_panel/support_bot.py) - исправлена логика обработки сообщений
- [check_support_messages.py](teaching_panel/check_support_messages.py) - скрипт мониторинга (новый)

## Коммит

```
fix(support): handle messages from non-staff users - create tickets from Telegram messages
```
