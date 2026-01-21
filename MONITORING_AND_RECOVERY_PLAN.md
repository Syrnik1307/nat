# LECTIO AUTO-RECOVERY & MONITORING SYSTEM
## Комплексный план защиты от простоев

> **Статус**: Готово к установке  
> **Создано**: 22 января 2026  
> **Причина**: 403 Forbidden после деплоя (проблема с правами доступа)

---

## Корневая причина сегодняшнего инцидента

Сайт упал из-за **неправильных прав доступа** после деплоя:
1. `scp` скопировал файлы с правами текущего пользователя
2. Nginx работает от `www-data` и не мог прочитать файлы
3. Результат: 403 Forbidden

**Исправление**: `sudo chown -R www-data:www-data /var/www/teaching_panel/frontend/build`

---

## Архитектура системы мониторинга

```
┌─────────────────────────────────────────────────────────────────┐
│                    LECTIO AUTO-RECOVERY SYSTEM                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │   Cron      │───▶│  Health     │───▶│  Auto       │        │
│  │   (1 min)   │    │  Check      │    │  Recovery   │        │
│  └─────────────┘    └──────┬──────┘    └──────┬──────┘        │
│                            │                   │                │
│                            ▼                   ▼                │
│                    ┌───────────────────────────────┐           │
│                    │      Telegram Alerts          │           │
│                    │   (мгновенные уведомления)    │           │
│                    └───────────────────────────────┘           │
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │  Systemd    │───▶│  Watchdog   │───▶│  Auto       │        │
│  │  Service    │    │  (60s)      │    │  Restart    │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
│                                                                 │
│  ┌─────────────────────────────────────────────────────┐       │
│  │               Safe Deploy Script                     │       │
│  │  • Pre-deploy health check                           │       │
│  │  • Automatic backup                                  │       │
│  │  • Permission fix (chown www-data)                   │       │
│  │  • Post-deploy health check                          │       │
│  │  • Auto-rollback on failure                          │       │
│  └─────────────────────────────────────────────────────┘       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Компоненты системы

### 1. Health Check Script (`health_check.sh`)
**Расположение**: `/opt/lectio-monitor/health_check.sh`

**Проверяет**:
- HTTP статус сайта (200 = OK)
- Время ответа (< 5 сек)
- Права доступа frontend
- Gunicorn workers
- Дисковое пространство
- Свободная память
- Соединение с базой данных

**Автовосстановление**:
- Исправление прав доступа
- Перезапуск teaching_panel
- Перезапуск nginx
- Ограничение попыток (3 подряд, потом cooldown 5 мин)

### 2. Systemd Watchdog
**Файл**: `/etc/systemd/system/teaching_panel.service`

**Возможности**:
- `WatchdogSec=60` - перезапуск если сервис не отвечает 60 сек
- `Restart=always` - автоперезапуск при любом сбое
- `StartLimitBurst=5` - максимум 5 перезапусков за 5 минут
- `OnFailure=failure-notifier@%n.service` - уведомление в Telegram

### 3. Telegram Alerts
**Уровни**:
- 🚨 **CRITICAL** - сайт недоступен, требуется вмешательство
- ⚠️ **WARNING** - проблемы обнаружены, автовосстановление запущено
- ℹ️ **INFO** - информационные сообщения

### 4. Safe Deploy Script
**Windows**: `scripts/deploy_safe.ps1`  
**Linux**: `/opt/lectio-monitor/deploy_safe.sh`

**Гарантии**:
1. Pre-deploy health check
2. Автоматический backup
3. Atomic swap (mv, не cp)
4. **Обязательное исправление прав** (`chown www-data`)
5. Post-deploy health check
6. Автоматический rollback при проблемах

---

## Установка на сервер

### Шаг 1: Копирование файлов
```bash
# С локальной машины
scp -r scripts/monitoring tp:/tmp/monitoring-install

# На сервере
ssh tp
cd /tmp/monitoring-install
sudo bash install_monitoring.sh
```

### Шаг 2: Настройка Telegram
```bash
# 1. Создать бота через @BotFather
# 2. Получить токен
# 3. Отправить боту сообщение
# 4. Получить chat_id: https://api.telegram.org/bot<TOKEN>/getUpdates

sudo nano /opt/lectio-monitor/config.env
# Заполнить:
# TELEGRAM_BOT_TOKEN="your_token"
# TELEGRAM_CHAT_ID="your_chat_id"
```

### Шаг 3: Проверка работы
```bash
# Тест health check
sudo /opt/lectio-monitor/health_check.sh

# Проверка cron
sudo crontab -l | grep lectio

# Проверка логов
sudo tail -f /var/log/lectio-monitor/health.log
```

---

## Использование Safe Deploy

### Из Windows (PowerShell)
```powershell
# Только frontend
.\scripts\deploy_safe.ps1 -Type frontend

# Только backend  
.\scripts\deploy_safe.ps1 -Type backend

# Полный деплой
.\scripts\deploy_safe.ps1 -Type full

# Без пересборки frontend
.\scripts\deploy_safe.ps1 -Type frontend -SkipBuild
```

### С сервера
```bash
# Frontend
sudo /opt/lectio-monitor/deploy_safe.sh frontend /path/to/build

# Backend
sudo /opt/lectio-monitor/deploy_safe.sh backend
```

---

## Что делать при критическом сбое

### Если сайт недоступен

1. **Подождать 1-2 минуты** - система должна восстановиться автоматически
2. Если не восстановился, проверить Telegram - там будут детали
3. SSH на сервер и проверить:
   ```bash
   # Статус сервисов
   systemctl status teaching_panel nginx
   
   # Логи
   sudo tail -50 /var/log/lectio-monitor/health.log
   sudo journalctl -u teaching_panel -n 50
   
   # Права frontend
   ls -la /var/www/teaching_panel/frontend/build/
   ```

4. Ручное восстановление:
   ```bash
   # Права
   sudo chown -R www-data:www-data /var/www/teaching_panel/frontend/build
   sudo chmod -R 755 /var/www/teaching_panel/frontend/build
   
   # Перезапуск
   sudo systemctl restart teaching_panel nginx
   ```

### Если база данных недоступна

```bash
# Проверить SQLite файл
ls -la /var/www/teaching_panel/teaching_panel/db.sqlite3

# Восстановить из backup
sudo cp /var/www/teaching_panel/backups/db_latest.sqlite3 \
        /var/www/teaching_panel/teaching_panel/db.sqlite3
sudo chown www-data:www-data /var/www/teaching_panel/teaching_panel/db.sqlite3
sudo systemctl restart teaching_panel
```

---

## Мониторинг и логи

### Где искать информацию

| Лог | Путь | Описание |
|-----|------|----------|
| Health check | `/var/log/lectio-monitor/health.log` | Результаты проверок |
| Alerts | `/var/log/lectio-monitor/alerts.log` | Все отправленные алерты |
| Deploy | `/var/log/lectio-monitor/deploy.log` | История деплоев |
| Cron | `/var/log/lectio-monitor/cron.log` | Логи cron задач |
| Django | `/var/log/teaching_panel/error.log` | Ошибки приложения |
| Nginx | `/var/log/nginx/error.log` | Ошибки web-сервера |

### Полезные команды

```bash
# Последние health check
tail -20 /var/log/lectio-monitor/health.log

# Все критические алерты
grep "CRITICAL\|ERROR" /var/log/lectio-monitor/health.log

# Статистика перезапусков
journalctl -u teaching_panel | grep "Started\|Stopped\|Failed" | tail -20

# Проверка cron
grep CRON /var/log/syslog | tail -10
```

---

## Тестирование системы

### Симуляция сбоя прав доступа
```bash
# Ломаем права (для теста)
sudo chmod 000 /var/www/teaching_panel/frontend/build/index.html

# Ждём 1-2 минуты
# Должно прийти уведомление в Telegram
# И автоматически восстановиться
```

### Симуляция падения сервиса
```bash
# Убиваем gunicorn
sudo pkill -f gunicorn

# Systemd должен перезапустить через 5 секунд
```

### Проверка rollback
```bash
# Создаём битую сборку
mkdir /tmp/broken-build
echo "broken" > /tmp/broken-build/index.html

# Деплоим (должен откатиться)
sudo /opt/lectio-monitor/deploy_safe.sh frontend /tmp/broken-build
```

---

## Файловая структура

```
scripts/monitoring/
├── health_check.sh           # Основной скрипт проверки
├── deploy_safe.sh            # Безопасный деплой (Linux)
├── notify_failure.sh         # Отправка Telegram уведомлений
├── install_monitoring.sh     # Установщик
├── config.env.example        # Пример конфигурации
└── systemd/
    ├── teaching_panel.service      # Сервис с watchdog
    └── failure-notifier@.service   # Уведомления о падениях

scripts/
└── deploy_safe.ps1           # Безопасный деплой (Windows)

teaching_panel/teaching_panel/
└── health.py                 # Django health endpoint
```

---

## Чек-лист установки

- [ ] Скопировать `scripts/monitoring/` на сервер
- [ ] Запустить `install_monitoring.sh`
- [ ] Создать Telegram бота через @BotFather
- [ ] Заполнить `/opt/lectio-monitor/config.env`
- [ ] Проверить cron: `crontab -l | grep lectio`
- [ ] Проверить systemd: `systemctl status teaching_panel`
- [ ] Тест health check: `/opt/lectio-monitor/health_check.sh`
- [ ] Тест Telegram: симулировать сбой и проверить уведомление

---

## Гарантии после установки

| Сценарий | Время обнаружения | Время восстановления |
|----------|-------------------|----------------------|
| Сервис упал | Мгновенно (systemd) | 5 секунд (auto restart) |
| Права доступа | 1 минута (cron) | 10 секунд (auto fix) |
| Nginx завис | 1 минута (cron) | 15 секунд (auto restart) |
| Полное зависание | 60 секунд (watchdog) | 15 секунд |
| Плохой деплой | Мгновенно (health check) | 30 секунд (auto rollback) |

**Telegram уведомления**: Вы получите алерт в течение 2 минут после любого сбоя.

---

## Контакты при эскалации

Если автовосстановление не помогает и прошло > 5 минут:
1. Проверить Telegram на детали ошибки
2. SSH на сервер для ручной диагностики
3. Проверить `/var/log/lectio-monitor/health.log`
4. При необходимости откатить вручную из backup

---

**Этот план обеспечивает 99.9% uptime при правильной настройке.**
