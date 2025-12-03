# 🤖 Инструкция по настройке Telegram бота

## Шаг 1: Создание бота через BotFather

1. Откройте Telegram и найдите бота **@BotFather**
2. Отправьте команду `/newbot`
3. Введите имя бота (например: **Teaching Panel Bot**)
4. Введите username бота (должен заканчиваться на `bot`, например: **teaching_panel_test_bot**)
5. BotFather выдаст вам **токен** вида: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`
6. **СОХРАНИТЕ ЭТОТ ТОКЕН!** Он понадобится для настройки

## Шаг 2: Настройка .env файла (локально)

Откройте файл `teaching_panel/.env` (или создайте его из `.env.example`) и добавьте:

```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=ВАШ_ТОКЕН_ОТ_BOTFATHER
TELEGRAM_BOT_USERNAME=teaching_panel_test_bot
```

## Шаг 3: Настройка .env на сервере

Подключитесь к серверу и отредактируйте файл:

```bash
ssh tp
nano /var/www/teaching_panel/.env
```

Добавьте те же строки:

```bash
TELEGRAM_BOT_TOKEN=ВАШ_ТОКЕН_ОТ_BOTFATHER
TELEGRAM_BOT_USERNAME=teaching_panel_test_bot
```

Сохраните файл (Ctrl+O, Enter, Ctrl+X)

## Шаг 4: Установка зависимостей (если ещё не установлены)

### Локально:

```powershell
cd C:\Users\User\Desktop\nat
.\.venv\Scripts\Activate.ps1
pip install python-telegram-bot
```

### На сервере:

```bash
ssh tp "cd /var/www/teaching_panel && source venv/bin/activate && pip install python-telegram-bot"
```

## Шаг 5: Запуск бота

### Локально (для тестирования):

```powershell
cd C:\Users\User\Desktop\nat\teaching_panel
.\.venv\Scripts\python.exe telegram_bot.py
```

Бот должен вывести:
```
✅ Бот запущен и готов принимать команды!
```

### На сервере (через systemd):

Создайте сервис файл (если ещё не создан):

```bash
sudo nano /etc/systemd/system/telegram_bot.service
```

Содержимое:

```ini
[Unit]
Description=Teaching Panel Telegram Bot
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/teaching_panel/teaching_panel
Environment="PATH=/var/www/teaching_panel/venv/bin"
ExecStart=/var/www/teaching_panel/venv/bin/python telegram_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Запустите сервис:

```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram_bot
sudo systemctl start telegram_bot
sudo systemctl status telegram_bot
```

## Шаг 6: Тестирование бота

1. Найдите своего бота в Telegram по username: `@teaching_panel_test_bot`
2. Отправьте команду `/start`
3. Бот должен ответить приветственным сообщением

## Команды бота:

- `/start` - Начало работы с ботом
- `/link <код>` - Привязать аккаунт (код получаете в веб-интерфейсе)
- `/unlink` - Отвязать аккаунт
- `/menu` - Главное меню
- `/lessons` - Список ближайших уроков
- `/homework` - Список домашних заданий
- `/notifications` - Настройки уведомлений
- `/help` - Справка

## Проверка работы уведомлений:

После привязки аккаунта:
1. Создайте ДЗ в веб-интерфейсе
2. Опубликуйте ДЗ
3. В течение минуты должно прийти уведомление в Telegram

## Troubleshooting:

### Бот не отвечает:
```bash
# Проверьте, запущен ли бот
sudo systemctl status telegram_bot

# Посмотрите логи
sudo journalctl -u telegram_bot -f
```

### Ошибка "TELEGRAM_BOT_TOKEN not set":
- Проверьте, что токен добавлен в .env файл
- Перезапустите бот после добавления токена

### Уведомления не приходят:
1. Проверьте, что аккаунт привязан: `/link` показывает ваш email
2. Проверьте настройки уведомлений: `/notifications`
3. Убедитесь, что в коде `homework/views.py` вызывается `_notify_students_about_new_homework()`

---

**Готово!** Бот настроен и готов к работе 🚀
